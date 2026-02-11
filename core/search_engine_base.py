"""
搜索引擎抽象基类 - 定义统一的搜索接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from PyQt5.QtCore import QThread, pyqtSignal


@dataclass
class SearchResult:
    """搜索结果数据类"""
    ip: str = ""
    port: int = 0
    domain: str = ""
    url: str = ""
    title: str = ""
    banner: str = ""
    protocol: str = ""
    country: str = ""
    region: str = ""
    city: str = ""
    isp: str = ""
    os: str = ""
    server: str = ""
    extra: Dict = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}
    
    def to_dict(self) -> Dict:
        return {
            'ip': self.ip,
            'port': self.port,
            'domain': self.domain,
            'url': self.url,
            'title': self.title,
            'banner': self.banner,
            'protocol': self.protocol,
            'country': self.country,
            'region': self.region,
            'city': self.city,
            'isp': self.isp,
            'os': self.os,
            'server': self.server,
            'extra': self.extra,
        }
    
    def get_target_url(self) -> str:
        """获取可用于扫描的目标 URL"""
        if self.url:
            return self.url
        if self.domain:
            protocol = self.protocol or 'http'
            if self.port and self.port not in [80, 443]:
                return f"{protocol}://{self.domain}:{self.port}"
            return f"{protocol}://{self.domain}"
        if self.ip:
            protocol = self.protocol or 'http'
            if self.port and self.port not in [80, 443]:
                return f"{protocol}://{self.ip}:{self.port}"
            return f"{protocol}://{self.ip}"
        return ""


class SearchEngineBase(ABC):
    """搜索引擎抽象基类"""
    
    # 引擎名称
    name: str = "BaseEngine"
    # 引擎显示名称
    display_name: str = "基础引擎"
    
    def __init__(self, api_key: str = "", api_url: str = "", **kwargs):
        """
        初始化搜索引擎
        
        参数:
            api_key: API 密钥
            api_url: API 地址（可选，某些引擎有默认地址）
            **kwargs: 其他参数（如 email 等）
        """
        self.api_key = api_key
        self.api_url = api_url
        self.extra_config = kwargs
    
    @abstractmethod
    def search(self, query: str, page: int = 1, page_size: int = 100) -> Dict:
        """
        执行搜索
        
        参数:
            query: 搜索语句
            page: 页码（从1开始）
            page_size: 每页结果数
        
        返回:
            {
                'success': bool,
                'total': int,  # 总结果数
                'results': List[SearchResult],
                'error': str,  # 错误信息（如有）
            }
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict:
        """
        测试 API 连接
        
        返回:
            {
                'success': bool,
                'message': str,
                'quota': dict,  # 配额信息（如有）
            }
        """
        pass
    
    def get_config_fields(self) -> List[Dict]:
        """
        获取配置字段列表（用于 UI 生成配置表单）
        
        返回:
            [
                {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True},
                {'name': 'email', 'label': '邮箱', 'type': 'text', 'required': False},
            ]
        """
        return [
            {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True},
        ]


class SearchEngineThread(QThread):
    """搜索引擎异步执行线程"""
    
    result_signal = pyqtSignal(dict)  # 搜索结果
    error_signal = pyqtSignal(str)  # 错误信息
    progress_signal = pyqtSignal(int, int)  # 当前页, 总页数
    
    def __init__(self, engine: SearchEngineBase, query: str, 
                 page: int = 1, page_size: int = 100, max_pages: int = 1):
        super().__init__()
        self.engine = engine
        self.query = query
        self.page = page
        self.page_size = page_size
        self.max_pages = max_pages
        self._is_stopped = False
    
    def run(self):
        """执行搜索"""
        all_results = []
        total = 0
        
        for current_page in range(1, self.max_pages + 1):
            if self._is_stopped:
                break
            
            try:
                result = self.engine.search(self.query, current_page, self.page_size)
                
                if not result.get('success'):
                    self.error_signal.emit(result.get('error', '搜索失败'))
                    return
                
                total = result.get('total', 0)
                all_results.extend(result.get('results', []))
                
                self.progress_signal.emit(current_page, self.max_pages)
                
                # 如果已经获取了所有结果，提前结束
                if len(all_results) >= total:
                    break
                    
            except Exception as e:
                self.error_signal.emit(f"搜索出错: {str(e)}")
                return
        
        self.result_signal.emit({
            'success': True,
            'total': total,
            'results': all_results,
        })
    
    def stop(self):
        """停止搜索"""
        self._is_stopped = True


# 引擎注册表
_engine_registry: Dict[str, type] = {}

def register_engine(engine_class: type):
    """注册搜索引擎"""
    _engine_registry[engine_class.name] = engine_class

def get_engine(name: str) -> Optional[type]:
    """获取搜索引擎类"""
    return _engine_registry.get(name)

def get_all_engines() -> Dict[str, type]:
    """获取所有已注册的搜索引擎"""
    return _engine_registry.copy()
