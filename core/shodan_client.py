"""
Shodan 搜索引擎客户端
官方 API 文档: https://developer.shodan.io/api
"""
import requests
from typing import Dict, List
from .search_engine_base import SearchEngineBase, SearchResult, register_engine


class ShodanClient(SearchEngineBase):
    """Shodan 搜索引擎客户端"""
    
    name = "shodan"
    display_name = "Shodan"
    
    def __init__(self, api_key: str = "", api_url: str = "", **kwargs):
        super().__init__(api_key, api_url, **kwargs)
        # Shodan 默认 API 地址
        if not self.api_url:
            self.api_url = "https://api.shodan.io"
    
    def search(self, query: str, page: int = 1, page_size: int = 100) -> Dict:
        """
        执行 Shodan 搜索
        
        参数:
            query: 搜索语句（Shodan 语法）
            page: 页码（从1开始）
            page_size: 每页结果数（Shodan 固定每页100条）
        """
        if not self.api_key:
            return {'success': False, 'error': '请配置 Shodan API Key'}
        
        try:
            url = f"{self.api_url}/shodan/host/search"
            params = {
                'key': self.api_key,
                'query': query,
                'page': page,
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 401:
                return {'success': False, 'error': 'Shodan API Key 无效'}
            elif response.status_code == 402:
                return {'success': False, 'error': 'Shodan 查询配额不足'}
            elif response.status_code != 200:
                return {'success': False, 'error': f'Shodan API 错误: HTTP {response.status_code}'}
            
            data = response.json()
            
            if 'error' in data:
                return {'success': False, 'error': data['error']}
            
            # 解析结果
            results = []
            matches = data.get('matches', []) or []
            
            for item in matches:
                location = item.get('location', {}) or {}
                
                result = SearchResult(
                    ip=item.get('ip_str', ''),
                    port=item.get('port', 0),
                    domain=','.join(item.get('hostnames', [])) if item.get('hostnames') else '',
                    title=item.get('http', {}).get('title', '') if item.get('http') else '',
                    protocol=item.get('transport', ''),
                    country=location.get('country_name', ''),
                    region=location.get('region_name', ''),
                    city=location.get('city', ''),
                    isp=item.get('isp', ''),
                    os=item.get('os', ''),
                    server=item.get('http', {}).get('server', '') if item.get('http') else '',
                    banner=item.get('data', '')[:500] if item.get('data') else '',
                    extra={
                        'org': item.get('org', ''),
                        'asn': item.get('asn', ''),
                        'product': item.get('product', ''),
                        'version': item.get('version', ''),
                    }
                )
                results.append(result)
            
            total = data.get('total', 0)
            
            return {
                'success': True,
                'total': total,
                'results': results,
            }
            
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Shodan API 请求超时'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Shodan API 请求失败: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'解析 Shodan 结果失败: {str(e)}'}
    
    def test_connection(self) -> Dict:
        """测试连接"""
        if not self.api_key:
            return {'success': False, 'message': '请配置 API Key'}
        
        try:
            url = f"{self.api_url}/api-info"
            params = {'key': self.api_key}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'message': f"连接成功，计划: {data.get('plan', 'N/A')}",
                    'quota': {
                        'query_credits': data.get('query_credits', 0),
                        'scan_credits': data.get('scan_credits', 0),
                    }
                }
            elif response.status_code == 401:
                return {'success': False, 'message': 'API Key 无效'}
            else:
                return {'success': False, 'message': f'连接失败: HTTP {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': f'连接失败: {str(e)}'}
    
    def get_config_fields(self) -> List[Dict]:
        return [
            {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True},
        ]


# 注册引擎
register_engine(ShodanClient)
