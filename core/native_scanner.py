
import requests
import yaml
import re
import urllib3
import logging
import threading
from urllib.parse import urljoin
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from PyQt5.QtCore import QObject, pyqtSignal
from i18n import tr

# 禁用 SSL 警告（扫描工具通常需要访问自签名证书的目标）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NativeScanner(QObject):
    """
    原生 Python 扫描核心
    替代 nuclei.exe，直接使用 requests 发包，解决进程卡死问题
    """
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal()

    def __init__(self, targets, templates, config=None):
        super().__init__()
        self.targets = targets
        self.templates = templates  # List of YAML file paths
        self.config = config or {}
        self._is_running = True
        self._stop_lock = threading.Lock()  # 线程安全锁
        self._executor = None  # 保存线程池引用，用于快速停止
        self._session = None   # 保存 Session 引用，用于快速停止

        # 配置 - 使用较短的超时便于快速停止
        self.timeout = min(self.config.get('timeout', 10), 5)  # 最大 5 秒
        configured_workers = self.config.get('rate_limit', 50)
        try:
            configured_workers = int(configured_workers)
        except (TypeError, ValueError):
            configured_workers = 10
        self.max_workers = max(1, min(configured_workers, 32))
        self.max_in_flight = max(self.max_workers * 2, 8)
        self.retries = self.config.get('retries', 0)
        self.proxies = None
        if self.config.get('proxy'):
            self.proxies = {
                'http': self.config['proxy'],
                'https': self.config['proxy']
            }

    def stop(self):
        """停止扫描 - 线程安全的停止机制"""
        with self._stop_lock:
            self._is_running = False

        # 立即关闭线程池并取消所有待执行任务
        if self._executor:
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
            except (TypeError, Exception):
                # Python < 3.9 不支持 cancel_futures 参数
                try:
                    self._executor.shutdown(wait=False)
                except Exception:
                    pass
            self._executor = None

        # 关闭 Session，中断正在进行的请求
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None

    def _is_stopped(self):
        """线程安全地检查是否已停止"""
        with self._stop_lock:
            return not self._is_running

    def _expand_target_urls(self):
        expanded_targets = []
        for target in self.targets:
            if not target.startswith(('http://', 'https://')):
                expanded_targets.extend([f'http://{target}', f'https://{target}'])
            else:
                expanded_targets.append(target)
        return expanded_targets

    def run(self):
        """Execute the scan with bounded in-flight tasks."""
        self.log_signal.emit(tr("scanner.engine_started", targets=len(self.targets), templates=len(self.templates), workers=self.max_workers))

        self._session = requests.Session()
        self._session.verify = False
        if self.proxies:
            self._session.proxies = self.proxies

        parsed_templates = []
        for t_path in self.templates:
            if not self._is_running:
                break
            try:
                with open(t_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    parsed_templates.append({
                        'path': t_path,
                        'id': data.get('id', 'unknown'),
                        'info': data.get('info', {}),
                        'requests': data.get('requests', []),
                        'http': data.get('http', []),
                    })
            except Exception as e:
                self.log_signal.emit(tr("scanner.template_parse_failed", path=t_path, error=e))

        expanded_targets = self._expand_target_urls()
        total_tasks = len(expanded_targets) * len(parsed_templates)
        processed_count = 0

        def submit_pending_jobs(executor, jobs_iter, in_flight):
            while self._is_running and len(in_flight) < self.max_in_flight:
                try:
                    base_url, tmpl = next(jobs_iter)
                except StopIteration:
                    break
                try:
                    in_flight.add(executor.submit(self._scan_single_target, base_url, tmpl))
                except RuntimeError:
                    break

        try:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            jobs_iter = iter((base_url, tmpl) for base_url in expanded_targets for tmpl in parsed_templates)
            in_flight = set()
            submit_pending_jobs(self._executor, jobs_iter, in_flight)

            while in_flight and self._is_running:
                done, in_flight = wait(in_flight, timeout=0.2, return_when=FIRST_COMPLETED)
                if not done:
                    continue

                for future in done:
                    try:
                        result = future.result()
                        if result and self._is_running:
                            try:
                                self.result_signal.emit(result)
                            except RuntimeError:
                                pass
                    except Exception:
                        pass

                    processed_count += 1
                    if self._is_running and total_tasks and (processed_count % 5 == 0 or processed_count == total_tasks):
                        try:
                            self.progress_signal.emit(processed_count, total_tasks, tr("scanner.scanning_progress", current=processed_count, total=total_tasks))
                        except RuntimeError:
                            pass

                submit_pending_jobs(self._executor, jobs_iter, in_flight)

        finally:
            if self._executor:
                try:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                except (TypeError, Exception):
                    try:
                        self._executor.shutdown(wait=False)
                    except Exception:
                        pass
                self._executor = None

            if self._session:
                try:
                    self._session.close()
                except Exception:
                    pass
                self._session = None

        try:
            if self._is_running:
                self.log_signal.emit(tr("scanner.scan_complete"))
            else:
                self.log_signal.emit(tr("scanner.scan_stopped"))
            self.finished_signal.emit()
        except RuntimeError:
            pass

    def _scan_single_target(self, target, tmpl):
        """扫描单个目标"""
        if not self._is_running:
            return None

        # 合并 requests 和 http 字段
        requests_list = tmpl.get('http', []) + tmpl.get('requests', [])
        
        # 用于存储所有步骤的响应，供后续匹配使用
        last_response = None
        last_matched_url = None
        last_req_method = None
        last_req_body = None
        
        for req_def in requests_list:
            # 每次请求前检查停止状态
            if not self._is_running:
                return None
            
            # 获取匹配器（只在最后一个有 matchers 的请求块上使用）
            matchers = req_def.get('matchers', [])
            matchers_condition = req_def.get('matchers-condition', 'or')
                
            try:
                # 检查是否是 raw 格式（多步骤 POC）
                raw_list = req_def.get('raw', [])
                if raw_list:
                    # 处理 raw 格式请求
                    for raw_request in raw_list:
                        if not self._is_running:
                            return None
                        
                        result = self._send_raw_request(target, raw_request)
                        if result:
                            last_response = result['response']
                            last_matched_url = result['url']
                            last_req_method = result['method']
                            last_req_body = result['body']
                else:
                    # 处理传统 path 格式请求
                    method = req_def.get('method', 'GET')
                    path_list = req_def.get('path', [])
                    
                    # 遍历路径变体
                    for raw_path in path_list:
                        # 检查停止状态
                        if not self._is_running:
                            return None
                            
                        # 替换变量 {{BaseURL}}
                        path = raw_path.replace('{{BaseURL}}', target.rstrip('/'))
                        path = path.replace('{{RootURL}}', target.rstrip('/'))
                        
                        # 使用 Session 发送请求 (可被 stop() 中断)
                        if not self._session:
                            return None
                            
                        response = self._session.request(
                            method=method,
                            url=path,
                            headers=req_def.get('headers', {'User-Agent': 'Mozilla/5.0'}),
                            data=req_def.get('body'),
                            timeout=(2, self.timeout),
                            allow_redirects=True
                        )
                        
                        last_response = response
                        last_matched_url = path
                        last_req_method = method
                        last_req_body = req_def.get('body', '')
                
                # 如果这个请求块有匹配器，则进行匹配
                if matchers and last_response:
                    if not self._is_running:
                        return None
                        
                    if self._match_response(last_response, matchers, matchers_condition):
                        # 获取请求详情用于复现
                        req_body = ""
                        if last_response.request.body:
                            try:
                                if isinstance(last_response.request.body, bytes):
                                    req_body = last_response.request.body.decode('utf-8', errors='ignore')
                                else:
                                    req_body = str(last_response.request.body)
                            except (UnicodeDecodeError, AttributeError):
                                req_body = "[Binary Data]"

                        return {
                            'template-id': tmpl['id'],
                            'template-path': tmpl['path'],
                            'matched-at': last_matched_url,
                            'info': tmpl['info'],
                            'type': 'http',
                            'request_method': last_req_method,
                            'request_body': req_body,
                            'response': ''
                        }

            except Exception as e:
                # 如果是因为 Session 关闭导致的错误，静默处理
                if not self._is_running:
                    return None
                pass
        
        return None
    
    def _send_raw_request(self, target, raw_request):
        """解析并发送 raw 格式的 HTTP 请求"""
        if not self._is_running or not self._session:
            return None
        
        try:
            # 替换变量
            raw_request = raw_request.replace('{{Hostname}}', target.replace('http://', '').replace('https://', '').rstrip('/'))
            raw_request = raw_request.replace('{{BaseURL}}', target.rstrip('/'))
            raw_request = raw_request.replace('{{RootURL}}', target.rstrip('/'))
            
            # 解析 raw 请求
            lines = raw_request.strip().split('\n')
            if not lines:
                return None
            
            # 解析请求行
            first_line = lines[0].strip()
            parts = first_line.split(' ')
            if len(parts) < 2:
                return None
            
            method = parts[0].upper()
            path = parts[1]
            
            # 构建完整 URL
            if path.startswith('/'):
                # 相对路径，需要加上目标 base URL
                from urllib.parse import urlparse
                parsed = urlparse(target)
                url = f"{parsed.scheme}://{parsed.netloc}{path}"
            else:
                url = path
            
            # 解析头和 body
            headers = {}
            body = ""
            body_start = False
            
            for i, line in enumerate(lines[1:], 1):
                line = line.rstrip('\r')
                if line == '' and not body_start:
                    body_start = True
                    continue
                if body_start:
                    body += line + '\n'
                else:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        # 跳过 Host 头，因为我们会自动设置
                        if key.strip().lower() != 'host':
                            headers[key.strip()] = value.strip()
            
            body = body.rstrip('\n')
            
            # 设置默认 User-Agent
            if 'User-Agent' not in headers:
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0'
            
            # 发送请求
            response = self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=body if body else None,
                timeout=(2, self.timeout),
                allow_redirects=True
            )
            
            return {
                'response': response,
                'url': url,
                'method': method,
                'body': body
            }
            
        except Exception as e:
            if self._is_running:
                pass  # 静默处理非停止导致的错误
            return None


    def _match_response(self, response, matchers, condition):
        """
        匹配响应
        matchers: list of matcher dicts
        condition: 'and' or 'or'
        """
        if not matchers:
            return False

        results = []
        for matcher in matchers:
            m_type = matcher.get('type', 'word')
            m_part = matcher.get('part', 'body') # body, header, status, all
            m_condition = matcher.get('condition', 'or') # and/or internally for words
            
            # 获取待匹配内容
            content = ""
            if m_part == 'body':
                content = response.text
            elif m_part == 'header':
                content = str(response.headers)
            elif m_part == 'status':
                content = str(response.status_code)
            else:
                content = response.text + str(response.headers)

            # 执行匹配
            is_match = False
            
            if m_type == 'status':
                status_codes = matcher.get('status', [])
                is_match = response.status_code in status_codes
                
            elif m_type == 'word':
                words = matcher.get('words', [])
                # 词组匹配
                hits = [w in content for w in words]
                if m_condition == 'and':
                    is_match = all(hits)
                else:
                    is_match = any(hits)
                    
            elif m_type == 'regex':
                regexs = matcher.get('regex', [])
                for r in regexs:
                    if re.search(r, content, re.IGNORECASE | re.MULTILINE):
                        is_match = True
                        break
            
            results.append(is_match)

        # 综合判断
        if condition == 'and':
            return all(results)
        else:
            return any(results)
