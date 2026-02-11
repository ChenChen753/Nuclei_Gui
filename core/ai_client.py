import requests
import json
import logging
from PyQt5.QtCore import QThread, pyqtSignal

class AIWorkerThread(QThread):
    """
    后台线程执行 AI 请求，避免阻塞 UI
    """
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, api_url, api_key, model, poc_name):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.poc_name = poc_name
    
    def run(self):
        try:
            client = AIClient(self.api_url, self.api_key, self.model)
            result = client.generate_fofa_rule(self.poc_name)
            self.result_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(f"发生错误: {str(e)}")

class AIClient:
    """
    简易 AI 客户端，用于连接 OpenAI 兼容接口 (如 DeepSeek, ChatGPT 等)
    """
    def __init__(self, api_url, api_key, model="deepseek-chat"):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        
    def generate_fofa_rule(self, poc_name):
        """
        根据 POC 名称生成 FOFA 语法
        """
        if not self.api_url or not self.api_key:
            return "错误: 请先配置 API 地址和密钥"
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 优化后的 Prompt，提供真实 FOFA 语法规则参考
        prompt = f"""你是一个资深网络安全专家。请根据漏洞/POC 名称："{poc_name}"，提供以下信息：

## 一、FOFA 搜索语法

请基于以下 **真实 FOFA 语法规则** 生成准确的查询语句：

**常用搜索字段：**
- `app="产品名"` - 搜索特定应用/框架（如 `app="Apache"`, `app="ThinkPHP"`）
- `title="关键词"` - 页面标题（如 `title="后台管理"`）
- `body="关键词"` - 页面内容（如 `body="Powered by"`）
- `header="关键词"` - HTTP 响应头（如 `header="X-Powered-By: PHP"`）
- `server="服务器"` - 服务器类型（如 `server="nginx"`）
- `port="端口"` - 端口号（如 `port="8080"`）
- `icon_hash="hash值"` - 网站图标哈希
- `cert="关键词"` - SSL 证书内容
- `protocol="协议"` - 协议类型（如 `protocol="https"`）

**逻辑运算符：** `&&`（与）、`||`（或）、`!`（非）

**输出格式要求：**
1. 提供 1-3 条推荐的 FOFA 语法（用代码块包裹）
2. 简要说明每条语法的搜索目标

## 二、漏洞利用/复现步骤

仅用于合法授权测试，请提供：
1. 漏洞原理简述
2. 验证步骤（Payload 用代码块展示）
3. 影响版本

**注意：** 请确保 FOFA 语法基于真实规则，避免使用不存在的搜索字段！"""
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful cybersecurity assistant."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        try:
            # 兼容 /v1/chat/completions
            endpoint = self.api_url
            if not endpoint.endswith("/chat/completions"):
                endpoint = f"{endpoint}/chat/completions"
                
            response = requests.post(endpoint, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return content
            else:
                return f"请求失败 (状态码 {response.status_code}): {response.text}"
                
        except Exception as e:
            return f"发生异常: {str(e)}"
    
    def _call_api(self, prompt: str, system_prompt: str = "You are a helpful cybersecurity assistant.") -> str:
        """通用 API 调用方法"""
        if not self.api_url or not self.api_key:
            return "错误: 请先配置 API 地址和密钥"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        try:
            endpoint = self.api_url
            if not endpoint.endswith("/chat/completions"):
                endpoint = f"{endpoint}/chat/completions"
            
            response = requests.post(endpoint, headers=headers, json=data, timeout=90)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"请求失败 (状态码 {response.status_code}): {response.text}"
        except Exception as e:
            return f"发生异常: {str(e)}"
    
    def generate_poc(self, vuln_description: str) -> str:
        """根据漏洞描述生成 Nuclei POC"""
        prompt = f"""你是一个 Nuclei POC 编写专家。请根据以下漏洞描述生成一个完整的 Nuclei YAML POC 模板：

漏洞描述：{vuln_description}

请生成符合 Nuclei 规范的 YAML POC，要求：

1. **基本信息**：
   - id: 唯一标识符（小写，用横线分隔）
   - name: 漏洞名称
   - author: your-name
   - severity: 严重程度 (critical/high/medium/low/info)
   - description: 详细描述
   - tags: 相关标签

2. **HTTP 请求**：
   - 合理的请求方法和路径
   - 必要的请求头和请求体
   - 使用 {{{{BaseURL}}}} 变量

3. **匹配规则**：
   - 使用 word/regex/status 匹配器
   - 设置合理的匹配条件

请直接输出完整的 YAML 代码，用代码块包裹。"""
        
        return self._call_api(prompt)
    
    def analyze_vulnerability(self, vuln_info: str) -> str:
        """分析漏洞影响和修复建议"""
        prompt = f"""你是一个资深安全分析师。请对以下漏洞进行深入分析：

漏洞信息：{vuln_info}

请提供以下分析内容：

## 一、漏洞概述
- 漏洞类型
- 危害等级
- 影响范围

## 二、技术分析
- 漏洞原理
- 利用条件
- 攻击向量

## 三、影响评估
- 对机密性的影响
- 对完整性的影响
- 对可用性的影响
- 潜在业务风险

## 四、修复建议
- 临时缓解措施
- 永久修复方案
- 安全加固建议

## 五、参考资料
- 相关 CVE 编号（如有）
- 官方安全公告
- 补丁下载链接

请尽量提供详细、专业的分析内容。"""
        
        return self._call_api(prompt)
    
    def recommend_pocs(self, target_info: str) -> str:
        """根据目标特征推荐 POC"""
        prompt = f"""你是一个渗透测试专家。根据以下目标信息，推荐可能适用的 Nuclei POC 类型：

目标信息：{target_info}

请分析并推荐：

## 一、目标识别
- 识别出的技术栈/框架
- 可能的服务/应用版本
- 潜在的攻击面

## 二、推荐 POC 类型
按优先级列出建议测试的漏洞类型：

1. **高优先级**
   - CVE 漏洞
   - 已知远程代码执行

2. **中优先级**  
   - 敏感信息泄露
   - 配置错误

3. **低优先级**
   - 信息收集
   - 版本探测

## 三、建议的 Nuclei 标签
推荐使用的 nuclei-templates 标签，例如：
- `tags: cve,rce,thinkphp`
- `tags: exposure,config`

## 四、注意事项
- 测试前的准备工作
- 需要特别关注的点"""
        
        return self._call_api(prompt)


class AIWorkerThreadV2(QThread):
    """
    通用 AI 后台线程
    支持不同类型的 AI 任务
    """
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    TASK_FOFA = "fofa"
    TASK_POC = "poc"
    TASK_ANALYZE = "analyze"
    TASK_RECOMMEND = "recommend"
    
    def __init__(self, api_url, api_key, model, task_type, content):
        super().__init__()
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.task_type = task_type
        self.content = content
    
    def run(self):
        try:
            client = AIClient(self.api_url, self.api_key, self.model)
            
            if self.task_type == self.TASK_FOFA:
                result = client.generate_fofa_rule(self.content)
            elif self.task_type == self.TASK_POC:
                result = client.generate_poc(self.content)
            elif self.task_type == self.TASK_ANALYZE:
                result = client.analyze_vulnerability(self.content)
            elif self.task_type == self.TASK_RECOMMEND:
                result = client.recommend_pocs(self.content)
            else:
                result = "未知任务类型"
            
            self.result_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(f"发生错误: {str(e)}")
