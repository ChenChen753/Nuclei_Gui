"""
FOFA API 客户端 - 支持第三方 API 接口
"""
import base64
import requests
from PyQt5.QtCore import QThread, pyqtSignal


class FofaSearchThread(QThread):
    """
    后台线程执行 FOFA 搜索，避免阻塞 UI
    """
    result_signal = pyqtSignal(list)      # 搜索结果列表
    error_signal = pyqtSignal(str)        # 错误信息
    progress_signal = pyqtSignal(str)     # 进度信息
    
    def __init__(self, api_url, email, api_key, query, page_size=100):
        super().__init__()
        self.api_url = api_url
        self.email = email
        self.api_key = api_key
        self.query = query
        self.page_size = page_size
    
    def run(self):
        try:
            self.progress_signal.emit("正在连接 FOFA API...")
            client = FofaClient(self.api_url, self.email, self.api_key)
            results = client.search(self.query, self.page_size)
            self.result_signal.emit(results)
        except Exception as e:
            self.error_signal.emit(f"搜索失败: {str(e)}")


class FofaClient:
    """
    FOFA API 客户端
    支持官方 API 和第三方兼容 API
    """
    
    def __init__(self, api_url: str, email: str, api_key: str):
        """
        初始化客户端
        :param api_url: API 地址（支持第三方接口）
        :param email: FOFA 邮箱（某些第三方可能不需要）
        :param api_key: API Key
        """
        self.api_url = api_url.rstrip('/')
        self.email = email
        self.api_key = api_key
    
    def search(self, query: str, size: int = 100) -> list:
        """
        执行 FOFA 搜索
        :param query: 搜索语句
        :param size: 返回结果数量
        :return: 搜索结果列表 [{"host": "xxx", "ip": "xxx", "port": "xxx", "title": "xxx"}, ...]
        """
        if not self.api_url or not self.api_key:
            raise ValueError("请先配置 FOFA API 地址和密钥")
        
        # Base64 编码查询语句
        query_b64 = base64.b64encode(query.encode('utf-8')).decode('utf-8')
        
        # 构建请求参数（兼容官方和大多数第三方 API）
        params = {
            "qbase64": query_b64,
            "size": size,
            "fields": "host,ip,port,title,protocol"
        }
        
        # 根据 API 类型添加认证参数
        if self.email:
            params["email"] = self.email
            params["key"] = self.api_key
        else:
            # 某些第三方 API 只需要 key
            params["key"] = self.api_key
        
        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查错误
            if data.get("error"):
                raise ValueError(data.get("errmsg", "未知错误"))
            
            # 解析结果
            results = []
            raw_results = data.get("results", [])
            
            for item in raw_results:
                # 兼容不同格式的返回数据
                if isinstance(item, list):
                    # 官方格式: [host, ip, port, title, protocol]
                    result = {
                        "host": item[0] if len(item) > 0 else "",
                        "ip": item[1] if len(item) > 1 else "",
                        "port": item[2] if len(item) > 2 else "",
                        "title": item[3] if len(item) > 3 else "",
                        "protocol": item[4] if len(item) > 4 else ""
                    }
                elif isinstance(item, dict):
                    # 某些第三方返回字典格式
                    result = {
                        "host": item.get("host", ""),
                        "ip": item.get("ip", ""),
                        "port": str(item.get("port", "")),
                        "title": item.get("title", ""),
                        "protocol": item.get("protocol", "")
                    }
                else:
                    continue
                
                results.append(result)
            
            return results
            
        except requests.RequestException as e:
            raise ValueError(f"网络请求失败: {str(e)}")
        except Exception as e:
            raise ValueError(f"解析响应失败: {str(e)}")
    
    def test_connection(self) -> bool:
        """
        测试 API 连接是否正常
        :return: 是否连接成功
        """
        try:
            # 使用简单查询测试连接
            results = self.search("port=80", size=1)
            return True
        except:
            return False
