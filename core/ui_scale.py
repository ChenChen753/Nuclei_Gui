"""
UI 缩放系统 — 全局共享模块
所有 UI 文件（main.py、dialogs、fortress_style）统一从此导入
"""
import re

# 全局缩放因子（在程序启动时根据屏幕逻辑分辨率设置）
_UI_SCALE = 1.0


def set_ui_scale(value):
    """设置 UI 缩放因子"""
    global _UI_SCALE
    try:
        _UI_SCALE = max(0.75, min(1.25, float(value)))
    except (TypeError, ValueError):
        _UI_SCALE = 1.0


def get_ui_scale():
    """获取当前 UI 缩放因子"""
    return _UI_SCALE


def scaled(value):
    """根据缩放因子计算缩放后的整数值"""
    result = int(round(value * _UI_SCALE))
    if value > 0 and result < 1:
        return 1
    return result


def scaled_f(value):
    """根据缩放因子计算缩放后的浮点值（用于字体等）"""
    return round(value * _UI_SCALE, 1)


_STYLE_UNIT_RE = re.compile(r'(\d+)(px|pt)')


def _is_font_size_value(style_str, match_start):
    """判断当前数值是否属于 font-size，避免字体被 DPI 和 UI_SCALE 双重缩放。"""
    prop_start = max(style_str.rfind(';', 0, match_start), style_str.rfind('{', 0, match_start))
    prop = style_str[prop_start + 1:match_start].lower()
    return 'font-size' in prop


def scaled_style(style_str):
    """
    自动缩放样式字符串中的尺寸值。

    Qt 开启 High DPI 后，字体已经由系统/Qt 处理；这里仅缩放 padding、margin、
    border-radius、width、height 等控件尺寸，避免 font-size 二次缩放。
    """
    def replace_unit(match):
        num = int(match.group(1))
        unit = match.group(2)
        if unit == 'pt' or _is_font_size_value(style_str, match.start()):
            return match.group(0)
        return f"{scaled(num)}{unit}"
    return _STYLE_UNIT_RE.sub(replace_unit, style_str)


def calculate_auto_ui_scale(logical_width, logical_height):
    """
    根据 Qt 的逻辑可用分辨率计算 UI 缩放。

    High DPI 模式下 Qt Widgets 已工作在设备无关像素中，这里不再用 DPI 比例二次
    修正，只按可用逻辑尺寸做保守压缩。
    """
    width = int(logical_width or 0)
    height = int(logical_height or 0)

    if width >= 2560 and height >= 1400:
        return 0.85, 10
    if width >= 1800 and height >= 1000:
        return 0.9, 10
    if width >= 1500 and height >= 850:
        return 0.92, 10
    if width >= 1280 and height >= 720:
        return 0.95, 10
    if width >= 1100:
        return 0.9, 10
    return 0.85, 10
