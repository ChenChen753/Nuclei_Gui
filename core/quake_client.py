"""
Quake 搜索引擎客户端
官方 API 文档: https://quake.360.cn/quake/#/help
"""
import requests
from typing import Dict, List
from .search_engine_base import SearchEngineBase, SearchResult, register_engine


class QuakeClient(SearchEngineBase):
    """Quake 搜索引擎客户端"""
    
    name = "quake"
    display_name = "Quake 360"
    
    def __init__(self, api_key: str = "", api_url: str = "", **kwargs):
        super().__init__(api_key, api_url, **kwargs)
        # Quake 默认 API 地址
        if not self.api_url:
            self.api_url = "https://quake.360.net/api/v3/search/quake_service"
    
    def search(self, query: str, page: int = 1, page_size: int = 100) -> Dict:
        """
        执行 Quake 搜索
        
        参数:
            query: 搜索语句（Quake 语法）
            page: 页码（从1开始）
            page_size: 每页结果数（最大100）
        """
        if not self.api_key:
            return {'success': False, 'error': '请配置 Quake API Key'}
        
        try:
            headers = {
                'X-QuakeToken': self.api_key,
                'Content-Type': 'application/json',
            }
            
            payload = {
                'query': query,
                'start': (page - 1) * page_size,
                'size': min(page_size, 100),
                'include': ['ip', 'port', 'hostname', 'transport', 'service', 'location', 'title'],
            }
            
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if data.get('code') != 0:
                return {
                    'success': False,
                    'error': data.get('message', f"Quake API 错误: {data.get('code')}")
                }
            
            # 解析结果
            results = []
            items = data.get('data', []) or []
            
            for item in items:
                location = item.get('location', {}) or {}
                service = item.get('service', {}) or {}
                
                result = SearchResult(
                    ip=item.get('ip', ''),
                    port=item.get('port', 0),
                    domain=item.get('hostname', ''),
                    title=item.get('title', ''),
                    protocol=item.get('transport', ''),
                    country=location.get('country_cn', ''),
                    region=location.get('province_cn', ''),
                    city=location.get('city_cn', ''),
                    isp=location.get('isp', ''),
                    server=service.get('name', ''),
                    banner=service.get('banner', ''),
                    extra={
                        'asn': location.get('asn', ''),
                        'org': location.get('owner', ''),
                    }
                )
                results.append(result)
            
            total = data.get('meta', {}).get('pagination', {}).get('total', 0)
            
            return {
                'success': True,
                'total': total,
                'results': results,
            }
            
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Quake API 请求超时'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Quake API 请求失败: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'解析 Quake 结果失败: {str(e)}'}
    
    def test_connection(self) -> Dict:
        """测试连接"""
        if not self.api_key:
            return {'success': False, 'message': '请配置 API Key'}
        
        try:
            # 使用用户信息接口测试
            headers = {'X-QuakeToken': self.api_key}
            response = requests.get(
                'https://quake.360.net/api/v3/user/info',
                headers=headers,
                timeout=10
            )
            data = response.json()
            
            if data.get('code') == 0:
                user = data.get('data', {})
                return {
                    'success': True,
                    'message': f"连接成功，用户: {user.get('user', {}).get('username', 'N/A')}",
                    'quota': {
                        'credit': user.get('credit', 0),
                        'persistent_credit': user.get('persistent_credit', 0),
                    }
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', 'API Key 无效'),
                }
        except Exception as e:
            return {'success': False, 'message': f'连接失败: {str(e)}'}
    
    def get_config_fields(self) -> List[Dict]:
        return [
            {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True},
        ]


# 注册引擎
register_engine(QuakeClient)
