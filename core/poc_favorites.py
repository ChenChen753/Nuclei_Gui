"""
POC 收藏/分组管理 - 支持自定义标签和分组
"""
import json
from pathlib import Path
from PyQt5.QtCore import QSettings


class POCFavorites:
    """
    POC 收藏和分组管理器
    使用 JSON 文件持久化存储
    """
    
    def __init__(self):
        self.settings = QSettings("Antigravity", "NucleiGUI")
        self._favorites = set()  # 收藏的 POC 路径集合
        self._groups = {}  # 分组: {组名: [poc路径列表]}
        self._tags = {}  # 标签: {poc路径: [标签列表]}
        self.load()
    
    def load(self):
        """从设置加载数据"""
        try:
            favorites_json = self.settings.value("poc_favorites", "[]")
            self._favorites = set(json.loads(favorites_json))
            
            groups_json = self.settings.value("poc_groups", "{}")
            self._groups = json.loads(groups_json)
            
            tags_json = self.settings.value("poc_tags", "{}")
            self._tags = json.loads(tags_json)
        except:
            self._favorites = set()
            self._groups = {}
            self._tags = {}
    
    def save(self):
        """保存数据到设置"""
        self.settings.setValue("poc_favorites", json.dumps(list(self._favorites)))
        self.settings.setValue("poc_groups", json.dumps(self._groups))
        self.settings.setValue("poc_tags", json.dumps(self._tags))
    
    # ============== 收藏管理 ==============
    
    def is_favorite(self, poc_path: str) -> bool:
        """检查 POC 是否被收藏"""
        return poc_path in self._favorites
    
    def add_favorite(self, poc_path: str):
        """添加收藏"""
        self._favorites.add(poc_path)
        self.save()
    
    def remove_favorite(self, poc_path: str):
        """移除收藏"""
        self._favorites.discard(poc_path)
        self.save()
    
    def toggle_favorite(self, poc_path: str) -> bool:
        """切换收藏状态，返回新状态"""
        if self.is_favorite(poc_path):
            self.remove_favorite(poc_path)
            return False
        else:
            self.add_favorite(poc_path)
            return True
    
    def get_all_favorites(self) -> list:
        """获取所有收藏的 POC 路径"""
        return list(self._favorites)
    
    # ============== 分组管理 ==============
    
    def get_groups(self) -> list:
        """获取所有分组名称"""
        return list(self._groups.keys())
    
    def create_group(self, group_name: str):
        """创建分组"""
        if group_name not in self._groups:
            self._groups[group_name] = []
            self.save()
    
    def delete_group(self, group_name: str):
        """删除分组"""
        if group_name in self._groups:
            del self._groups[group_name]
            self.save()
    
    def rename_group(self, old_name: str, new_name: str):
        """重命名分组"""
        if old_name in self._groups and new_name not in self._groups:
            self._groups[new_name] = self._groups.pop(old_name)
            self.save()
    
    def add_to_group(self, poc_path: str, group_name: str):
        """将 POC 添加到分组"""
        if group_name not in self._groups:
            self._groups[group_name] = []
        if poc_path not in self._groups[group_name]:
            self._groups[group_name].append(poc_path)
            self.save()
    
    def remove_from_group(self, poc_path: str, group_name: str):
        """从分组移除 POC"""
        if group_name in self._groups and poc_path in self._groups[group_name]:
            self._groups[group_name].remove(poc_path)
            self.save()
    
    def get_group_pocs(self, group_name: str) -> list:
        """获取分组中的所有 POC"""
        return self._groups.get(group_name, [])
    
    def get_poc_groups(self, poc_path: str) -> list:
        """获取 POC 所属的所有分组"""
        groups = []
        for group_name, pocs in self._groups.items():
            if poc_path in pocs:
                groups.append(group_name)
        return groups
    
    # ============== 标签管理 ==============
    
    def get_tags(self, poc_path: str) -> list:
        """获取 POC 的标签"""
        return self._tags.get(poc_path, [])
    
    def add_tag(self, poc_path: str, tag: str):
        """为 POC 添加标签"""
        if poc_path not in self._tags:
            self._tags[poc_path] = []
        if tag not in self._tags[poc_path]:
            self._tags[poc_path].append(tag)
            self.save()
    
    def remove_tag(self, poc_path: str, tag: str):
        """移除 POC 的标签"""
        if poc_path in self._tags and tag in self._tags[poc_path]:
            self._tags[poc_path].remove(tag)
            if not self._tags[poc_path]:
                del self._tags[poc_path]
            self.save()
    
    def get_all_tags(self) -> list:
        """获取所有使用过的标签"""
        all_tags = set()
        for tags in self._tags.values():
            all_tags.update(tags)
        return sorted(list(all_tags))


# 全局单例
_favorites_instance = None

def get_favorites() -> POCFavorites:
    """获取收藏管理器单例"""
    global _favorites_instance
    if _favorites_instance is None:
        _favorites_instance = POCFavorites()
    return _favorites_instance
