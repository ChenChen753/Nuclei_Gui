"""
扫描结果导出管理器
支持导出为 CSV 表格和 HTML 报告格式
"""
import csv
import json
import os
from datetime import datetime


def export_to_csv(scan_record: dict, vulns: list, file_path: str) -> bool:
    """
    将扫描结果导出为 CSV 格式
    
    参数:
        scan_record: 扫描记录字典
        vulns: 漏洞结果列表
        file_path: 导出文件路径
        
    返回:
        是否导出成功
    """
    try:
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                '序号', '严重程度', 'POC ID', '目标地址', 'POC 路径', 
                '请求方法', '请求体', 'POC 完整请求链', '发现时间'
            ])
            
            # 写入漏洞数据
            for idx, v in enumerate(vulns, 1):
                # 解析 raw_json 获取请求信息
                raw_data = {}
                try:
                    if v.get('raw_json'):
                        raw_data = json.loads(v['raw_json'])
                except:
                    pass
                
                # 提取请求方法和请求体
                method = "GET"
                body = ""
                if raw_data:
                    if raw_data.get('request'):
                        full_request = raw_data['request']
                        first_line = full_request.split('\r\n')[0] if '\r\n' in full_request else full_request.split('\n')[0]
                        if first_line:
                            parts = first_line.split(' ')
                            if parts:
                                method = parts[0]
                        if '\r\n\r\n' in full_request:
                            body = full_request.split('\r\n\r\n', 1)[1] if len(full_request.split('\r\n\r\n')) > 1 else ""
                        elif '\n\n' in full_request:
                            body = full_request.split('\n\n', 1)[1] if len(full_request.split('\n\n')) > 1 else ""
                    else:
                        method = raw_data.get('request_method', 'GET')
                        body = raw_data.get('request_body', '')
                
                # === 从 POC 文件解析完整请求链 ===
                poc_requests_text = ""
                poc_path = v.get('template_path') or (raw_data.get('template-path') if raw_data else None)
                matched_url = v.get('matched_at', '')
                
                # 提取实际的 Hostname
                actual_hostname = ""
                actual_base_url = ""
                if matched_url:
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(matched_url)
                        if parsed.port and parsed.port not in [80, 443]:
                            actual_hostname = f"{parsed.hostname}:{parsed.port}"
                        else:
                            actual_hostname = parsed.hostname or ""
                        actual_base_url = f"{parsed.scheme}://{actual_hostname}"
                    except:
                        pass
                
                # 如果路径不存在，尝试根据 template_id 搜索 POC 文件
                if poc_path and not os.path.exists(poc_path):
                    template_id = v.get('template_id', '')
                    if template_id:
                        try:
                            from pathlib import Path
                            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                            poc_library = Path(base_dir) / "poc_library"
                            for yaml_file in poc_library.rglob("*.yaml"):
                                try:
                                    import yaml
                                    with open(yaml_file, 'r', encoding='utf-8') as pf:
                                        content = yaml.safe_load(pf)
                                        if content and content.get('id') == template_id:
                                            poc_path = str(yaml_file)
                                            break
                                except:
                                    continue
                        except:
                            pass
                
                if poc_path and os.path.exists(poc_path):
                    try:
                        import yaml
                        import re as regex_module
                        with open(poc_path, 'r', encoding='utf-8') as pf:
                            poc_content = yaml.safe_load(pf)
                        
                        # === 从 matched_url 提取随机生成的变量值 ===
                        extracted_random_values = {}
                        
                        # 获取 POC 中定义的变量名和提取器名称
                        poc_variable_names = []
                        poc_extractor_names = []
                        if poc_content.get('variables'):
                            poc_variable_names = list(poc_content['variables'].keys())
                            # 将 POC 中定义的变量默认值加入替换字典
                            for var_name, var_value in poc_content['variables'].items():
                                if var_value is not None:
                                    # 处理不同类型的值
                                    if isinstance(var_value, (int, float)):
                                        extracted_random_values[var_name] = str(var_value)
                                    elif isinstance(var_value, str):
                                        extracted_random_values[var_name] = var_value
                                    else:
                                        extracted_random_values[var_name] = str(var_value)
                        for item in poc_content.get('http', []):
                            extractors = item.get('extractors', [])
                            for ext in extractors:
                                if ext.get('name'):
                                    poc_extractor_names.append(ext['name'])
                        
                        # 从 matched_url 提取文件名
                        if matched_url:
                            try:
                                from urllib.parse import urlparse
                                parsed_url = urlparse(matched_url)
                                url_path = parsed_url.path
                                path_parts = url_path.split('/')
                                if path_parts:
                                    last_part = path_parts[-1]
                                    if '.' in last_part:
                                        full_filename = last_part
                                        basename = last_part.rsplit('.', 1)[0]
                                        
                                        # 将文件名赋值给提取器变量
                                        for ext_name in poc_extractor_names:
                                            extracted_random_values[ext_name] = full_filename
                                        if 'uploadfile' not in extracted_random_values:
                                            extracted_random_values['uploadfile'] = full_filename
                                        
                                        if regex_module.match(r'^[a-zA-Z0-9]{6,50}$', basename):
                                            extracted_random_values['random_filename'] = basename
                                            extracted_random_values['rand_base(8)'] = basename
                                            for var_name in poc_variable_names:
                                                if 'name' in var_name.lower() or 'user' in var_name.lower():
                                                    extracted_random_values[var_name] = basename
                            except:
                                pass
                        
                        http_section = poc_content.get('http', [])
                        if http_section:
                            request_steps = []
                            step_num = 1
                            
                            for item in http_section:
                                raw_requests = item.get('raw', [])
                                if raw_requests:
                                    for raw_req in raw_requests:
                                        req_content = raw_req.strip()
                                        if actual_hostname:
                                            req_content = req_content.replace('{{Hostname}}', actual_hostname)
                                            req_content = req_content.replace('{{BaseURL}}', actual_base_url)
                                            req_content = req_content.replace('{{Host}}', actual_hostname)
                                        # 替换所有变量
                                        for var_name, var_value in extracted_random_values.items():
                                            req_content = req_content.replace('{{' + var_name + '}}', var_value)
                                        if extracted_random_values.get('random_filename'):
                                            random_val = extracted_random_values['random_filename']
                                            req_content = regex_module.sub(r'\{\{rand_base\(\d+\)\}\}', random_val, req_content)
                                            req_content = regex_module.sub(r'\{\{to_lower\(rand_base\(\d+\)\)\}\}', random_val.lower(), req_content)
                                            req_content = regex_module.sub(r'\{\{to_upper\(rand_base\(\d+\)\)\}\}', random_val.upper(), req_content)
                                        # 替换其他未知变量
                                        remaining_vars = regex_module.findall(r'\{\{([^}]+)\}\}', req_content)
                                        for var in remaining_vars:
                                            if extracted_random_values.get('random_filename'):
                                                req_content = req_content.replace('{{' + var + '}}', f"[{extracted_random_values['random_filename']}]")
                                        request_steps.append(f"[步骤{step_num}] {req_content}")
                                        step_num += 1
                                
                                if item.get('path') or item.get('method'):
                                    req_method = item.get('method', 'GET')
                                    paths = item.get('path', [])
                                    if isinstance(paths, str):
                                        paths = [paths]
                                    for path in paths:
                                        actual_path = path
                                        if actual_hostname:
                                            actual_path = actual_path.replace('{{Hostname}}', actual_hostname)
                                            actual_path = actual_path.replace('{{BaseURL}}', actual_base_url)
                                        for var_name, var_value in extracted_random_values.items():
                                            actual_path = actual_path.replace('{{' + var_name + '}}', var_value)
                                        request_steps.append(f"[步骤{step_num}] {req_method} {actual_path}")
                                        step_num += 1
                            
                            if len(request_steps) > 1:
                                poc_requests_text = " | ".join(request_steps)
                    except:
                        pass
                
                writer.writerow([
                    idx,
                    v.get('severity', 'unknown'),
                    v.get('template_id', ''),
                    v.get('matched_at', ''),
                    v.get('template_path', ''),
                    method,
                    body.replace('\n', ' ').replace('\r', ''),  # 清理换行符
                    poc_requests_text.replace('\n', ' ').replace('\r', '')[:500],  # 限制长度
                    v.get('timestamp', '')
                ])
        
        return True
    except Exception as e:
        print(f"[!] CSV 导出失败: {str(e)}")
        return False


