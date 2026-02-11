"""
版本管理模块
统一管理应用程序版本信息
"""

__version__ = "2.3.0"
__version_info__ = (2, 3, 0)
__author__ = "辰辰"
__app_name__ = "Nuclei GUI Scanner"

# 版本历史
VERSION_HISTORY = [
    {
        "version": "2.3.0",
        "date": "2026-01-27",
        "changes": [
            "新增: 任务队列优先级支持",
            "新增: 断点续扫功能",
            "新增: 漏洞趋势分析模块",
            "新增: 扫描代理池（多代理轮换）",
            "新增: 性能监控面板",
            "新增: 定时扫描任务",
            "优化: 任务持久化存储",
            "优化: 自动重试失败任务",
        ]
    },
    {
        "version": "2.2.0",
        "date": "2026-01-27",
        "changes": [
            "新增: 统一日志管理系统",
            "新增: 安全存储模块（加密存储 API Key）",
            "新增: 快捷键支持",
            "优化: 线程安全改进",
            "优化: 异常处理完善",
            "修复: 重复的 stop() 方法定义",
        ]
    },
    {
        "version": "2.1.3",
        "date": "2026-01-20",
        "changes": [
            "新增: 多主题支持",
            "新增: AI 助手功能",
            "优化: 扫描性能提升",
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
    return f"""
{__app_name__}
版本: {__version__}
作者: {__author__}

一款基于 Nuclei 的漏洞扫描 GUI 工具，提供：
• POC 管理和编辑
• FOFA/Hunter/Shodan 资产搜索
• AI 辅助分析
• 扫描历史管理
• 漏洞报告生成
• 任务队列（优先级、断点续扫）
• 漏洞趋势分析
• 代理池管理
• 性能监控

GitHub: https://github.com/your-repo/nuclei-gui
"""


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
