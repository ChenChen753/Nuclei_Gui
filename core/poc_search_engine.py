"""
POC 搜索引擎 - 支持按 CVE 编号、产品名、关键词等多字段搜索
独立模块，不修改现有 poc_library.py 核心逻辑
"""
import re
from typing import List, Dict, Optional


class POCSearchEngine:
    """POC 搜索引擎 - 提供高级搜索功能"""
    
    def __init__(self, poc_library):
        """
        初始化搜索引擎
        
        参数:
            poc_library: POCLibrary 实例
        """
        self.poc_library = poc_library
        self._search_index = {}
        self._index_built = False
    
    def build_index(self, force_rebuild: bool = False):
        """
        构建搜索索引
        
        参数:
            force_rebuild: 是否强制重建索引
        """
        if self._index_built and not force_rebuild:
            return
        
        self._search_index = {}
        pocs = self.poc_library.get_all_pocs(use_cache=True)
        
        for poc in pocs:
            poc_id = poc.get('id', '')
            self._search_index[poc_id] = {
                'poc': poc,
                'searchable_text': self._build_searchable_text(poc),
                'cve': self._extract_cve(poc),
                'product': self._extract_product(poc),
                'tags': self._extract_tags(poc),
            }
        
        self._index_built = True
    
    def _build_searchable_text(self, poc: dict) -> str:
        """构建可搜索文本（合并所有字段）"""
        parts = [
            poc.get('id', ''),
            poc.get('name', ''),
            poc.get('author', ''),
            poc.get('description', ''),
            poc.get('tags', ''),
            poc.get('filename', ''),
        ]
        return ' '.join(str(p).lower() for p in parts if p)
    
    def _extract_cve(self, poc: dict) -> List[str]:
        """提取 CVE 编号"""
        text = f"{poc.get('id', '')} {poc.get('name', '')} {poc.get('tags', '')} {poc.get('description', '')}"
        # 匹配 CVE-YYYY-NNNNN 格式
        cve_pattern = r'CVE-\d{4}-\d{4,}'
        matches = re.findall(cve_pattern, text, re.IGNORECASE)
        return [m.upper() for m in matches]
    
    def _extract_product(self, poc: dict) -> str:
        """提取产品名称（从 name 和 tags 推断）"""
        name = poc.get('name', '')
        # 常见产品名称提取
        # 例如: "Apache Struts2 RCE" -> "Apache Struts2"
        # 简单实现：取前两个词
        words = name.split()
        if len(words) >= 2:
            return ' '.join(words[:2]).lower()
        return name.lower()
    
    def _extract_tags(self, poc: dict) -> List[str]:
        """提取标签列表"""
        tags = poc.get('tags', '')
        if isinstance(tags, list):
            return [t.lower() for t in tags]
        elif isinstance(tags, str):
            return [t.strip().lower() for t in tags.split(',') if t.strip()]
        return []
    
    def search(self, query: str, fields: Optional[List[str]] = None, 
               category: Optional[str] = None) -> List[dict]:
        """
        搜索 POC
        
        参数:
            query: 搜索关键词
            fields: 搜索字段列表，可选值: ['all', 'cve', 'name', 'tags', 'author', 'product']
                    默认为 ['all']
            category: POC 来源分类过滤，可选值: ['all', 'user_generated', 'cloud', 'custom', 'legacy']
        
        返回:
            匹配的 POC 列表
        """
        # 确保索引已构建
        self.build_index()
        
        if not query:
            # 无搜索词时返回所有（可能需要分类过滤）
            results = [item['poc'] for item in self._search_index.values()]
            if category and category != 'all':
                results = self._filter_by_category(results, category)
            return results
        
        query_lower = query.lower().strip()
        fields = fields or ['all']
        results = []
        
        for poc_id, index_data in self._search_index.items():
            if self._match_query(query_lower, index_data, fields):
                results.append(index_data['poc'])
        
        # 分类过滤
        if category and category != 'all':
            results = self._filter_by_category(results, category)
        
        # 按相关度排序（CVE 精确匹配优先）
        results = self._sort_by_relevance(results, query_lower)
        
        return results
    
    def _match_query(self, query: str, index_data: dict, fields: List[str]) -> bool:
        """检查是否匹配查询"""
        if 'all' in fields:
            # 全文搜索
            if query in index_data['searchable_text']:
                return True
            # CVE 搜索
            for cve in index_data['cve']:
                if query.upper() in cve:
                    return True
            return False
        
        # 特定字段搜索
        poc = index_data['poc']
        
        if 'cve' in fields:
            for cve in index_data['cve']:
                if query.upper() in cve:
                    return True
        
        if 'name' in fields:
            if query in poc.get('name', '').lower():
                return True
        
        if 'tags' in fields:
            for tag in index_data['tags']:
                if query in tag:
                    return True
        
        if 'author' in fields:
            if query in poc.get('author', '').lower():
                return True
        
        if 'product' in fields:
            if query in index_data['product']:
                return True
        
        return False
    
    def _filter_by_category(self, pocs: List[dict], category: str) -> List[dict]:
        """按分类过滤"""
        # 分类映射
        category_mapping = {
            'user_generated': lambda p: 'user_generated' in p.get('path', ''),
            'cloud': lambda p: p.get('source') == 'cloud',
            'custom': lambda p: p.get('source') == 'custom' and 'user_generated' not in p.get('path', ''),
            'legacy': lambda p: p.get('source') == 'legacy',
        }
        
        filter_func = category_mapping.get(category)
        if filter_func:
            return [p for p in pocs if filter_func(p)]
        return pocs
    
    def _sort_by_relevance(self, pocs: List[dict], query: str) -> List[dict]:
        """按相关度排序"""
        def relevance_score(poc):
            score = 0
            name = poc.get('name', '').lower()
            poc_id = poc.get('id', '').lower()
            
            # 精确匹配 POC ID 得分最高
            if query == poc_id:
                score += 100
            elif query in poc_id:
                score += 50
            
            # 名称匹配
            if query in name:
                score += 30
                # 开头匹配额外加分
                if name.startswith(query):
                    score += 20
            
            # CVE 精确匹配
            if query.upper().startswith('CVE-'):
                if query.upper() in poc.get('name', '').upper():
                    score += 40
            
            return -score  # 负数用于降序排序
        
        return sorted(pocs, key=relevance_score)
    
    def get_categories(self) -> Dict[str, int]:
        """
        获取所有分类及其 POC 数量
        
        返回:
            分类名称到数量的映射
        """
        self.build_index()
        
        categories = {
            'all': 0,
            'user_generated': 0,
            'cloud': 0,
            'custom': 0,
            'legacy': 0,
        }
        
        for index_data in self._search_index.values():
            poc = index_data['poc']
            categories['all'] += 1
            
            path = poc.get('path', '')
            source = poc.get('source', '')
            
            if 'user_generated' in path:
                categories['user_generated'] += 1
            elif source == 'cloud':
                categories['cloud'] += 1
            elif source == 'custom':
                categories['custom'] += 1
            elif source == 'legacy':
                categories['legacy'] += 1
        
        return categories
    
    def invalidate_index(self):
        """使索引失效（当 POC 库变更时调用）"""
        self._index_built = False
        self._search_index = {}
    
    def search_by_cve(self, cve_id: str) -> List[dict]:
        """按 CVE 编号搜索"""
        return self.search(cve_id, fields=['cve'])
    
    def search_by_product(self, product: str) -> List[dict]:
        """按产品名称搜索"""
        return self.search(product, fields=['product', 'name', 'tags'])
    
    def search_by_severity(self, severity: str) -> List[dict]:
        """按严重程度搜索"""
        self.build_index()
        results = []
        for index_data in self._search_index.values():
            poc = index_data['poc']
            if poc.get('severity', '').lower() == severity.lower():
                results.append(poc)
        return results


# 单例模式
_search_engine_instance = None

def get_poc_search_engine(poc_library=None):
    """
    获取 POC 搜索引擎单例
    
    参数:
        poc_library: POCLibrary 实例（首次调用时必须提供）
    """
    global _search_engine_instance
    
    if _search_engine_instance is None:
        if poc_library is None:
            raise ValueError("首次调用必须提供 poc_library 参数")
        _search_engine_instance = POCSearchEngine(poc_library)
    
    return _search_engine_instance
