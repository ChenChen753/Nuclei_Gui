import json
import shutil
from pathlib import Path
import yaml

from i18n import tr
from core.paths import ensure_external_layout, external_path, user_data_path

class POCLibrary:
    """POC 库管理器 - 负责 POC 的导入、存储和读取"""
    
    def __init__(self, library_path: str = None):
        # 默认使用当前目录下的 poc_library 文件夹
        if library_path is None:
            ensure_external_layout()
            self.library_path = external_path("poc_library")
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
        self._cache_file = user_data_path("cache", "poc_index.json")
    
    def get_poc_count(self) -> int:
        """快速获取 POC 数量（不解析内容，仅计数文件）"""
        return sum(1 for _ in self._iter_poc_files())
    
    def invalidate_cache(self):
        """使缓存失效"""
        self._cache_valid = False
        self._poc_cache = None

    def _iter_poc_files(self):
        """遍历全部 POC 文件并返回来源标记"""
        seen = set()
        if not self.library_path.exists():
            return

        for file in self.library_path.rglob("*"):
            if not file.is_file() or file.suffix.lower() not in (".yaml", ".yml"):
                continue

            cache_key = str(file.resolve())
            if cache_key in seen:
                continue

            seen.add(cache_key)
            yield file, self._get_source_for_path(file)

    def _get_source_for_path(self, path: Path) -> str:
        """根据 POC 路径返回兼容旧逻辑的来源标记"""
        try:
            relative = path.resolve().relative_to(self.library_path.resolve())
        except ValueError:
            return "custom"

        if len(relative.parts) <= 1:
            return "legacy"

        top_folder = relative.parts[0]
        if top_folder == "cloud":
            return "cloud"
        if top_folder in ("custom", "user_generated"):
            return "custom"
        return "folder"

    def _get_folder_metadata(self, path: Path) -> tuple:
        """返回用于 UI 筛选的文件夹分类信息"""
        try:
            folder = path.resolve().parent.relative_to(self.library_path.resolve())
        except ValueError:
            folder = Path(path.parent.name)

        if str(folder) in ("", "."):
            return "__root__", ""

        folder_key = folder.as_posix()
        return folder_key, folder_key

    def get_folder_options(self) -> list:
        """Return top-level POC folders for source filters, including empty custom folders."""
        if not self.library_path.exists():
            return []

        folders = {}
        for folder in self.library_path.iterdir():
            if folder.is_dir():
                folder_key = folder.name
                folders[folder_key] = folder_key

        return sorted(folders.items(), key=lambda item: item[0].lower())

    def _add_folder_metadata(self, info: dict, path: Path) -> dict:
        folder_key, folder_label = self._get_folder_metadata(path)
        info["folder_key"] = folder_key
        info["folder_label"] = folder_label
        return info

    def _load_persistent_cache(self) -> dict:
        """加载磁盘缓存"""
        if not self._cache_file.exists():
            return {}

        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                return {}
            if payload.get("version") != 2:
                return {}
            entries = payload.get("entries", {})
            return entries if isinstance(entries, dict) else {}
        except Exception:
            return {}

    def _save_persistent_cache(self, entries: dict):
        """保存磁盘缓存"""
        payload = {
            "version": 2,
            "entries": entries,
        }
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception:
            pass

    def _serialize_poc_info(self, poc: dict, path: Path, source: str, stat_result) -> dict:
        """序列化 POC 信息用于磁盘缓存"""
        return {
            "mtime_ns": stat_result.st_mtime_ns,
            "size": stat_result.st_size,
            "source": source,
            "info": {
                "id": poc.get("id", "unknown"),
                "name": poc.get("name", tr("poc.unnamed")),
                "author": poc.get("author", tr("poc.unknown")),
                "severity": poc.get("severity", "unknown"),
                "description": poc.get("description", ""),
                "tags": poc.get("tags", ""),
                "filename": path.name,
                "path": str(path.absolute()),
                "source": source,
                "folder_key": poc.get("folder_key", "__root__"),
                "folder_label": poc.get("folder_label", ""),
            },
        }
    
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
            return {"success": False, "error": tr("poc.file_not_found")}
        
        if source.suffix not in ['.yaml', '.yml']:
            return {"success": False, "error": tr("poc.must_be_yaml")}
        
        # 解析模板获取信息
        poc_info = self._parse_poc(source)
        if not poc_info:
            return {"success": False, "error": tr("poc.invalid_template_format")}
        
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
                return {"success": False, "error": tr("poc.copy_failed", error=str(e))}
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

        disk_cache = self._load_persistent_cache()
        next_cache = {}
        pocs = []

        for file, source in self._iter_poc_files():
            try:
                stat_result = file.stat()
            except OSError:
                continue

            cache_key = str(file.resolve())
            cache_entry = disk_cache.get(cache_key)

            if (
                isinstance(cache_entry, dict)
                and cache_entry.get("mtime_ns") == stat_result.st_mtime_ns
                and cache_entry.get("size") == stat_result.st_size
            ):
                info = cache_entry.get("info")
                if isinstance(info, dict):
                    self._add_folder_metadata(info, file)
                    next_cache[cache_key] = cache_entry
                    pocs.append(info)
                    continue

            info = self._parse_poc(file)
            if not info:
                continue

            info["path"] = str(file.absolute())
            info["source"] = source
            self._add_folder_metadata(info, file)
            pocs.append(info)
            next_cache[cache_key] = self._serialize_poc_info(info, file, source, stat_result)

        pocs.sort(key=lambda item: (item.get("id", ""), item.get("name", "")))
        self._save_persistent_cache(next_cache)

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
                "name": data["info"].get("name", tr("poc.unnamed")),
                "author": data["info"].get("author", tr("poc.unknown")),
                "severity": data["info"].get("severity", "unknown"),
                "description": data["info"].get("description", ""),
                "tags": data["info"].get("tags", ""),
                "filename": path.name
            }
        except Exception as e:
            print(f"[!] {tr('poc.parse_error', path=str(path), e=str(e))}")
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
