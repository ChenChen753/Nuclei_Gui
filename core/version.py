"""
版本管理模块
统一管理应用程序版本信息
"""

from i18n import tr

__version__ = "2.5.2"
__version_info__ = (2, 5, 2)
__author__ = "辰辰"
__app_name__ = "Nuclei GUI Scanner"

# 版本历史 - 变更描述通过 tr() 获取
def get_version_history():
    """获取版本历史（支持多语言）"""
    return [
        {
            "version": "2.3.0",
            "date": "2026-01-27",
            "changes": [
                tr("version.v230_change1"),
                tr("version.v230_change2"),
                tr("version.v230_change3"),
                tr("version.v230_change4"),
                tr("version.v230_change5"),
                tr("version.v230_change6"),
                tr("version.v230_change7"),
                tr("version.v230_change8"),
            ]
        },
        {
            "version": "2.2.0",
            "date": "2026-01-27",
            "changes": [
                tr("version.v220_change1"),
                tr("version.v220_change2"),
                tr("version.v220_change3"),
                tr("version.v220_change4"),
                tr("version.v220_change5"),
                tr("version.v220_change6"),
            ]
        },
        {
            "version": "2.1.3",
            "date": "2026-01-20",
            "changes": [
                tr("version.v213_change1"),
                tr("version.v213_change2"),
                tr("version.v213_change3"),
            ]
        },
    ]


def get_version() -> str:
    """获取当前版本号"""
    return __version__


def get_version_info() -> tuple:
    """获取版本信息元组 (major, minor, patch)"""
    return __version_info__


def get_full_version_string() -> str:
    """获取完整版本字符串"""
    return f"{__app_name__} v{__version__} - By {__author__}"


def get_about_text() -> str:
    """获取关于信息文本"""
    return tr("version.about_text", app_name=__app_name__, version=__version__, author=__author__)


def check_for_updates() -> dict:
    """
    检查更新（预留接口）
    
    Returns:
        dict: 包含 has_update, latest_version, download_url 等信息
    """
    # TODO: 实现在线更新检查
    return {
        "has_update": False,
        "latest_version": __version__,
        "download_url": "",
        "changelog": ""
    }
