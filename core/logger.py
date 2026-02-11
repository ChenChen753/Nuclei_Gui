"""
统一日志管理模块
提供全局日志配置和便捷的日志记录接口
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler


class LoggerManager:
    """
    日志管理器 - 单例模式
    提供统一的日志配置和管理
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if LoggerManager._initialized:
            return
        
        LoggerManager._initialized = True
        
        # 日志目录
        self.log_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # 日志文件路径
        self.log_file = self.log_dir / "nuclei_gui.log"
        self.error_log_file = self.log_dir / "error.log"
        
        # 配置根日志器
        self._setup_root_logger()
        
        # 创建各模块日志器
        self.loggers = {}
    
    def _setup_root_logger(self):
        """配置根日志器"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 清除已有的处理器
        root_logger.handlers.clear()
        
        # 日志格式
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # 文件处理器 - 全部日志（轮转，最大 10MB，保留 5 个备份）
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # 错误日志文件处理器
        error_handler = RotatingFileHandler(
            self.error_log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # 控制台处理器（仅在调试模式下启用）
        if os.environ.get('NUCLEI_GUI_DEBUG', '').lower() == 'true':
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(simple_formatter)
            root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取指定名称的日志器
        
        Args:
            name: 日志器名称，通常使用模块名
            
        Returns:
            logging.Logger: 配置好的日志器
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        return self.loggers[name]
    
    def get_log_file_path(self) -> str:
        """获取日志文件路径"""
        return str(self.log_file)
    
    def clear_logs(self):
        """清空日志文件"""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write("# 日志已清空 - " + datetime.now().isoformat() + "\n")
            if self.error_log_file.exists():
                with open(self.error_log_file, 'w', encoding='utf-8') as f:
                    f.write("# 错误日志已清空 - " + datetime.now().isoformat() + "\n")
            return True
        except Exception:
            return False


# 全局单例
_logger_manager = None


def get_logger_manager() -> LoggerManager:
    """获取日志管理器单例"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager


def get_logger(name: str) -> logging.Logger:
    """
    便捷函数：获取指定名称的日志器
    
    使用示例:
        from core.logger import get_logger
        logger = get_logger(__name__)
        logger.info("这是一条信息日志")
        logger.error("这是一条错误日志", exc_info=True)
    """
    return get_logger_manager().get_logger(name)


class ModuleLoggers:
    """预定义的模块日志器，便于统一管理"""
    
    @staticmethod
    def scanner():
        """扫描模块日志器"""
        return get_logger("scanner")
    
    @staticmethod
    def poc():
        """POC 模块日志器"""
        return get_logger("poc")
    
    @staticmethod
    def fofa():
        """FOFA 模块日志器"""
        return get_logger("fofa")
    
    @staticmethod
    def ai():
        """AI 模块日志器"""
        return get_logger("ai")
    
    @staticmethod
    def ui():
        """UI 模块日志器"""
        return get_logger("ui")
    
    @staticmethod
    def database():
        """数据库模块日志器"""
        return get_logger("database")
    
    @staticmethod
    def settings():
        """设置模块日志器"""
        return get_logger("settings")


def log_exception(logger: logging.Logger, message: str, exc: Exception = None):
    """
    便捷函数：记录异常信息
    
    Args:
        logger: 日志器
        message: 错误消息
        exc: 异常对象（可选）
    """
    if exc:
        logger.error(message + ": " + type(exc).__name__ + ": " + str(exc), exc_info=True)
    else:
        logger.error(message, exc_info=True)


def log_operation(logger: logging.Logger, operation: str, success: bool, details: str = ""):
    """
    便捷函数：记录操作结果
    
    Args:
        logger: 日志器
        operation: 操作名称
        success: 是否成功
        details: 详细信息
    """
    status = "成功" if success else "失败"
    level = logging.INFO if success else logging.WARNING
    message = "[" + operation + "] " + status
    if details:
        message += " - " + details
    logger.log(level, message)
