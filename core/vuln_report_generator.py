"""
漏洞报告生成器 - 用于生成补天SRC格式的漏洞报告
"""
import os
import yaml
import json
from datetime import datetime
from urllib.parse import urlparse


class VulnReportGenerator:
    """漏洞报告生成器"""
    
    def __init__(self):
        # 危险等级映射
        self.severity_map = {
            'critical': '严重',
            'high': '高危',
            'medium': '中危',
            'low': '低危',
            'info': '信息',
            'unknown': '未知'
        }
        
        # 漏洞类型识别规则 (标签关键词 -> 漏洞类型)
        self.type_rules = [
            (['sqli', 'sql-injection', 'sql注入'], 'SQL注入'),
            (['xss', 'cross-site-scripting', '跨站脚本'], 'XSS跨站脚本'),
            (['rce', 'command-injection', 'code-execution', '命令执行', '代码执行'], '远程命令执行'),
            (['file-upload', 'upload', '文件上传'], '任意文件上传'),
            (['ssrf', '请求伪造'], 'SSRF服务端请求伪造'),
            (['lfi', 'path-traversal', 'file-inclusion', '文件包含', '路径遍历'], '文件包含/路径遍历'),
            (['auth-bypass', 'unauthorized', '认证绕过', '越权'], '越权访问/认证绕过'),
            (['info-disclosure', 'exposure', '信息泄露', '敏感信息'], '信息泄露'),
            (['default-login', 'weak-password', '弱口令', '默认密码'], '弱口令/默认密码'),
            (['xxe', 'xml-external-entity'], 'XXE外部实体注入'),
            (['unauth', 'redis', 'mongodb', 'elasticsearch', '未授权'], '未授权访问'),
            (['deserialization', 'fastjson', 'shiro', '反序列化'], '反序列化漏洞'),
            (['csrf', '跨站请求伪造'], 'CSRF跨站请求伪造'),
        ]
        
        # 危害描述模板
        self.harm_templates = {
            'SQL注入': '''攻击者可利用此SQL注入漏洞实施以下攻击：
1. 【数据泄露】未经授权访问数据库中的敏感数据，包括用户凭据、个人信息、信用卡详细信息、商业机密等
2. 【数据篡改】修改、插入或删除数据库中的记录，导致数据完整性受损
3. 【权限绕过】绕过应用程序的认证和授权机制，以管理员身份登录系统
4. 【远程代码执行】在某些数据库系统中可升级为执行操作系统命令，获取服务器Shell权限
5. 【内网渗透】通过数据库服务器作为跳板进一步攻击内部网络
6. 【拒绝服务】通过锁定记录或删除数据库表导致服务不可用''',

            'XSS跨站脚本': '''攻击者可利用此XSS漏洞实施以下攻击：
1. 【会话劫持】窃取用户的Cookie和会话信息，伪造用户身份执行非法操作
2. 【钓鱼攻击】篡改网页内容，诱导用户点击恶意链接，窃取用户敏感信息
3. 【恶意软件传播】在用户浏览器中传播恶意软件或进行DDoS攻击
4. 【页面篡改】破坏或篡改网页内容，影响网站的正常功能和用户体验
5. 【蠕虫传播】通过注入恶意脚本传播XSS蠕虫，扩大攻击范围
6. 【后台权限获取】在某些严重情况下可能导致后台管理权限被窃取''',

            '远程命令执行': '''攻击者可利用此远程命令执行漏洞实施以下攻击：
1. 【完全控制系统】在目标服务器上执行任意系统命令，获取服务器完全控制权
2. 【敏感数据窃取】访问并窃取系统中的账户凭据、密码、财务数据和其他机密资料
3. 【恶意软件部署】向受害系统部署病毒、木马、勒索软件等恶意程序
4. 【后门植入】在系统中植入后门，实现持续访问和控制
5. 【内网横向渗透】以受控服务器为跳板，窃取登录凭证，扩大内网访问权限
6. 【服务中断】发起拒绝服务攻击，删除重要数据，导致业务系统瘫痪
7. 【僵尸网络】将被控服务器用于构建僵尸网络或进行加密货币挖矿''',

            '任意文件上传': '''攻击者可利用此文件上传漏洞实施以下攻击：
1. 【获取服务器权限】上传恶意脚本文件（Webshell），在服务器上执行任意代码，获取服务器控制权限
2. 【系统文件篡改】利用目录跳转上传文件覆盖系统关键文件
3. 【拒绝服务攻击】上传大文件或高频上传导致服务器资源耗尽
4. 【钓鱼攻击】上传恶意HTML页面进行钓鱼攻击，非法获取用户信息
5. 【恶意SEO】上传包含恶意JavaScript代码的页面进行黑帽SEO
6. 【内网渗透】以Webshell为跳板进一步渗透内网系统''',

            'SSRF服务端请求伪造': '''攻击者可利用此SSRF漏洞实施以下攻击：
1. 【内网探测】获取服务器所在内网信息，进行端口扫描，获取开放服务信息
2. 【攻击内网服务】对内网应用发起攻击，如Redis未授权访问、Struts2漏洞利用等
3. 【绕过防火墙】利用服务器作为跳板，访问外网无法直接访问的内部系统
4. 【读取本地文件】利用file://协议读取服务器本地敏感文件
5. 【识别内网应用】通过访问内网应用默认文件，识别Web应用类型和版本
6. 【拒绝服务】通过请求大文件或维持长时间连接造成服务拒绝''',

            '文件包含/路径遍历': '''攻击者可利用此文件包含漏洞实施以下攻击：
1. 【敏感信息泄露】读取服务器敏感文件，如配置文件、用户凭据、数据库内容、源代码等
2. 【远程代码执行】结合文件上传或日志投毒技术实现远程代码执行
3. 【权限提升】利用漏洞提升在Web应用程序中的权限
4. 【系统破坏】严重情况下可能导致系统被完全控制、数据被破坏
5. 【跨站脚本】可能导致XSS漏洞的产生
6. 【会话劫持】读取PHP会话文件获取用户会话信息''',

            '越权访问/认证绕过': '''攻击者可利用此越权访问漏洞实施以下攻击：
1. 【水平越权】访问其他拥有相同权限用户的敏感数据和资源
2. 【垂直越权】低权限用户执行高权限操作，如普通用户执行管理员功能
3. 【未授权访问】绕过认证机制直接访问受保护的功能和数据
4. 【敏感数据泄露】查看、修改或删除其他用户的个人信息和业务数据
5. 【业务逻辑绕过】绕过正常的业务流程执行非法操作
6. 【账户接管】可能导致其他用户账户被完全控制''',

            '信息泄露': '''攻击者可利用此信息泄露漏洞实施以下攻击：
1. 【敏感数据获取】获取系统配置信息、数据库连接信息、API密钥等敏感数据
2. 【进一步攻击】利用泄露的信息为后续攻击提供情报支持
3. 【社会工程】利用泄露的用户信息进行针对性的社会工程攻击
4. 【密码破解】获取密码哈希后进行离线破解
5. 【业务影响】商业机密泄露可能造成重大经济损失
6. 【合规风险】用户数据泄露可能导致法律诉讼和监管处罚''',

            '弱口令/默认密码': '''攻击者可利用此弱口令漏洞实施以下攻击：
1. 【系统入侵】使用默认密码或弱密码直接登录系统后台
2. 【权限获取】获取管理员或其他高权限账户的访问权限
3. 【数据窃取】访问并窃取系统中的敏感业务数据和用户信息
4. 【系统控制】修改系统配置，植入后门，实现持久化访问
5. 【横向移动】利用获取的凭据尝试登录其他系统或服务
6. 【业务破坏】恶意修改或删除业务数据，造成服务中断''',

            'XXE外部实体注入': '''攻击者可利用此XXE漏洞实施以下攻击：
1. 【本地文件读取】利用外部实体读取服务器本地敏感文件
2. 【SSRF攻击】利用XXE发起服务端请求伪造攻击，扫描内网
3. 【拒绝服务】通过递归实体引用（十亿笑声攻击）导致服务器资源耗尽
4. 【远程代码执行】在特定配置下可能实现远程代码执行
5. 【端口探测】探测内网主机的开放端口
6. 【数据外传】将敏感数据通过外部请求发送到攻击者控制的服务器''',

            '未授权访问': '''攻击者可利用此未授权访问漏洞实施以下攻击：
1. 【敏感数据泄露】无需认证即可访问数据库/服务中存储的所有敏感数据
2. 【数据篡改删除】随意修改或删除系统中的关键业务数据，如执行FLUSHALL清空数据库
3. 【远程代码执行】利用Redis写入SSH公钥或Webshell，获取服务器控制权限
4. 【权限提升】若服务以root运行，可直接获取系统最高权限
5. 【植入后门】写入计划任务或后门程序，实现持久化访问
6. 【内网渗透】以受控服务为跳板，进一步渗透内网其他系统
7. 【拒绝服务】发送大量命令或清空数据导致服务不可用''',

            '反序列化漏洞': '''攻击者可利用此反序列化漏洞实施以下攻击：
1. 【远程代码执行】通过构造恶意序列化数据在服务器上执行任意系统命令
2. 【完全控制系统】获取服务器Shell权限，完全控制目标系统
3. 【数据篡改】修改反序列化后的对象数据，篡改应用程序敏感信息
4. 【权限提升】通过修改对象属性获得超出应有范围的权限
5. 【任意文件读写】利用漏洞链读取或写入服务器任意文件
6. 【拒绝服务】构造恶意数据导致应用程序崩溃或资源耗尽
7. 【JNDI注入】触发远程类加载，从攻击者服务器加载恶意代码''',

            'CSRF跨站请求伪造': '''攻击者可利用此CSRF漏洞实施以下攻击：
1. 【非法操作】冒充用户执行修改密码、转账、发帖等敏感操作
2. 【账户劫持】诱导用户绑定攻击者账户或修改安全设置
3. 【数据篡改】利用用户身份修改个人资料、业务数据等
4. 【会话劫持】窃取用户会话令牌，进一步控制用户账户
5. 【蠕虫传播】在社交平台利用CSRF传播恶意链接
6. 【信誉损害】以用户名义发布不当内容，损害用户和平台信誉''',
        }
        
        # 修复建议模板
        self.fix_templates = {
            'SQL注入': '''1. 【参数化查询】使用预编译语句（PreparedStatement/PDO）将SQL代码与用户输入严格分离
2. 【输入验证】对用户输入进行严格的类型、长度和业务合法性验证，采用白名单机制
3. 【特殊字符转义】对无法参数化的场景，确保对所有用户输入进行正确转义
4. 【最小权限】限制数据库账户权限，禁止使用root/sa等高权限账户
5. 【禁用危险函数】禁用xp_cmdshell等高危存储过程
6. 【错误信息处理】生产环境禁用详细错误信息，使用统一错误页面
7. 【部署WAF】使用Web应用防火墙拦截SQL注入攻击
8. 【使用ORM】采用Hibernate、SQLAlchemy等ORM框架自动处理查询绑定''',

            'XSS跨站脚本': '''1. 【输入验证】对所有用户输入进行严格的白名单验证，过滤<script>、onerror等危险标签
2. 【输出编码】根据输出上下文（HTML/JavaScript/URL）对特殊字符进行正确编码转义
3. 【CSP策略】配置Content-Security-Policy响应头，限制可执行脚本来源
4. 【HttpOnly】为敏感Cookie设置HttpOnly属性，防止JavaScript访问
5. 【X-Frame-Options】配置X-Frame-Options防止点击劫持攻击
6. 【使用安全库】使用DOMPurify等安全库清理不受信任的HTML内容
7. 【前端框架】使用React/Vue等框架的自动转义特性
8. 【代码审查】定期进行代码审计和自动化安全扫描''',

            '远程命令执行': '''1. 【输入验证过滤】对所有用户输入进行严格检测和过滤，防止命令注入
2. 【避免危险函数】减少或避免使用eval()、system()、exec()等可能导致命令执行的函数
3. 【及时更新】定期将操作系统、应用程序、框架升级到最新安全版本
4. 【最小权限】将应用程序运行权限限制在最低必要级别
5. 【部署WAF】使用Web应用防火墙检测和拦截恶意请求
6. 【网络隔离】配置防火墙规则封堵高危URL，实施网络分段隔离关键系统
7. 【安全配置】对框架和应用进行安全加固配置
8. 【定期审计】持续进行安全监控、渗透测试和代码审查''',

            '任意文件上传': '''1. 【白名单校验】服务器端严格采用白名单机制校验文件扩展名
2. 【MIME检查】对上传文件进行MIME类型验证
3. 【内容检测】使用系统函数验证文件内容的真实性
4. 【文件重命名】使用随机字符串重命名文件，禁止包含路径字符
5. 【大小限制】设置合理的文件上传大小限制
6. 【目录权限】上传目录禁用执行权限，隐藏真实路径
7. 【隔离存储】将上传文件存储到独立的静态存储服务器
8. 【病毒扫描】对上传文件进行病毒扫描
9. 【更新组件】确保Web服务器和处理组件不存在解析漏洞''',

            'SSRF服务端请求伪造': '''1. 【白名单机制】实施严格的白名单策略，限制服务器只能向预定义的域名/IP发起请求
2. 【IP校验】对外部传入的域名进行DNS解析，校验是否为内网IP，拒绝内网地址请求
3. 【禁用重定向】关闭自动跟随HTTP 30x重定向
4. 【物理隔离】设置专门的下载代理服务，与核心业务系统物理隔离
5. 【协议限制】限制请求协议，禁用file://、gopher://等危险协议
6. 【URL过滤】清除URL中可能被利用的特殊字符
7. 【Host设置】请求时明确设置Host Header为目标IP''',

            '文件包含/路径遍历': '''1. 【输入验证】对文件路径参数进行严格的白名单验证
2. 【禁止特殊字符】过滤../、..\\等目录遍历字符
3. 【使用绝对路径】使用绝对路径而非相对路径引用文件
4. 【限制文件范围】将可包含的文件限制在特定目录下
5. 【禁用远程包含】PHP环境下禁用allow_url_include
6. 【权限控制】限制Web应用对文件系统的访问权限
7. 【日志监控】监控异常的文件访问行为''',

            '越权访问/认证绕过': '''1. 【服务端验证】在服务器端对所有受保护资源进行严格的授权检查
2. 【最小权限】确保用户仅拥有执行其职责所需的最低权限
3. 【定期审计】定期检查用户权限，移除不再需要的权限
4. 【默认拒绝】默认情况下拒绝所有访问，只授予明确允许的权限
5. 【会话管理】使用短生命周期令牌、安全Cookie、多因素认证
6. 【不信任用户ID】将用户控制的ID视为不可信数据，进行服务端验证
7. 【日志告警】实施日志记录和异常访问告警机制
8. 【资源ID随机化】对敏感资源ID进行随机化处理''',

            '信息泄露': '''1. 【错误处理】生产环境禁用详细错误信息，使用统一错误页面
2. 【注释清理】上线前清理代码注释和调试信息
3. 【目录保护】禁用目录浏览，保护敏感目录
4. 【文件权限】正确设置敏感文件的访问权限
5. 【响应头配置】配置安全响应头，移除服务器版本信息
6. 【日志保护】敏感日志文件禁止Web访问
7. 【加密存储】敏感数据加密存储和传输
8. 【定期扫描】使用自动化工具定期扫描信息泄露风险''',

            '弱口令/默认密码': '''1. 【修改默认密码】首次部署时强制修改所有默认密码
2. 【密码策略】实施强密码策略：长度≥8位，包含大小写字母、数字、特殊字符
3. 【账户锁定】多次登录失败后锁定账户
4. 【双因素认证】敏感系统启用双因素认证
5. 【定期更换】要求定期更换密码
6. 【密码审计】使用工具定期检测弱密码账户
7. 【禁用通用账户】禁用admin、test等通用账户名
8. 【安全存储】密码使用bcrypt等安全算法哈希存储''',

            'XXE外部实体注入': '''1. 【禁用外部实体】在XML解析器中禁用外部实体和DTD处理
2. 【使用安全库】使用不解析外部实体的安全XML库
3. 【输入验证】对XML输入进行严格验证和过滤
4. 【使用JSON】如无必要，优先使用JSON替代XML
5. 【更新组件】及时更新XML解析库到最新版本
6. 【WAF防护】部署WAF拦截XXE攻击载荷
7. 【限制文件访问】限制XML解析进程的文件系统访问权限''',

            '未授权访问': '''1. 【启用认证】为Redis/MongoDB/Elasticsearch等服务配置强密码认证
2. 【绑定IP】将服务绑定到本地地址(127.0.0.1)或指定可信IP
3. 【防火墙规则】配置防火墙限制服务端口只允许可信IP访问
4. 【保护模式】启用Redis的protected-mode等内置保护机制
5. 【禁用高危命令】重命名或禁用CONFIG、FLUSHALL等危险命令
6. 【非root运行】使用低权限账户运行数据库服务
7. 【网络隔离】将数据库服务部署在内网，禁止直接暴露公网
8. 【定期审计】监控异常访问行为，启用访问日志''',

            '反序列化漏洞': '''1. 【避免不可信数据】不反序列化来自不可信来源的数据
2. 【白名单验证】实现反序列化类的白名单机制，只允许安全的类
3. 【升级组件】将Fastjson、Shiro、Commons Collections等组件升级到安全版本
4. 【禁用危险方法】在应用中禁用或限制可能被恶意利用的方法
5. 【使用安全格式】用JSON/XML等更安全的格式替代原生序列化
6. 【修改默认密钥】对Shiro等框架修改默认加密密钥
7. 【WAF防护】部署WAF检测包含可疑序列化特征的请求
8. 【RASP防护】使用运行时应用自保护技术拦截恶意反序列化''',

            'CSRF跨站请求伪造': '''1. 【CSRF Token】在敏感操作的表单/请求中加入随机Token并验证
2. 【验证Referer】检查请求的Referer/Origin头是否来自可信域名
3. 【SameSite Cookie】为Cookie设置SameSite属性(Lax/Strict)
4. 【二次验证】敏感操作要求重新输入密码或验证码
5. 【用户交互】关键操作增加确认步骤，如弹窗确认
6. 【短生命周期Token】使用短有效期的会话Token
7. 【及时退出】提醒用户使用后及时退出登录
8. 【定期审计】定期进行安全扫描发现CSRF漏洞''',
        }
        
        # 默认模板
        self.default_harm = '''攻击者可利用此漏洞实施以下攻击：
1. 【安全风险】可能导致系统安全性降低
2. 【数据风险】可能造成敏感数据泄露或被篡改
3. 【业务影响】可能影响正常业务运行'''

        self.default_fix = '''1. 【漏洞修复】及时修复相关漏洞
2. 【安全加固】对系统进行安全加固
3. 【监控告警】部署安全监控和告警机制
4. 【定期检查】定期进行安全检查和渗透测试'''

    def identify_vuln_type(self, poc_data: dict) -> str:
        """
        根据POC数据识别漏洞类型
        
        参数:
            poc_data: POC模板数据(字典)或漏洞结果数据
            
        返回:
            识别出的漏洞类型
        """
        # 收集所有可用的标签和关键词
        keywords = []
        
        # 从info.tags获取
        info = poc_data.get('info', {})
        if isinstance(info, dict):
            tags = info.get('tags', [])
            if isinstance(tags, str):
                keywords.extend(tags.lower().split(','))
            elif isinstance(tags, list):
                keywords.extend([str(t).lower() for t in tags])
            
            # 从info.classification获取
            classification = info.get('classification', {})
            if isinstance(classification, dict):
                cve_id = classification.get('cve-id', '')
                cwe_id = classification.get('cwe-id', [])
                if cwe_id:
                    keywords.extend([str(c).lower() for c in cwe_id] if isinstance(cwe_id, list) else [str(cwe_id).lower()])
            
            # 从info.name获取关键词
            name = info.get('name', '')
            if name:
                keywords.append(str(name).lower())
        
        # 从template-id获取
        template_id = poc_data.get('template-id', poc_data.get('id', ''))
        if template_id:
            keywords.append(str(template_id).lower())
        
        # 匹配漏洞类型
        for rule_keywords, vuln_type in self.type_rules:
            for kw in rule_keywords:
                kw_lower = kw.lower()
                for keyword in keywords:
                    if kw_lower in str(keyword):
                        return vuln_type
        
        return '其他漏洞'

    def get_harm_description(self, vuln_type: str) -> str:
        """获取漏洞危害描述"""
        return self.harm_templates.get(str(vuln_type), self.default_harm)

    def get_fix_suggestion(self, vuln_type: str) -> str:
        """获取修复建议"""
        return self.fix_templates.get(str(vuln_type), self.default_fix)

    def parse_poc_file(self, poc_path: str) -> dict:
        """
        解析POC文件
        
        参数:
            poc_path: POC文件路径
            
        返回:
            POC数据字典
        """
        try:
            if os.path.exists(poc_path):
                with open(poc_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            print(f"解析POC文件失败: {e}")
        return {}

    def extract_request_info(self, poc_data: dict) -> dict:
        """
        从POC提取请求信息
        
        参数:
            poc_data: POC数据字典
            
        返回:
            请求信息字典
        """
        request_info = {
            'method': 'GET',
            'path': '',
            'headers': {},
            'body': ''
        }
        
        # 获取http请求信息
        http = poc_data.get('http', poc_data.get('requests', []))
        if isinstance(http, list) and len(http) > 0:
            req = http[0]
            request_info['method'] = req.get('method', 'GET')
            
            # 获取路径
            path = req.get('path', [])
            if isinstance(path, list) and len(path) > 0:
                request_info['path'] = path[0]
            elif isinstance(path, str):
                request_info['path'] = path
            
            # 获取请求头
            request_info['headers'] = req.get('headers', {})
            
            # 获取请求体
            request_info['body'] = req.get('body', '')
        
        return request_info

    def generate_report(self, vuln_data: dict, poc_path: str = None) -> str:
        """
        生成补天格式的漏洞报告 (新模板)
        
        参数:
            vuln_data: 漏洞结果数据
            poc_path: POC模板文件路径
            
        返回:
            Markdown 格式的漏洞报告
        """
        # 解析POC文件获取更多信息
        poc_data = {}
        if poc_path:
            poc_data = self.parse_poc_file(poc_path)
        
        # 合并数据
        merged_data = {**poc_data, **vuln_data}
        
        # 解析 raw_json
        raw_json = vuln_data.get('raw_json', '')
        raw_request = ""
        curl_command = ""
        if raw_json and isinstance(raw_json, str):
            try:
                raw_data_parsed = json.loads(raw_json)
                merged_data.update(raw_data_parsed)
                raw_request = raw_data_parsed.get('request', '')
                curl_command = raw_data_parsed.get('curl-command', '')
            except:
                pass
        
        # 1. 基础信息提取
        info = merged_data.get('info', {})
        template_id = merged_data.get('template-id', merged_data.get('template_id', ''))
        matched_at = merged_data.get('matched-at', merged_data.get('matched_at', ''))
        
        # 严重等级
        severity = merged_data.get('severity', info.get('severity', 'unknown'))
        severity_cn = self.severity_map.get(str(severity).lower() if severity else 'unknown', '未知')
        
        # 漏洞类型
        vuln_type = self.identify_vuln_type(merged_data)
        
        # 2. URL 处理 (区分 漏洞URL 和 Payload)
        # 漏洞URL: 默认的正常访问地址 (去除参数)
        base_url = matched_at
        try:
            parsed = urlparse(matched_at)
            # 重新构建不带 query 的 URL
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            domain = parsed.netloc
        except:
            domain = matched_at
            
        # 3. Payload 处理
        # 如果有完整请求包，优先使用完整请求包
        # 否则使用 matched_at (通常包含 Payload)
        payload_content = ""
        if raw_request:
            payload_content = raw_request
        elif curl_command:
            payload_content = curl_command
        else:
            payload_content = matched_at  # 如果没有 raw request，matched_at 通常就是带 payload 的 url

        # 4. 漏洞标题
        vuln_name = info.get('name', template_id) if isinstance(info, dict) else template_id
        # 移除可能存在的非法文件名字符
        title = f"{domain}存在{vuln_name}"
        
        # 5. 生成报告 (Markdown 表格格式)
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        report = f'''# 漏洞报告

## 一、 漏洞概述

| **描述** | **内容** |
| :--- | :--- |
| **标题** | {title} |
| **漏洞报送时间** | {current_date} |
| **漏洞单位** | {domain} |
| **漏洞分类** | {vuln_type} |
| **漏洞类型** | Web漏洞 |
| **漏洞等级** | {severity_cn} |
| **URL地址** | {base_url} |

## 二、 漏洞说明

### 描述漏洞过程
{self.get_harm_description(vuln_type)}

### Payload
```http
{payload_content}
```

## 三、 修复建议

```text
{self.get_fix_suggestion(vuln_type)}
```
'''
        return report


# 全局单例
_generator_instance = None

def get_report_generator() -> VulnReportGenerator:
    """获取报告生成器单例"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = VulnReportGenerator()
    return _generator_instance
