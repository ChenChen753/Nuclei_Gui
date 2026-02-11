"""
设置管理器 - 统一管理所有配置项
包括 AI 模型预设、FOFA API 配置、扫描参数等
"""
import json
from pathlib import Path
from PyQt5.QtCore import QSettings

from core.secure_storage import get_secure_storage


class SettingsManager:
    """
    统一设置管理器
    使用 QSettings 持久化存储配置
    """
    
    # AI 模型预设模板
    DEFAULT_AI_PRESETS = [
        {
            "name": "DeepSeek",
            "api_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "api_key": ""
        },
        {
            "name": "POC生成模型",
            "api_url": "https://api.deepseek.com",
            "model": "deepseek-reasoner",
            "api_key": ""
        },
        {
            "name": "OpenAI",
            "api_url": "https://api.openai.com/v1",
            "model": "gpt-3.5-turbo",
            "api_key": ""
        },
        {
            "name": "通义千问",
            "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-turbo",
            "api_key": ""
        },
        {
            "name": "自定义",
            "api_url": "",
            "model": "",
            "api_key": ""
        }
    ]
    
    def __init__(self):
        self.settings = QSettings("Antigravity", "NucleiGUI")
        self._secure_storage = get_secure_storage()
    
    # ============== AI 配置 ==============

    def get_ai_presets(self) -> list:
        """获取 AI 模型预设列表"""
        presets_json = self.settings.value("ai_presets", None)
        presets = None
        if presets_json:
            try:
                presets = json.loads(presets_json)
            except json.JSONDecodeError:
                pass
        if presets is None:
            presets = [p.copy() for p in self.DEFAULT_AI_PRESETS]

        # 从安全存储中恢复 API Key
        for i, preset in enumerate(presets):
            stored_key = self._secure_storage.retrieve(f"ai_api_key_{i}")
            if stored_key:
                preset["api_key"] = stored_key
        return presets

    def save_ai_presets(self, presets: list):
        """保存 AI 模型预设列表"""
        # 将 API Key 存储到安全存储，并从预设中移除
        presets_to_save = []
        for i, preset in enumerate(presets):
            preset_copy = preset.copy()
            api_key = preset_copy.get("api_key", "")
            if api_key:
                self._secure_storage.store(f"ai_api_key_{i}", api_key)
            else:
                self._secure_storage.delete(f"ai_api_key_{i}")
            preset_copy["api_key"] = ""  # 不保存到 QSettings
            presets_to_save.append(preset_copy)

        self.settings.setValue("ai_presets", json.dumps(presets_to_save, ensure_ascii=False))
        self.settings.sync()  # 强制同步到磁盘
    
    def get_current_ai_preset_index(self) -> int:
        """获取当前选中的 AI 预设索引"""
        return int(self.settings.value("ai_current_index", 0))
    
    def set_current_ai_preset_index(self, index: int):
        """设置当前选中的 AI 预设索引"""
        self.settings.setValue("ai_current_index", index)
        self.settings.sync()  # 强制同步到磁盘
    
    def get_current_ai_config(self) -> dict:
        """获取当前 AI 配置"""
        presets = self.get_ai_presets()
        index = self.get_current_ai_preset_index()
        if 0 <= index < len(presets):
            return presets[index]
        return presets[0] if presets else {}
    
    # ============== FOFA 配置 ==============

    def get_fofa_config(self) -> dict:
        """获取 FOFA API 配置"""
        # API Key 从安全存储获取
        api_key = self._secure_storage.retrieve("fofa_api_key") or ""
        return {
            "api_url": self.settings.value("fofa_api_url", "https://fofa.info/api/v1/search/all"),
            "email": self.settings.value("fofa_email", ""),
            "api_key": api_key,
            "page_size": int(self.settings.value("fofa_page_size", 100))
        }

    def save_fofa_config(self, config: dict):
        """保存 FOFA API 配置"""
        self.settings.setValue("fofa_api_url", config.get("api_url", ""))
        self.settings.setValue("fofa_email", config.get("email", ""))
        # API Key 存储到安全存储
        api_key = config.get("api_key", "")
        if api_key:
            self._secure_storage.store("fofa_api_key", api_key)
        else:
            self._secure_storage.delete("fofa_api_key")
        self.settings.setValue("fofa_page_size", config.get("page_size", 100))
        self.settings.sync()  # 强制同步到磁盘，确保配置不会丢失
    
    # ============== 扫描参数配置 ==============
    
    def get_scan_config(self) -> dict:
        """获取扫描默认参数"""
        return {
            "rate_limit": int(self.settings.value("scan_rate_limit", 150)),
            "bulk_size": int(self.settings.value("scan_bulk_size", 25)),
            "timeout": int(self.settings.value("scan_timeout", 5)),
            "retries": int(self.settings.value("scan_retries", 0)),
            "follow_redirects": str(self.settings.value("scan_follow_redirects", "false")).lower() == "true",
            "stop_at_first_match": str(self.settings.value("scan_stop_at_first_match", "false")).lower() == "true",
            "no_httpx": str(self.settings.value("scan_no_httpx", "false")).lower() == "true",
            "verbose": str(self.settings.value("scan_verbose", "false")).lower() == "true",
            "proxy": self.settings.value("scan_proxy", ""),
            "use_native_scanner": str(self.settings.value("scan_use_native", "false")).lower() == "true"
        }
    
    def save_scan_config(self, config: dict):
        """保存扫描默认参数"""
        self.settings.setValue("scan_rate_limit", config.get("rate_limit", 150))
        self.settings.setValue("scan_bulk_size", config.get("bulk_size", 25))
        self.settings.setValue("scan_timeout", config.get("timeout", 5))
        self.settings.setValue("scan_retries", config.get("retries", 0))
        self.settings.setValue("scan_follow_redirects", "true" if config.get("follow_redirects") else "false")
        self.settings.setValue("scan_stop_at_first_match", "true" if config.get("stop_at_first_match") else "false")
        self.settings.setValue("scan_no_httpx", "true" if config.get("no_httpx") else "false")
        self.settings.setValue("scan_verbose", "true" if config.get("verbose") else "false")
        self.settings.setValue("scan_proxy", config.get("proxy", ""))
        self.settings.setValue("scan_use_native", "true" if config.get("use_native_scanner") else "false")
        self.settings.sync()  # 强制同步到磁盘
    
    # ============== 主题配置 ==============
    
    def get_current_theme(self) -> str:
        """获取当前主题名称"""
        return self.settings.value("theme_name", "经典蓝")
    
    def save_current_theme(self, theme_name: str):
        """保存当前主题名称"""
        self.settings.setValue("theme_name", theme_name)
        self.settings.sync()  # 强制同步到磁盘
    
    # ============== 窗口配置 ==============
    
    def get_window_geometry(self) -> dict:
        """获取保存的窗口几何信息"""
        return {
            "x": int(self.settings.value("window_x", -1)),
            "y": int(self.settings.value("window_y", -1)),
            "width": int(self.settings.value("window_width", -1)),
            "height": int(self.settings.value("window_height", -1)),
            "maximized": str(self.settings.value("window_maximized", "false")).lower() == "true"
        }
    
    def save_window_geometry(self, x: int, y: int, width: int, height: int, maximized: bool = False):
        """保存窗口几何信息"""
        self.settings.setValue("window_x", x)
        self.settings.setValue("window_y", y)
        self.settings.setValue("window_width", width)
        self.settings.setValue("window_height", height)
        self.settings.setValue("window_maximized", "true" if maximized else "false")
        self.settings.sync()  # 强制同步到磁盘



# 全局单例
_settings_instance = None

def get_settings() -> SettingsManager:
    """获取设置管理器单例"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager()
    return _settings_instance
