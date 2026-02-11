
import requests
import yaml
import re
import urllib3
import logging
import threading
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QObject, pyqtSignal

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
        self.max_workers = self.config.get('rate_limit', 50)
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

    def run(self):
        """执行扫描"""
        total_tasks = len(self.targets) * len(self.templates)
        self.log_signal.emit(f"[*] Native 引擎启动: {len(self.targets)} 目标, {len(self.templates)} POC, 并发 {self.max_workers}")

        # 创建共享 Session，便于快速关闭
        self._session = requests.Session()
        self._session.verify = False
        if self.proxies:
            self._session.proxies = self.proxies

        # 解析所有模板
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
                        # 兼容 http 字段 (新版 nuclei 使用 http，旧版使用 requests)
                        'http': data.get('http', [])
                    })
            except Exception as e:
                self.log_signal.emit(f"[!] 模板解析失败 {t_path}: {e}")

        # 任务队列
        tasks = []
        processed_count = 0

        try:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            
            for target in self.targets:
                if not self._is_running:
                    break
                    
                # 规范化目标 URL
                if not target.startswith(('http://', 'https://')):
                    base_urls = [f'http://{target}', f'https://{target}']
                else:
                    base_urls = [target]

                for base_url in base_urls:
                    for tmpl in parsed_templates:
                        if not self._is_running:
                            break
                        
                        # 提交任务
                        future = self._executor.submit(self._scan_single_target, base_url, tmpl)
                        tasks.append(future)

            # 等待结果 - 使用超时避免阻塞
            for future in as_completed(tasks):
                if not self._is_running:
                    break
                
                try:
                    # 添加短超时，避免阻塞
                    result = future.result(timeout=0.1)
                    if result and self._is_running:
                        try:
                            self.result_signal.emit(result)
                        except RuntimeError:
                            pass  # 信号可能已断开
                except TimeoutError:
                    # 任务尚未完成，跳过
                    pass
                except Exception:
                    pass
                
                processed_count += 1
                # 降频发送进度，避免 UI 卡顿
                if self._is_running and (processed_count % 5 == 0 or processed_count == len(tasks)):
                    try:
                        self.progress_signal.emit(processed_count, len(tasks), f"扫描中... {processed_count}/{len(tasks)}")
                    except RuntimeError:
                        pass  # 信号可能已断开
                    
        finally:
            # 确保线程池被关闭
            if self._executor:
                try:
                    self._executor.shutdown(wait=False, cancel_futures=True)
                except (TypeError, Exception):
                    try:
                        self._executor.shutdown(wait=False)
                    except Exception:
                        pass
                self._executor = None

            # 关闭 Session
            if self._session:
                try:
                    self._session.close()
                except Exception:
                    pass
                self._session = None

        # 安全地发送完成信号
        try:
            if self._is_running:
                self.log_signal.emit("[*] 扫描完成")
            else:
                self.log_signal.emit("[*] 扫描已停止")
            self.finished_signal.emit()
        except RuntimeError:
            pass  # 信号可能已断开

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