def export_to_html(scan_record: dict, vulns: list, file_path: str) -> bool:
    """
    将扫描结果导出为美观的 HTML 报告
    特点：单条漏洞默认折叠，点击展开详情
    
    参数:
        scan_record: 扫描记录字典
        vulns: 漏洞结果列表
        file_path: 导出文件路径
        
    返回:
        是否导出成功
    """
    try:
        # 统计严重程度
        severity_count = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0, 'unknown': 0}
        for v in vulns:
            sev = v.get('severity', 'unknown').lower()
            if sev in severity_count:
                severity_count[sev] += 1
            else:
                severity_count['unknown'] += 1
        
        # 统计漏洞类型（用于图表）
        type_count = {'RCE': 0, 'SQLi': 0, 'XSS': 0, 'SSRF': 0, 'LFI': 0, '未授权': 0, '信息泄露': 0, '其他': 0}
        for v in vulns:
            tags = str(v.get('tags', '')).lower()
            poc_id = str(v.get('template_id', '')).lower()
            name = str(v.get('name', '')).lower()
            all_text = f"{tags} {poc_id} {name}"
            
            if any(k in all_text for k in ['rce', 'remote-code', 'command-execution', 'code-execution']):
                type_count['RCE'] += 1
            elif any(k in all_text for k in ['sqli', 'sql-injection', 'sql_injection']):
                type_count['SQLi'] += 1
            elif any(k in all_text for k in ['xss', 'cross-site-scripting']):
                type_count['XSS'] += 1
            elif 'ssrf' in all_text:
                type_count['SSRF'] += 1
            elif any(k in all_text for k in ['lfi', 'rfi', 'file-inclusion', 'path-traversal', 'file-read']):
                type_count['LFI'] += 1
            elif any(k in all_text for k in ['unauth', 'unauthorized', 'bypass', 'default-login']):
                type_count['未授权'] += 1
            elif any(k in all_text for k in ['exposure', 'disclosure', 'leak', 'info']):
                type_count['信息泄露'] += 1
            else:
                type_count['其他'] += 1
        
        # 扫描时间
        scan_time = scan_record.get('scan_time', '')[:19] if scan_record else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 生成漏洞条目 HTML
        vuln_items_html = ""
        for idx, v in enumerate(vulns, 1):
            # 解析 raw_json
            raw_data = {}
            try:
                if v.get('raw_json'):
                    raw_data = json.loads(v['raw_json'])
            except:
                pass
            
            sev = v.get('severity', 'unknown').lower()
            sev_class = f"severity-{sev}"
            sev_label = {'critical': '危急', 'high': '高危', 'medium': '中危', 'low': '低危', 'info': '信息'}.get(sev, '未知')
            
            # 提取请求信息
            full_request = raw_data.get('request', '')
            curl_command = raw_data.get('curl-command', '')
            response_data = raw_data.get('response', '')
            
            # 处理请求方法
            method = "GET"
            if full_request:
                first_line = full_request.split('\r\n')[0] if '\r\n' in full_request else full_request.split('\n')[0]
                if first_line:
                    parts = first_line.split(' ')
                    if parts:
                        method = parts[0]
            
            # === 从 POC 文件解析完整请求链 ===
            poc_requests_html = ""
            poc_path = v.get('template_path') or (raw_data.get('template-path') if raw_data else None)
            matched_url = v.get('matched_at', '')
            
            # 提取实际的 Hostname
            actual_hostname = ""
            actual_base_url = ""
            if matched_url:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(matched_url)
                    if parsed.port and parsed.port not in [80, 443]:
                        actual_hostname = f"{parsed.hostname}:{parsed.port}"
                    else:
                        actual_hostname = parsed.hostname or ""
                    actual_base_url = f"{parsed.scheme}://{actual_hostname}"
                except:
                    pass
            
            # 如果路径不存在，尝试根据 template_id 搜索 POC 文件
            if poc_path and not os.path.exists(poc_path):
                # 尝试在 poc_library 目录中搜索
                template_id = v.get('template_id', '')
                if template_id:
                    try:
                        from pathlib import Path
                        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        poc_library = Path(base_dir) / "poc_library"
                        # 搜索所有 YAML 文件
                        for yaml_file in poc_library.rglob("*.yaml"):
                            try:
                                import yaml
                                with open(yaml_file, 'r', encoding='utf-8') as pf:
                                    content = yaml.safe_load(pf)
                                    if content and content.get('id') == template_id:
                                        poc_path = str(yaml_file)
                                        break
                            except:
                                continue
                    except:
                        pass
            
            if poc_path and os.path.exists(poc_path):
                try:
                    import yaml
                    import re as regex_module
                    with open(poc_path, 'r', encoding='utf-8') as pf:
                        poc_content = yaml.safe_load(pf)
                    
                    # === 从 matched_url 或 Nuclei 实际请求中提取随机生成的变量值 ===
                    extracted_random_values = {}
                    
                    # 首先，从 POC 文件的 variables 和 extractors 部分获取变量名
                    poc_variable_names = []
                    poc_extractor_names = []
                    
                    # 获取 POC 中定义的变量及其默认值
                    if poc_content.get('variables'):
                        poc_variable_names = list(poc_content['variables'].keys())
                        # 将 POC 中定义的变量默认值加入替换字典
                        for var_name, var_value in poc_content['variables'].items():
                            if var_value is not None:
                                # 处理不同类型的值
                                if isinstance(var_value, (int, float)):
                                    extracted_random_values[var_name] = str(var_value)
                                elif isinstance(var_value, str):
                                    extracted_random_values[var_name] = var_value
                                else:
                                    extracted_random_values[var_name] = str(var_value)
                    
                    # 获取 POC 中的提取器名称
                    for item in poc_content.get('http', []):
                        extractors = item.get('extractors', [])
                        for ext in extractors:
                            if ext.get('name'):
                                poc_extractor_names.append(ext['name'])
                    
                    # 尝试从 matched_url 的路径中提取文件名（适用于文件上传类漏洞）
                    # 例如: /userfile/messageserv/402880f29a529b4d019bd10369fa2675.jsp -> 402880f29a529b4d019bd10369fa2675.jsp
                    if matched_url:
                        try:
                            from urllib.parse import urlparse
                            parsed_url = urlparse(matched_url)
                            url_path = parsed_url.path
                            path_parts = url_path.split('/')
                            if path_parts:
                                last_part = path_parts[-1]
                                # 提取完整文件名
                                if '.' in last_part:
                                    full_filename = last_part  # 例如 402880f29a529b4d019bd10369fa2675.jsp
                                    basename = last_part.rsplit('.', 1)[0]  # 例如 402880f29a529b4d019bd10369fa2675
                                    
                                    # 将文件名赋值给可能的提取器变量
                                    for ext_name in poc_extractor_names:
                                        if 'file' in ext_name.lower() or 'upload' in ext_name.lower() or 'path' in ext_name.lower():
                                            extracted_random_values[ext_name] = full_filename
                                    
                                    # 如果 POC 未明确定义提取器名，使用通用名称
                                    if 'uploadfile' not in extracted_random_values:
                                        extracted_random_values['uploadfile'] = full_filename
                                    
                                    # 检查是否看起来像随机生成的值
                                    if regex_module.match(r'^[a-zA-Z0-9]{6,50}$', basename):
                                        extracted_random_values['random_filename'] = basename
                                        extracted_random_values['rand_base(8)'] = basename
                                        # 也为 POC 中定义的变量赋值
                                        for var_name in poc_variable_names:
                                            if 'name' in var_name.lower() or 'user' in var_name.lower() or 'file' in var_name.lower():
                                                extracted_random_values[var_name] = basename
                        except:
                            pass
                    
                    # 从 Nuclei 记录的实际请求中提取变量值
                    if full_request:
                        try:
                            # 从请求中提取文件名（例如从 Content-Disposition: form-data; name="file"; filename="xxx.jsp"）
                            match = regex_module.search(r'filename="([^"]+)"', full_request)
                            if match:
                                actual_filename = match.group(1)
                                if '.' in actual_filename:
                                    basename = actual_filename.rsplit('.', 1)[0]
                                    for var_name in poc_variable_names:
                                        if var_name not in extracted_random_values:
                                            extracted_random_values[var_name] = basename
                            
                            # 从 Cookie 或其他请求头中提取 session 等值
                            match = regex_module.search(r'JSESSIONID=([a-zA-Z0-9]+)', full_request)
                            if match:
                                extracted_random_values['jsessionid'] = match.group(1)
                        except:
                            pass
                    
                    # 也尝试从 Nuclei 返回的 response 中提取（例如 CVE-2025-15503-gLCSDRzl）
                    if response_data and not extracted_random_values.get('random_filename'):
                        try:
                            match = regex_module.search(r'CVE-\d+-\d+-([a-zA-Z0-9]{6,12})', response_data)
                            if match:
                                extracted_random_values['random_filename'] = match.group(1)
                                extracted_random_values['rand_base(8)'] = match.group(1)
                        except:
                            pass
                    
                    http_section = poc_content.get('http', [])
                    if http_section:
                        request_steps = []
                        step_num = 1
                        
                        for item in http_section:
                            raw_requests = item.get('raw', [])
                            if raw_requests:
                                for raw_req in raw_requests:
                                    req_content = raw_req.strip()
                                    # 替换标准内置变量
                                    if actual_hostname:
                                        req_content = req_content.replace('{{Hostname}}', actual_hostname)
                                        req_content = req_content.replace('{{BaseURL}}', actual_base_url)
                                        req_content = req_content.replace('{{Host}}', actual_hostname)
                                        req_content = req_content.replace('{{RootURL}}', actual_base_url)
                                        # 提取并替换 Scheme、Port、Path
                                        try:
                                            from urllib.parse import urlparse
                                            parsed = urlparse(matched_url)
                                            req_content = req_content.replace('{{Scheme}}', parsed.scheme or 'http')
                                            req_content = req_content.replace('{{Port}}', str(parsed.port) if parsed.port else ('443' if parsed.scheme == 'https' else '80'))
                                            req_content = req_content.replace('{{Path}}', parsed.path or '/')
                                        except:
                                            pass
                                    
                                    # 替换提取到的随机变量（如 {{uploadfile}}, {{username}} 等）
                                    for var_name, var_value in extracted_random_values.items():
                                        req_content = req_content.replace('{{' + var_name + '}}', var_value)
                                    
                                    # 替换常见的 Nuclei 随机函数占位符
                                    # 例如 {{rand_base(8)}}, {{rand_int(1000,9999)}}, {{to_lower(rand_base(6))}} 等
                                    if extracted_random_values.get('random_filename'):
                                        random_val = extracted_random_values['random_filename']
                                        # 替换各种形式的随机函数
                                        req_content = regex_module.sub(
                                            r'\{\{rand_base\(\d+\)\}\}', 
                                            random_val, 
                                            req_content
                                        )
                                        req_content = regex_module.sub(
                                            r'\{\{to_lower\(rand_base\(\d+\)\)\}\}', 
                                            random_val.lower(), 
                                            req_content
                                        )
                                        req_content = regex_module.sub(
                                            r'\{\{to_upper\(rand_base\(\d+\)\)\}\}', 
                                            random_val.upper(), 
                                            req_content
                                        )
                                        # 替换其他随机字符串函数
                                        req_content = regex_module.sub(
                                            r'\{\{rand_text_alpha\(\d+\)\}\}', 
                                            random_val, 
                                            req_content
                                        )
                                        req_content = regex_module.sub(
                                            r'\{\{rand_text_alphanumeric\(\d+\)\}\}', 
                                            random_val, 
                                            req_content
                                        )
                                        req_content = regex_module.sub(
                                            r'\{\{rand_char\([^)]*\)\}\}', 
                                            random_val[:1] if random_val else 'x', 
                                            req_content
                                        )
                                    
                                    # 替换随机整数（使用固定值表示已替换）
                                    req_content = regex_module.sub(
                                        r'\{\{rand_int\(\d+,\s*\d+\)\}\}', 
                                        '[随机数]', 
                                        req_content
                                    )
                                    
                                    # 替换哈希函数（显示为占位符）
                                    req_content = regex_module.sub(
                                        r'\{\{md5\([^)]*\)\}\}', 
                                        '[MD5哈希]', 
                                        req_content
                                    )
                                    req_content = regex_module.sub(
                                        r'\{\{sha1\([^)]*\)\}\}', 
                                        '[SHA1哈希]', 
                                        req_content
                                    )
                                    req_content = regex_module.sub(
                                        r'\{\{sha256\([^)]*\)\}\}', 
                                        '[SHA256哈希]', 
                                        req_content
                                    )
                                    
                                    # 替换时间戳函数
                                    req_content = regex_module.sub(
                                        r'\{\{unix_time\(\)\}\}', 
                                        '[时间戳]', 
                                        req_content
                                    )
                                    
                                    # 检查是否仍有未替换的变量，添加标注
                                    remaining_vars = regex_module.findall(r'\{\{([^}]+)\}\}', req_content)
                                    if remaining_vars:
                                        # 尝试使用已有的值替换未知变量
                                        for var in remaining_vars:
                                            if extracted_random_values and 'random_filename' in extracted_random_values:
                                                req_content = req_content.replace(
                                                    '{{' + var + '}}', 
                                                    f"[{extracted_random_values['random_filename']}]"
                                                )
                                    
                                    request_steps.append({'step': step_num, 'content': req_content})
                                    step_num += 1
                            
                            if item.get('path') or item.get('method'):
                                req_method = item.get('method', 'GET')
                                
                                # 处理 Headers
                                headers = item.get('headers', {})
                                if headers is None:
                                    headers = {}
                                
                                headers_str = ""
                                # 自动补充 Host 头 (如果 YAML 中未定义)
                                if actual_hostname and not any(k.lower() == 'host' for k in headers.keys()):
                                    headers_str += f"\nHost: {actual_hostname}"

                                for key, value in headers.items():
                                    headers_str += f"\n{key}: {value}"
                                
                                # 处理 Body
                                body = item.get('body', '')
                                if body:
                                    # 简单处理 Body 中的变量替换
                                    for var_name, var_value in extracted_random_values.items():
                                        body = body.replace('{{' + var_name + '}}', var_value)
                                    
                                    # 自动补充 Content-Length
                                    if not any(k.lower() == 'content-length' for k in headers.keys()):
                                        try:
                                            # 计算字节长度
                                            content_len = len(body.encode('utf-8'))
                                            headers_str += f"\nContent-Length: {content_len}"
                                        except:
                                            headers_str += f"\nContent-Length: {len(body)}"
                                        
                                    body = f"\n\n{body}"
                                
                                paths = item.get('path', [])
                                if isinstance(paths, str):
                                    paths = [paths]
                                for path in paths:
                                    actual_path = path
                                    if actual_hostname:
                                        actual_path = actual_path.replace('{{Hostname}}', actual_hostname)
                                        actual_path = actual_path.replace('{{BaseURL}}', actual_base_url)
                                        actual_path = actual_path.replace('{{RootURL}}', actual_base_url)
                                    # 替换随机变量
                                    for var_name, var_value in extracted_random_values.items():
                                        actual_path = actual_path.replace('{{' + var_name + '}}', var_value)
                                    
                                    # 拼接完整请求内容
                                    full_content = f"{req_method} {actual_path}{headers_str}{body}"
                                    request_steps.append({'step': step_num, 'content': full_content})
                                    step_num += 1
                        
                        if len(request_steps) > 1:
                            import base64
                            poc_requests_html = '<div class="code-section"><h4>✅ POC 完整请求链 - 实际发送内容 (共{}个步骤)</h4>'.format(len(request_steps))
                            for req in request_steps:
                                # 转义 HTML 用于显示
                                escaped_content = req['content'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                # 使用 Base64 编码原始内容，避免特殊字符问题
                                raw_base64 = base64.b64encode(req['content'].encode('utf-8')).decode('ascii')
                                copy_btn_id = f"copy-step-{idx}-{req['step']}"
                                poc_requests_html += f'''<div style="margin-bottom:10px;position:relative;"><strong style="color:#3498db;">步骤 {req["step"]}</strong><button class="copy-btn" onclick="copyBase64Content('{raw_base64}', '{copy_btn_id}')" id="{copy_btn_id}">📋 复制</button><pre>{escaped_content}</pre></div>'''
                            poc_requests_html += '</div>'
                except:
                    pass
            
            # 转义 HTML 特殊字符并清理多余空行
            def escape_html(text, clean_empty_lines=False):
                if not text:
                    return ""
                result = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
                if clean_empty_lines:
                    # 清理连续的空行，保留单个换行
                    import re
                    result = re.sub(r'\r\n', '\n', result)  # 统一换行符
                    result = re.sub(r'\n{3,}', '\n\n', result)  # 最多保留一个空行
                    result = result.strip()
                return result
            
            vuln_items_html += f'''
            <div class="vuln-item">
                <div class="vuln-header" onclick="toggleVuln('vuln-{idx}')">
                    <span class="vuln-sev {sev_class}">{sev_label}</span>
                    <span class="vuln-id">{escape_html(v.get('template_id', '未知'))}</span>
                    <span class="vuln-target">{escape_html(v.get('matched_at', ''))}</span>
                    <span class="vuln-toggle" id="toggle-{idx}">▶</span>
                </div>
                <div class="vuln-detail" id="vuln-{idx}" style="display: none;">
                    <table class="detail-table">
                        <tr>
                            <th>严重程度</th>
                            <td>{sev_label} ({sev.upper()})</td>
                        </tr>
                        <tr>
                            <th>POC ID</th>
                            <td>{escape_html(v.get('template_id', ''))}</td>
                        </tr>
                        <tr>
                            <th>目标地址</th>
                            <td><a href="{escape_html(v.get('matched_at', ''))}" target="_blank">{escape_html(v.get('matched_at', ''))}</a></td>
                        </tr>
                        <tr>
                            <th>POC 路径</th>
                            <td>{escape_html(v.get('template_path', '') or raw_data.get('template-path', ''))}</td>
                        </tr>
                        <tr>
                            <th>发现时间</th>
                            <td>{escape_html(v.get('timestamp', ''))}</td>
                        </tr>
                    </table>
                    
                    {poc_requests_html}
                    {'<div class="code-section"><h4>触发漏洞的请求 (Nuclei 记录) <span style="font-size:11px;color:#7f8c8d;font-weight:normal;margin-left:10px;">(注: Nuclei 通常仅记录触发验证的最后一步请求，完整测试链请见上方)</span> <button class="copy-btn" onclick="copyPreContent(this)">📋 复制</button></h4><pre data-raw="' + full_request.replace('"', '&quot;').replace(chr(10), '&#10;').replace(chr(13), '&#13;') + '">' + escape_html(full_request, True) + '</pre></div>' if full_request else ''}
                    {'<div class="code-section"><h4>CURL 命令 <button class="copy-btn" onclick="copyPreContent(this)">📋 复制</button></h4><pre data-raw="' + curl_command.replace('"', '&quot;').replace(chr(10), '&#10;').replace(chr(13), '&#13;') + '">' + escape_html(curl_command, True) + '</pre></div>' if curl_command else ''}
                    {'<div class="code-section"><h4>响应数据</h4><pre>' + escape_html(response_data[:2000] + ('...(截断)' if len(response_data) > 2000 else ''), True) + '</pre></div>' if response_data else ''}
                </div>
            </div>
            '''
        
        # 生成完整 HTML
        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>漏洞扫描报告 - {scan_time}</title>
    <!-- Chart.js CDN 用于可视化图表 -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #e0e0e0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        /* 报告头部 */
        .report-header {{
            background: linear-gradient(135deg, #2d2d44 0%, #1f1f33 100%);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .report-title {{
            font-size: 28px;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 10px;
        }}
        
        .report-subtitle {{
            color: #a0a0a0;
            font-size: 14px;
        }}
        
        /* 统计卡片 */
        .stats-row {{
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .stat-card {{
            flex: 1;
            min-width: 150px;
            background: linear-gradient(135deg, #2d2d44 0%, #1f1f33 100%);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        
        .stat-card.critical {{
            border-left: 4px solid #9b59b6;
        }}
        
        .stat-card.high {{
            border-left: 4px solid #e74c3c;
        }}
        
        .stat-card.medium {{
            border-left: 4px solid #f39c12;
        }}
        
        .stat-card.low {{
            border-left: 4px solid #3498db;
        }}
        
        .stat-card.info {{
            border-left: 4px solid #1abc9c;
        }}
        
        .stat-card.total {{
            border-left: 4px solid #7f8c8d;
        }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: #ffffff;
        }}
        
        .stat-label {{
            font-size: 13px;
            color: #a0a0a0;
            margin-top: 5px;
        }}
        
        /* 漏洞列表 */
        .vuln-list {{
            background: linear-gradient(135deg, #2d2d44 0%, #1f1f33 100%);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .vuln-list h3 {{
            font-size: 18px;
            color: #ffffff;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .vuln-item {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            margin-bottom: 10px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .vuln-header {{
            display: flex;
            align-items: center;
            padding: 15px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .vuln-header:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .vuln-sev {{
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 15px;
            min-width: 50px;
            text-align: center;
        }}
        
        .severity-critical {{
            background: linear-gradient(135deg, #9b59b6, #8e44ad);
            color: white;
        }}
        
        .severity-high {{
            background: linear-gradient(135deg, #e74c3c, #c0392b);
            color: white;
        }}
        
        .severity-medium {{
            background: linear-gradient(135deg, #f39c12, #d68910);
            color: white;
        }}
        
        .severity-low {{
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
        }}
        
        .severity-info {{
            background: linear-gradient(135deg, #1abc9c, #16a085);
            color: white;
        }}
        
        .severity-unknown {{
            background: linear-gradient(135deg, #7f8c8d, #6c7a7d);
            color: white;
        }}
        
        .vuln-id {{
            font-weight: 600;
            color: #ffffff;
            margin-right: 15px;
            flex-shrink: 0;
        }}
        
        .vuln-target {{
            color: #a0a0a0;
            font-size: 13px;
            flex-grow: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .vuln-toggle {{
            color: #7f8c8d;
            font-size: 12px;
            transition: transform 0.3s;
        }}
        
        .vuln-toggle.expanded {{
            transform: rotate(90deg);
        }}
        
        .vuln-detail {{
            padding: 0 20px 20px 20px;
            background: rgba(0, 0, 0, 0.1);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .detail-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        
        .detail-table th,
        .detail-table td {{
            padding: 10px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .detail-table th {{
            width: 120px;
            color: #a0a0a0;
            font-weight: 500;
        }}
        
        .detail-table td {{
            color: #e0e0e0;
        }}
        
        .detail-table a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        .detail-table a:hover {{
            text-decoration: underline;
        }}
        
        .code-section {{
            margin-top: 15px;
        }}
        
        .code-section h4 {{
            font-size: 13px;
            color: #a0a0a0;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .copy-btn {{
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            border: none;
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            margin-left: 10px;
            transition: all 0.2s;
        }}
        
        .copy-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
        }}
        
        .copy-btn.copied {{
            background: linear-gradient(135deg, #3b82f6, #2563eb);
        }}
        
        .code-section pre {{
            background: #1a1a2e;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
            font-size: 12px;
            line-height: 1.5;
            color: #b0b0b0;
            white-space: pre;  /* 禁止自动换行，保持原始格式 */
            word-wrap: normal; /* 禁止强制断行 */
            max-height: 300px;
            overflow-y: auto;
        }}
        
        /* 页脚 */
        .report-footer {{
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 12px;
            margin-top: 20px;
        }}
        
        /* 无漏洞提示 */
        .no-vulns {{
            text-align: center;
            padding: 60px 20px;
            color: #7f8c8d;
        }}
        
        .no-vulns-icon {{
            font-size: 48px;
            margin-bottom: 15px;
        }}
        
        /* 按钮样式 */
        .btn-expand-all {{
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            margin-bottom: 15px;
            transition: all 0.2s;
        }}
        
        .btn-expand-all:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
        }}
        
        /* 图表区域样式 */
        .charts-row {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .chart-card {{
            flex: 1;
            min-width: 300px;
            background: linear-gradient(135deg, #2d2d44 0%, #1f1f33 100%);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .chart-card h4 {{
            font-size: 16px;
            color: #ffffff;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .chart-container {{
            position: relative;
            height: 250px;
            width: 100%;
        }}
        
        @media print {{
            body {{
                background: white;
                color: #333;
            }}
            
            .report-header, .stat-card, .vuln-list, .vuln-item {{
                background: white !important;
                box-shadow: none !important;
                border: 1px solid #ddd !important;
            }}
            
            .vuln-detail {{
                display: block !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 报告头部 -->
        <div class="report-header">
            <h1 class="report-title">🔒 漏洞扫描报告</h1>
            <p class="report-subtitle">扫描时间: {scan_time} | 目标数量: {scan_record.get('target_count', 0) if scan_record else 0} | POC 数量: {scan_record.get('poc_count', 0) if scan_record else 0}</p>
        </div>
        
        <!-- 统计卡片 -->
        <div class="stats-row">
            <div class="stat-card total">
                <div class="stat-value">{len(vulns)}</div>
                <div class="stat-label">漏洞总数</div>
            </div>
            <div class="stat-card critical">
                <div class="stat-value">{severity_count['critical']}</div>
                <div class="stat-label">危急</div>
            </div>
            <div class="stat-card high">
                <div class="stat-value">{severity_count['high']}</div>
                <div class="stat-label">高危</div>
            </div>
            <div class="stat-card medium">
                <div class="stat-value">{severity_count['medium']}</div>
                <div class="stat-label">中危</div>
            </div>
            <div class="stat-card low">
                <div class="stat-value">{severity_count['low']}</div>
                <div class="stat-label">低危</div>
            </div>
            <div class="stat-card info">
                <div class="stat-value">{severity_count['info']}</div>
                <div class="stat-label">信息</div>
            </div>
        </div>
        
        <!-- 可视化图表区域 -->
        <div class="charts-row">
            <div class="chart-card">
                <h4>📊 严重程度分布</h4>
                <div class="chart-container">
                    <canvas id="severityChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h4>🎯 漏洞类型分布</h4>
                <div class="chart-container">
                    <canvas id="typeChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- 漏洞列表 -->
        <div class="vuln-list">
            <h3>📋 漏洞详情列表</h3>
            {f'<button class="btn-expand-all" onclick="toggleAll()">展开全部 / 折叠全部</button>' if vulns else ''}
            
            {vuln_items_html if vulns else '<div class="no-vulns"><div class="no-vulns-icon">✅</div><p>本次扫描未发现漏洞</p></div>'}
        </div>
        
        <!-- 页脚 -->
        <div class="report-footer">
            <p>报告由 Nuclei GUI Scanner 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
    
    <script>
        function toggleVuln(id) {{
            const detail = document.getElementById(id);
            const toggle = document.getElementById('toggle-' + id.split('-')[1]);
            
            if (detail.style.display === 'none') {{
                detail.style.display = 'block';
                toggle.classList.add('expanded');
            }} else {{
                detail.style.display = 'none';
                toggle.classList.remove('expanded');
            }}
        }}
        
        let allExpanded = false;
        function toggleAll() {{
            const details = document.querySelectorAll('.vuln-detail');
            const toggles = document.querySelectorAll('.vuln-toggle');
            
            allExpanded = !allExpanded;
            
            details.forEach(detail => {{
                detail.style.display = allExpanded ? 'block' : 'none';
            }});
            
            toggles.forEach(toggle => {{
                if (allExpanded) {{
                    toggle.classList.add('expanded');
                }} else {{
                    toggle.classList.remove('expanded');
                }}
            }});
        }}
        
        // 解码 Base64 并复制
        function copyBase64Content(base64, btnId) {{
            try {{
                const binaryString = window.atob(base64);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {{
                    bytes[i] = binaryString.charCodeAt(i);
                }}
                const text = new TextDecoder().decode(bytes);
                copyToClipboard(text, btnId);
            }} catch (e) {{
                console.error('Base64 decoding failed', e);
                alert('复制失败：Base64解码错误');
            }}
        }}

        // 复制内容到剪贴板（用于步骤请求）
        function copyToClipboard(text, btnId) {{
            navigator.clipboard.writeText(text).then(() => {{
                const btn = document.getElementById(btnId);
                const originalText = btn.textContent;
                btn.textContent = '✅ 已复制';
                btn.classList.add('copied');
                setTimeout(() => {{
                    btn.textContent = originalText;
                    btn.classList.remove('copied');
                }}, 2000);
            }}).catch(err => {{
                // 降级方案：使用传统方法
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                const btn = document.getElementById(btnId);
                btn.textContent = '✅ 已复制';
                setTimeout(() => {{ btn.textContent = '📋 复制'; }}, 2000);
            }});
        }}
        
        // 从pre的data-raw属性复制原始内容
        function copyPreContent(btn) {{
            const pre = btn.closest('.code-section').querySelector('pre');
            let rawContent = pre.getAttribute('data-raw');
            if (rawContent) {{
                // 解码HTML实体
                rawContent = rawContent.replace(/&#10;/g, '\\n').replace(/&#13;/g, '\\r').replace(/&quot;/g, '"');
            }} else {{
                rawContent = pre.textContent;
            }}
            navigator.clipboard.writeText(rawContent).then(() => {{
                const originalText = btn.textContent;
                btn.textContent = '✅ 已复制';
                btn.classList.add('copied');
                setTimeout(() => {{
                    btn.textContent = originalText;
                    btn.classList.remove('copied');
                }}, 2000);
            }}).catch(err => {{
                const textarea = document.createElement('textarea');
                textarea.value = rawContent;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                btn.textContent = '✅ 已复制';
                setTimeout(() => {{ btn.textContent = '📋 复制'; }}, 2000);
            }});
        }}
        
        // 初始化图表
        function initCharts() {{
            // 严重程度数据
            const severityData = {{
                labels: ['危急', '高危', '中危', '低危', '信息'],
                datasets: [{{
                    data: [{severity_count['critical']}, {severity_count['high']}, {severity_count['medium']}, {severity_count['low']}, {severity_count['info']}],
                    backgroundColor: ['#9b59b6', '#e74c3c', '#f39c12', '#3498db', '#1abc9c'],
                    borderWidth: 0
                }}]
            }};
            
            // 漏洞类型数据
            const typeData = {{
                labels: {list(type_count.keys())},
                datasets: [{{
                    data: {list(type_count.values())},
                    backgroundColor: [
                        '#e74c3c', '#f39c12', '#27ae60', '#3498db', 
                        '#9b59b6', '#e67e22', '#1abc9c', '#7f8c8d'
                    ],
                    borderWidth: 0
                }}]
            }};
            
            // 通用配置
            const commonOptions = {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{
                            color: '#e0e0e0',
                            font: {{ size: 12 }}
                        }}
                    }}
                }}
            }};
            
            // 渲染严重程度图表
            const ctxSev = document.getElementById('severityChart');
            if (ctxSev) {{
                new Chart(ctxSev, {{
                    type: 'doughnut',
                    data: severityData,
                    options: {{
                        ...commonOptions,
                        cutout: '60%'
                    }}
                }});
            }}
            
            // 渲染类型图表
            const ctxType = document.getElementById('typeChart');
            if (ctxType) {{
                new Chart(ctxType, {{
                    type: 'pie',  // 使用饼图或柱状图
                    data: typeData,
                    options: commonOptions
                }});
            }}
        }}
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', initCharts);
    </script>
</body>
</html>
'''
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return True
    except Exception as e:
        print(f"[!] HTML 导出失败: {str(e)}")
        return False

