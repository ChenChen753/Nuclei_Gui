"""
多语言支持模块
使用 JSON 字典方案，零额外依赖
"""
import json
import os

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh_CN': '简体中文',
    'en_US': 'English',
}

# 当前加载的翻译字典
_translations = {}
_current_language = 'zh_CN'
_translations_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))


def init_language(lang_code='zh_CN'):
    """初始化语言，加载翻译文件"""
    global _translations, _current_language
    _current_language = lang_code

    lang_file = os.path.join(_translations_dir, f'{lang_code}.json')
    if os.path.exists(lang_file):
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                _translations = json.load(f)
        except Exception as e:
            print(f"[i18n] Failed to load {lang_file}: {e}")
            _translations = {}
    else:
        _translations = {}


def get_current_language():
    """获取当前语言代码"""
    return _current_language


def tr(key, **kwargs):
    """
    获取翻译文本

    参数:
        key: 翻译键，如 'nav.scan_results'
        **kwargs: 占位符替换，如 tr('scan.progress', count=5)

    返回:
        翻译后的文本，如果 key 不存在则返回 key 本身
    """
    text = _translations.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
