import shutil
from pathlib import Path
import yaml
import time

class POCLibrary:
    """POC 库管理器 - 负责 POC 的导入、存储和读取"""
    
    def __init__(self, library_path: str = None):
        # 默认使用当前目录下的 poc_library 文件夹
        if library_path is None:
            self.library_path = Path("poc_library")
        else:
            self.library_path = Path(library_path)
        
        # 用户自定义 POC 目录
        self.custom_path = self.library_path / "custom"
        # 云端同步 POC 目录
        self.cloud_path = self.library_path / "cloud"
        # 用户生成的 POC 目录
        self.user_generated_path = self.library_path / "user_generated"
        
        # 确保目录存在
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.custom_path.mkdir(parents=True, exist_ok=True)
        self.cloud_path.mkdir(parents=True, exist_ok=True)
        self.user_generated_path.mkdir(parents=True, exist_ok=True)
        
        # POC 缓存
        self._poc_cache = None
        self._cache_valid = False
    
    def get_poc_count(self) -> int:
        """快速获取 POC 数量（不解析内容，仅计数文件）"""
        count = 0

        # 扫描各目录的 yaml/yml 文件数量（合并遍历）
        for dir_path in [self.custom_path, self.cloud_path, self.user_generated_path]:
            if dir_path.exists():
                count += sum(1 for f in dir_path.rglob("*") if f.suffix in ('.yaml', '.yml'))

        # 兼容旧版：扫描根目录
        count += len(list(self.library_path.glob("*.yaml")))

        return count
    
    def invalidate_cache(self):
        """使缓存失效"""
        self._cache_valid = False
        self._poc_cache = None
    
    def import_poc(self, source_file: str, auto_sync: bool = True) -> dict:
        """
        导入 POC 文件（保存到 custom 目录）
        :param source_file: 源文件路径
        :param auto_sync: 是否自动同步到库 (复制文件)
        :return: 导入结果信息
        """
        source = Path(source_file)
        
        # 验证文件
        if not source.exists():
            return {"success": False, "error": "文件不存在"}
        
        if source.suffix not in ['.yaml', '.yml']:
            return {"success": False, "error": "必须是 YAML 文件"}
        
        # 解析模板获取信息
        poc_info = self._parse_poc(source)
        if not poc_info:
            return {"success": False, "error": "无效的 Nuclei 模板格式 (缺少 id 或 info 字段)"}
        
        final_path = source
        
        if auto_sync:
            # 复制到 custom 目录
            dest = self.custom_path / source.name
            
            # 如果已存在，自动重命名
            if dest.exists():
                dest = self._get_unique_name(dest)
            
            try:
                shutil.copy2(source, dest)
                final_path = dest
                poc_info["synced_path"] = str(dest)
                poc_info["is_synced"] = True
                poc_info["source"] = "custom"
                # 使缓存失效
                self.invalidate_cache()
            except Exception as e:
                return {"success": False, "error": f"复制文件失败: {str(e)}"}
        else:
            poc_info["synced_path"] = str(source)
            poc_info["is_synced"] = False
            poc_info["source"] = "custom"
        
        poc_info["success"] = True
        return poc_info

    def get_all_pocs(self, use_cache: bool = True) -> list:
        """获取库中所有 POC（包括 custom、cloud 和 user_generated）

        参数:
            use_cache: 是否使用缓存，默认为 True
        """
        # 如果缓存有效且允许使用缓存，直接返回
        if use_cache and self._cache_valid and self._poc_cache is not None:
            return self._poc_cache

        pocs = []

        # 定义要扫描的目录及其来源标识
        scan_dirs = [
            (self.custom_path, "custom"),
            (self.cloud_path, "cloud"),
            (self.user_generated_path, "custom"),  # 显示为用户来源
        ]

        # 扫描各目录（合并 .yaml 和 .yml 遍历）
        for dir_path, source in scan_dirs:
            if dir_path.exists():
                for file in dir_path.rglob("*"):
                    if file.suffix in ('.yaml', '.yml'):
                        info = self._parse_poc(file)
                        if info:
                            info["path"] = str(file.absolute())
                            info["source"] = source
                            pocs.append(info)

        # 兼容旧版：扫描根目录
        for file in self.library_path.glob("*.yaml"):
            info = self._parse_poc(file)
            if info:
                info["path"] = str(file.absolute())
                info["source"] = "legacy"
                pocs.append(info)

        # 更新缓存
        self._poc_cache = pocs
        self._cache_valid = True

        return pocs
    
    def delete_poc(self, file_path: str) -> bool:
        """删除库中的 POC"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                # 使缓存失效
                self.invalidate_cache()
                return True
        except:
            pass
        return False

    def _parse_poc(self, path: Path) -> dict:
        """解析 POC 文件获取基本信息"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or 'id' not in data or 'info' not in data:
                return None
            
            return {
                "id": data.get("id", "unknown"),
                "name": data["info"].get("name", "未命名"),
                "author": data["info"].get("author", "未知"),
                "severity": data["info"].get("severity", "unknown"),
                "description": data["info"].get("description", ""),
                "tags": data["info"].get("tags", ""),
                "filename": path.name
            }
        except Exception as e:
            print(f"解析出错 {path}: {e}")
            return None
    
    def _get_unique_name(self, path: Path) -> Path:
        """生成唯一文件名"""
        counter = 1
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        new_path = path
        while new_path.exists():
            new_path = parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        return new_path
