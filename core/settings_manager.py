"""
设置管理器 - 统一管理所有配置项
包括 AI 模型预设、FOFA API 配置、扫描参数等
"""
import json
from pathlib import Path
from PyQt5.QtCore import QSettings

from i18n import tr
from core.network_proxy import (
    DEFAULT_PROXY_MODES,
    PROXY_MODE_CUSTOM,
    PROXY_SCOPE_SCAN,
    normalize_proxy_mode,
    normalize_proxy_scope,
    normalize_proxy_url,
)
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

    def get_proxy_config(self, scope: str) -> dict:
        """获取指定功能的代理配置。"""
        scope = normalize_proxy_scope(scope)
        mode_key = f"network_proxy_mode_{scope}"
        stored_mode = self.settings.value(mode_key, None)
        proxy_url = self._secure_storage.retrieve(f"network_proxy_url_{scope}") or ""

        # 兼容旧版扫描代理字段：首次升级时自动视为自定义扫描代理。
        if stored_mode is None and scope == PROXY_SCOPE_SCAN:
            legacy_proxy = str(self.settings.value("scan_proxy", "") or "").strip()
            if legacy_proxy:
                return {
                    "mode": PROXY_MODE_CUSTOM,
                    "url": normalize_proxy_url(legacy_proxy),
                }

        return {
            "mode": normalize_proxy_mode(stored_mode or DEFAULT_PROXY_MODES[scope]),
            "url": normalize_proxy_url(proxy_url) if proxy_url else "",
        }

    def get_proxy_configs(self) -> dict:
        """获取全部功能的代理配置。"""
        return {scope: self.get_proxy_config(scope) for scope in DEFAULT_PROXY_MODES}

    def save_proxy_configs(self, configs: dict):
        """校验后一次性保存全部代理配置。"""
        normalized = {}
        for raw_scope, config in configs.items():
            scope = normalize_proxy_scope(raw_scope)
            mode = normalize_proxy_mode((config or {}).get("mode"))
            proxy_url = normalize_proxy_url((config or {}).get("url", ""))
            if mode == PROXY_MODE_CUSTOM and not proxy_url:
                raise ValueError(f"Custom proxy URL is required for {scope}")
            normalized[scope] = {"mode": mode, "url": proxy_url}

        for scope, config in normalized.items():
            self.settings.setValue(f"network_proxy_mode_{scope}", config["mode"])
            storage_key = f"network_proxy_url_{scope}"
            if config["url"]:
                if not self._secure_storage.store(storage_key, config["url"]):
                    raise ValueError(f"Failed to store proxy URL for {scope}")
            else:
                self._secure_storage.delete(storage_key)

        scan_config = normalized.get(PROXY_SCOPE_SCAN)
        if scan_config is not None:
            legacy_proxy = scan_config["url"] if scan_config["mode"] == PROXY_MODE_CUSTOM else ""
            self.settings.setValue("scan_proxy", legacy_proxy)
        self.settings.sync()

    def save_proxy_config(self, scope: str, mode: str, proxy_url: str = ""):
        """保存单个功能的代理配置。"""
        self.save_proxy_configs({scope: {"mode": mode, "url": proxy_url}})
    
    def get_scan_config(self) -> dict:
        """获取扫描默认参数"""
        scan_proxy = self.get_proxy_config(PROXY_SCOPE_SCAN)
        return {
            "rate_limit": int(self.settings.value("scan_rate_limit", 150)),
            "bulk_size": int(self.settings.value("scan_bulk_size", 25)),
            "timeout": int(self.settings.value("scan_timeout", 5)),
            "retries": int(self.settings.value("scan_retries", 0)),
            "follow_redirects": str(self.settings.value("scan_follow_redirects", "false")).lower() == "true",
            "stop_at_first_match": str(self.settings.value("scan_stop_at_first_match", "false")).lower() == "true",
            # Skip the discovery probe and enable verbose output by default for new users.
            # Existing QSettings values still take precedence, so user choices are preserved.
            "no_httpx": str(self.settings.value("scan_no_httpx", "true")).lower() == "true",
            "verbose": str(self.settings.value("scan_verbose", "true")).lower() == "true",
            "proxy": scan_proxy["url"] if scan_proxy["mode"] == PROXY_MODE_CUSTOM else "",
            "proxy_mode": scan_proxy["mode"],
            "use_native_scanner": str(self.settings.value("scan_use_native", "false")).lower() == "true",
            "oast_mode": self.settings.value("scan_oast_mode", "auto"),
            "oast_server": self.settings.value("scan_oast_server", ""),
            "oast_token": self.settings.value("scan_oast_token", ""),
            "oast_poll_duration": int(self.settings.value("scan_oast_poll_duration", 5)),
            "oast_cooldown_period": int(self.settings.value("scan_oast_cooldown_period", 5)),
            "oast_cache_size": int(self.settings.value("scan_oast_cache_size", 5000)),
            "oast_eviction": int(self.settings.value("scan_oast_eviction", 60)),
            "oast_adapt_legacy": str(self.settings.value("scan_oast_adapt_legacy", "true")).lower() == "true"
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
        # Keep compatibility with callers that still pass the former scan proxy fields.
        if "proxy" in config or "proxy_mode" in config:
            proxy_url = config.get("proxy", "")
            proxy_mode = config.get("proxy_mode")
            if proxy_mode is None:
                proxy_mode = PROXY_MODE_CUSTOM if proxy_url else DEFAULT_PROXY_MODES[PROXY_SCOPE_SCAN]
            self.save_proxy_config(PROXY_SCOPE_SCAN, proxy_mode, proxy_url)
        self.settings.setValue("scan_use_native", "true" if config.get("use_native_scanner") else "false")
        self.settings.setValue("scan_oast_mode", config.get("oast_mode", "auto"))
        self.settings.setValue("scan_oast_server", config.get("oast_server", ""))
        self.settings.setValue("scan_oast_token", config.get("oast_token", ""))
        self.settings.setValue("scan_oast_poll_duration", config.get("oast_poll_duration", 5))
        self.settings.setValue("scan_oast_cooldown_period", config.get("oast_cooldown_period", 5))
        self.settings.setValue("scan_oast_cache_size", config.get("oast_cache_size", 5000))
        self.settings.setValue("scan_oast_eviction", config.get("oast_eviction", 60))
        self.settings.setValue("scan_oast_adapt_legacy", "true" if config.get("oast_adapt_legacy", True) else "false")
        self.settings.sync()  # 强制同步到磁盘
    
    # ============== 主题配置 ==============

    # 旧中文主题名 → 新英文内部 key 的迁移映射
    _THEME_MIGRATION = {
        "经典蓝": "classic_blue",
        "深邃蓝": "deep_blue",
        "清新绿": "fresh_green",
        "优雅紫": "elegant_purple",
    }

    def get_current_theme(self) -> str:
        """获取当前主题名称"""
        theme = self.settings.value("theme_name", "classic_blue")
        # 自动迁移旧中文主题名
        if theme in self._THEME_MIGRATION:
            theme = self._THEME_MIGRATION[theme]
            self.save_current_theme(theme)
        return theme
    
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

    # ============== 更新配置 ==============

    def get_auto_check_update(self) -> bool:
        """获取是否启动时自动检查更新"""
        return str(self.settings.value("update_auto_check", "true")).lower() == "true"

    def set_auto_check_update(self, enabled: bool):
        """设置是否启动时自动检查更新"""
        self.settings.setValue("update_auto_check", "true" if enabled else "false")
        self.settings.sync()

    # ============== UI 缩放配置 ==============

    def get_ui_scale(self) -> float:
        """获取 UI 缩放比例，返回 0 表示自动"""
        value = self.settings.value("ui_scale", "auto")
        if value == "auto":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def set_ui_scale(self, scale: float):
        """设置 UI 缩放比例，0 表示自动"""
        if scale == 0.0:
            self.settings.setValue("ui_scale", "auto")
        else:
            self.settings.setValue("ui_scale", str(scale))
        self.settings.sync()

    def get_language(self) -> str:
        """获取界面语言，默认 zh_CN"""
        return self.settings.value("language", "zh_CN")

    def set_language(self, lang_code: str):
        """设置界面语言"""
        self.settings.setValue("language", lang_code)
        self.settings.sync()



# 全局单例
_settings_instance = None

def get_settings() -> SettingsManager:
    """获取设置管理器单例"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager()
    return _settings_instance
