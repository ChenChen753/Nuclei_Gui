"""
Hunter 搜索引擎客户端
官方 API 文档: https://hunter.io/api-documentation
"""
import requests
import base64
from typing import Dict, List
from .search_engine_base import SearchEngineBase, SearchResult, register_engine


class HunterClient(SearchEngineBase):
    """Hunter 搜索引擎客户端"""
    
    name = "hunter"
    display_name = "Hunter 鹰图"
    
    def __init__(self, api_key: str = "", api_url: str = "", **kwargs):
        super().__init__(api_key, api_url, **kwargs)
        # Hunter 默认 API 地址
        if not self.api_url:
            self.api_url = "https://hunter.qianxin.com/openApi/search"
    
    def search(self, query: str, page: int = 1, page_size: int = 100) -> Dict:
        """
        执行 Hunter 搜索
        
        参数:
            query: 搜索语句（Hunter 语法）
            page: 页码（从1开始）
            page_size: 每页结果数（最大100）
        """
        if not self.api_key:
            return {'success': False, 'error': '请配置 Hunter API Key'}
        
        try:
            # Hunter API 需要 Base64 编码搜索语句
            query_b64 = base64.urlsafe_b64encode(query.encode('utf-8')).decode('utf-8')
            
            params = {
                'api-key': self.api_key,
                'search': query_b64,
                'page': page,
                'page_size': min(page_size, 100),
                'is_web': 3,  # 1:web 2:非web 3:全部
            }
            
            response = requests.get(self.api_url, params=params, timeout=30)
            data = response.json()
            
            if data.get('code') != 200:
                return {
                    'success': False,
                    'error': data.get('message', f"Hunter API 错误: {data.get('code')}")
                }
            
            # 解析结果
            results = []
            arr = data.get('data', {}).get('arr', []) or []
            
            for item in arr:
                result = SearchResult(
                    ip=item.get('ip', ''),
                    port=item.get('port', 0),
                    domain=item.get('domain', ''),
                    url=item.get('url', ''),
                    title=item.get('web_title', ''),
                    protocol=item.get('protocol', ''),
                    country=item.get('country', ''),
                    region=item.get('province', ''),
                    city=item.get('city', ''),
                    isp=item.get('isp', ''),
                    os=item.get('os', ''),
                    server=item.get('component', [{}])[0].get('name', '') if item.get('component') else '',
                    extra={
                        'status_code': item.get('status_code'),
                        'company': item.get('company', ''),
                        'number': item.get('number', ''),
                        'as_org': item.get('as_org', ''),
                    }
                )
                results.append(result)
            
            total = data.get('data', {}).get('total', 0)
            
            return {
                'success': True,
                'total': total,
                'results': results,
            }
            
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Hunter API 请求超时'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Hunter API 请求失败: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'解析 Hunter 结果失败: {str(e)}'}
    
    def test_connection(self) -> Dict:
        """测试连接"""
        if not self.api_key:
            return {'success': False, 'message': '请配置 API Key'}
        
        # 使用一个简单的查询测试
        result = self.search('port="80"', page=1, page_size=1)
        
        if result.get('success'):
            return {
                'success': True,
                'message': f"连接成功，共找到 {result.get('total', 0)} 条结果",
            }
        else:
            return {
                'success': False,
                'message': result.get('error', '连接失败'),
            }
    
    def get_config_fields(self) -> List[Dict]:
        return [
            {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True},
        ]


# 注册引擎
register_engine(HunterClient)
