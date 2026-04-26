import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QFileDialog, QTabWidget,
                             QSplitter, QGroupBox, QSpinBox, QMessageBox, QCheckBox,
                             QProgressBar, QGridLayout, QPlainTextEdit, QDialog, QComboBox,
                             QToolBar, QAction, QFrame, QStackedWidget, QListWidget,
                             QListWidgetItem, QSizePolicy, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSlot, QSettings, QSize, QUrl
from PyQt5.QtGui import QFont, QIcon, QColor, QPainter, QBrush, QPen, QDesktopServices

# ================= DPI 缩放系统（从公共模块导入） =================
from core.ui_scale import (
    set_ui_scale, get_ui_scale, scaled, scaled_f, scaled_style,
    calculate_auto_ui_scale,
)
from core.paths import ensure_external_layout, external_path, resource_path, is_frozen
from i18n import tr

# ================= 主题管理系统 =================

# 定义多种主题配色
THEME_PRESETS = {
    "classic_blue": {
        'nav_bg': '#ffffff',
        'nav_border': '#e5e7eb',
        'nav_active': '#3b82f6',
        'nav_hover': '#f3f4f6',
        'nav_text': '#1f2937',
        'nav_text_secondary': '#6b7280',
        'btn_primary': '#2563eb',
        'btn_primary_hover': '#1d4ed8',
        'btn_warning': '#f97316',
        'btn_warning_hover': '#ea580c',
        'btn_info': '#3b82f6',
        'btn_info_hover': '#2563eb',
        'btn_success': '#22c55e',
        'btn_success_hover': '#16a34a',
        'btn_purple': '#9b59b6',
        'btn_purple_hover': '#8e44ad',
        'content_bg': '#f8fafc',
        'table_header': '#f1f5f9',
        'table_row_alt': '#f8fafc',
        'status_high': '#3b82f6',
        'status_medium': '#f97316',
        'status_critical': '#ef4444',
        'status_low': '#22c55e',
        'text_primary': '#1f2937',
        'text_secondary': '#6b7280',
        'is_dark': False,
    },

    "deep_blue": {
        'nav_bg': '#1e293b',
        'nav_border': '#334155',
        'nav_active': '#60a5fa',
        'nav_hover': '#334155',
        'nav_text': '#f1f5f9',
        'nav_text_secondary': '#94a3b8',
        'btn_primary': '#3b82f6',
        'btn_primary_hover': '#2563eb',
        'btn_warning': '#f97316',
        'btn_warning_hover': '#ea580c',
        'btn_info': '#60a5fa',
        'btn_info_hover': '#3b82f6',
        'btn_success': '#22c55e',
        'btn_success_hover': '#16a34a',
        'btn_purple': '#a78bfa',
        'btn_purple_hover': '#8b5cf6',
        'content_bg': '#1e293b',
        'table_header': '#334155',
        'table_row_alt': '#283548',
        'status_high': '#60a5fa',
        'status_medium': '#f97316',
        'status_critical': '#ef4444',
        'status_low': '#22c55e',
        'text_primary': '#f1f5f9',
        'text_secondary': '#94a3b8',
        'is_dark': True,
    },

    "fresh_green": {
        'nav_bg': '#ffffff',
        'nav_border': '#e5e7eb',
        'nav_active': '#10b981',
        'nav_hover': '#f0fdf4',
        'nav_text': '#1f2937',
        'nav_text_secondary': '#6b7280',
        'btn_primary': '#10b981',
        'btn_primary_hover': '#059669',
        'btn_warning': '#f59e0b',
        'btn_warning_hover': '#d97706',
        'btn_info': '#06b6d4',
        'btn_info_hover': '#0891b2',
        'btn_success': '#22c55e',
        'btn_success_hover': '#16a34a',
        'btn_purple': '#8b5cf6',
        'btn_purple_hover': '#7c3aed',
        'content_bg': '#f8fafc',
        'table_header': '#f1f5f9',
        'table_row_alt': '#f8fafc',
        'status_high': '#10b981',
        'status_medium': '#f59e0b',
        'status_critical': '#ef4444',
        'status_low': '#22c55e',
        'text_primary': '#1f2937',
        'text_secondary': '#6b7280',
        'is_dark': False,
    },

    "elegant_purple": {
        'nav_bg': '#ffffff',
        'nav_border': '#e9d5ff',
        'nav_active': '#7c3aed',
        'nav_hover': '#f3e8ff',
        'nav_text': '#1f2937',
        'nav_text_secondary': '#6b7280',
        'btn_primary': '#7c3aed',
        'btn_primary_hover': '#6d28d9',
        'btn_warning': '#f97316',
        'btn_warning_hover': '#ea580c',
        'btn_info': '#8b5cf6',
        'btn_info_hover': '#7c3aed',
        'btn_success': '#22c55e',
        'btn_success_hover': '#16a34a',
        'btn_purple': '#a855f7',
        'btn_purple_hover': '#9333ea',
        'content_bg': '#faf5ff',
        'table_header': '#f3e8ff',
        'table_row_alt': '#faf5ff',
        'status_high': '#8b5cf6',
        'status_medium': '#f97316',
        'status_critical': '#ef4444',
        'status_low': '#22c55e',
        'text_primary': '#1f2937',
        'text_secondary': '#6b7280',
        'is_dark': False,
    },
}




# 当前主题颜色（将在程序启动时从设置加载）
FORTRESS_COLORS = THEME_PRESETS["classic_blue"].copy()

def get_theme_colors(theme_name: str) -> dict:
    """获取指定主题的颜色配置"""
    return THEME_PRESETS.get(theme_name, THEME_PRESETS["classic_blue"]).copy()

def get_available_themes() -> list:
    """获取所有可用的主题名称"""
    return list(THEME_PRESETS.keys())


def display_scan_status(status: str) -> str:
    """将内部扫描状态转换为当前语言的显示文本。"""
    status_map = {
        "completed": tr("scan_status.completed"),
        "failed": tr("scan_status.failed"),
        "stopped": tr("scan_status.stopped"),
        "cancelled": tr("scan_status.stopped"),
    }
    return status_map.get(str(status), str(status))


def display_severity(severity: str) -> str:
    """将 nuclei 严重程度转换为当前语言的显示文本。"""
    severity_key = str(severity or "unknown").lower()
    severity_map = {
        "critical": tr("severity.critical"),
        "high": tr("severity.high"),
        "medium": tr("severity.medium"),
        "low": tr("severity.low"),
        "info": tr("severity.info"),
        "unknown": tr("severity.unknown"),
    }
    return severity_map.get(severity_key, severity_key)


def message_text(text: str) -> str:
    """兼容翻译资源中历史遗留的字面量 \\n。"""
    return str(text).replace("\\n", "\n")




# 导入核心逻辑
from core.poc_library import POCLibrary
from core.nuclei_runner import NucleiScanThread
from core.settings_manager import get_settings
from core.target_utils import dedupe_targets, parse_targets_text
from core.version import __version__, __author__

# 导入弹窗组件
from dialogs.settings_dialog import SettingsDialog
from dialogs.fofa_dialog import FofaDialog
from dialogs.ai_assistant_dialog import AIAssistantDialog

class PlainPasteTextEdit(QPlainTextEdit):
    """
    重写粘贴行为，优先使用纯文本/URL，避免富文本污染
    """
    def insertFromMimeData(self, source):
        if source.hasUrls():
            # 优先提取 URL
            urls = []
            for url in source.urls():
                urls.append(url.toString())
            self.insertPlainText("\n".join(urls))
        elif source.hasText():
            # 其次使用纯文本
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nuclei GUI Scanner - By 辰辰")
        
        # 设置窗口图标（任务栏图标）
        self._set_window_icon()
        
        # 初始化设置管理器（需要先初始化才能加载主题和窗口设置）
        self.settings = get_settings()
        
        # 加载保存的主题
        self._load_saved_theme()
        
        # 设置窗口尺寸 - 优先恢复保存的大小，否则根据屏幕分辨率自适应
        self._setup_window_size()
        
        # 设置最小窗口尺寸
        self.setMinimumSize(scaled(900), scaled(600))
        
        # 初始化核心组件
        self.poc_library = POCLibrary()
        self.pending_scan_pocs = set()  # 待扫描的 POC 队列
        self.scan_thread = None
        self.scan_results_data = [] # 确保初始化

        
        # 初始化 UI
        self.init_ui()
        
        # 初始化快捷键
        self._setup_shortcuts()
        
        # 加载 POC 列表
        # 加载 POC 列表
        self.refresh_poc_list()
        
        # 连接任务队列信号
        from core.task_queue_manager import get_task_queue_manager
        self.task_queue = get_task_queue_manager()
        self.task_queue.task_status_changed.connect(self._on_task_status_changed)

        # 启动时检查更新（如果启用）
        self._check_update_on_startup()
    
    def _set_window_icon(self):
        """设置窗口图标（会显示在标题栏和任务栏）"""
        import os
        from PyQt5.QtGui import QIcon
        
        # 图标文件路径优先级：icon.ico > icon.png
        icon_paths = [
            resource_path("resources", "icon.ico"),
            resource_path("resources", "icon.png"),
            external_path("icon.ico"),
            external_path("icon.png"),
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(str(icon_path)))
                return
        
        # 如果没有找到图标文件，使用默认图标（可选：打印提示）
        # print("提示：未找到图标文件，使用默认图标。请将 icon.ico 或 icon.png 放入 resources 文件夹")
    
    def _setup_shortcuts(self):
        """设置全局快捷键"""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        
        # Ctrl+N: 新建扫描
        shortcut_new = QShortcut(QKeySequence("Ctrl+N"), self)
        shortcut_new.activated.connect(self.show_new_scan_dialog)
        
        # Ctrl+S: 保存设置
        shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut_save.activated.connect(self._save_all_settings)
        
        # Ctrl+E: 导出结果
        shortcut_export = QShortcut(QKeySequence("Ctrl+E"), self)
        shortcut_export.activated.connect(self.export_results)
        
        # F5: 刷新 POC 列表
        shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        shortcut_refresh.activated.connect(self.refresh_poc_list)
        
        # Escape: 停止扫描
        shortcut_stop = QShortcut(QKeySequence("Escape"), self)
        shortcut_stop.activated.connect(self._stop_scan_if_running)
        
        # Ctrl+1 到 Ctrl+6: 快速切换页面
        for i in range(1, 7):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            page_index = [2, 0, 1, 3, 4, 5][i-1]  # 映射到页面索引
            shortcut.activated.connect(lambda idx=page_index: self._switch_page(idx))
        
        # Ctrl+F: 聚焦搜索框
        shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_search.activated.connect(self._focus_search)
        
        # Ctrl+L: 显示日志
        shortcut_log = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut_log.activated.connect(self.show_log_dialog)
    
    def _stop_scan_if_running(self):
        """如果扫描正在运行则停止"""
        if self.scan_thread and self.scan_thread.isRunning():
            self.stop_scan()
    
    def _focus_search(self):
        """聚焦到当前页面的搜索框"""
        current_index = self.content_stack.currentIndex()
        if current_index == 1 and hasattr(self, 'poc_search_input'):
            self.poc_search_input.setFocus()
        elif current_index == 3 and hasattr(self, 'fofa_query_input'):
            self.fofa_query_input.setFocus()
    
    def _load_saved_theme(self):
        """加载保存的主题到全局变量"""
        global FORTRESS_COLORS
        theme_name = self.settings.get_current_theme()
        if theme_name in THEME_PRESETS:
            FORTRESS_COLORS.clear()
            FORTRESS_COLORS.update(THEME_PRESETS[theme_name])
    
    def _setup_window_size(self):
        """根据屏幕分辨率自动调整窗口大小，优先恢复保存的窗口大小"""
        from PyQt5.QtWidgets import QDesktopWidget
        
        screen = QDesktopWidget().screenGeometry()
        screen_width = screen.width()
        screen_height = screen.height()
        
        # 尝试恢复保存的窗口大小
        saved_geo = self.settings.get_window_geometry()
        if saved_geo["width"] > 0 and saved_geo["height"] > 0:
            # 确保窗口不会超出屏幕
            width = min(saved_geo["width"], screen_width - 50)
            height = min(saved_geo["height"], screen_height - 50)
            self.resize(width, height)
            
            # 恢复窗口位置，确保在屏幕内
            x = saved_geo["x"]
            y = saved_geo["y"]
            if x >= 0 and y >= 0:
                x = min(x, screen_width - width)
                y = min(y, screen_height - height)
                self.move(max(0, x), max(0, y))
            else:
                # 居中显示
                self.move((screen_width - self.width()) // 2, (screen_height - self.height()) // 2)
            
            # 恢复最大化状态
            if saved_geo["maximized"]:
                self.showMaximized()
            return
        
        # 没有保存的大小，根据屏幕分辨率设置默认窗口大小
        if screen_width >= 1920:
            # 高分辨率屏幕
            self.resize(scaled(1400), scaled(900))
        elif screen_width >= 1600:
            # 中高分辨率
            self.resize(scaled(1200), scaled(800))
        elif screen_width >= 1366:
            # 笔记本常见分辨率
            self.resize(scaled(1100), scaled(700))
        else:
            # 低分辨率屏幕
            self.resize(min(screen_width - scaled(50), scaled(1000)), min(screen_height - scaled(100), scaled(650)))
        
        # 居中显示
        self.move((screen_width - self.width()) // 2, (screen_height - self.height()) // 2)
    
    def closeEvent(self, event):
        """窗口关闭时保存窗口大小"""
        # 保存窗口几何信息
        if not self.isMaximized():
            geo = self.geometry()
            self.settings.save_window_geometry(geo.x(), geo.y(), geo.width(), geo.height(), False)
        else:
            # 最大化时保存原始大小
            self.settings.save_window_geometry(-1, -1, -1, -1, True)
        event.accept()


    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== 左侧导航栏 =====
        self.nav_panel = self._create_nav_panel()
        main_layout.addWidget(self.nav_panel)

        # ===== 右侧主内容区 =====
        self.content_area = QWidget()
        self.content_area.setStyleSheet(f"background-color: {FORTRESS_COLORS['content_bg']};")
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(scaled(20), scaled(15), scaled(20), scaled(15))
        content_layout.setSpacing(scaled(15))

        # 页面标题栏
        self.page_header = QWidget()
        header_layout = QHBoxLayout(self.page_header)
        header_layout.setContentsMargins(0, 0, 0, scaled(10))

        self.page_title = QLabel(tr("nav.dashboard"))
        self.page_title.setStyleSheet(scaled_style(f"""
            font-size: 20px;
            font-weight: bold;
            color: {FORTRESS_COLORS['text_primary']};
        """))
        header_layout.addWidget(self.page_title)

        self.page_subtitle = QLabel("")
        self.page_subtitle.setStyleSheet(scaled_style(f"color: {FORTRESS_COLORS['text_secondary']}; font-size: 13px;"))
        header_layout.addWidget(self.page_subtitle)

        header_layout.addStretch()

        # 状态指示器
        self.status_indicator = QLabel(tr("status.ready"))
        self.status_indicator.setStyleSheet(scaled_style(f"""
            color: {FORTRESS_COLORS['status_low']};
            font-size: 13px;
            padding: 5px 12px;
            background-color: #f0fdf4;
            border-radius: 12px;
        """))
        header_layout.addWidget(self.status_indicator)
        
        content_layout.addWidget(self.page_header)
        
        # 使用 QStackedWidget 切换不同页面内容
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)
        
        main_layout.addWidget(self.content_area, 1)
        
        # 应用全局样式（滚动条、下拉框等）
        from core.fortress_style import get_global_stylesheet
        self.setStyleSheet(get_global_stylesheet(FORTRESS_COLORS))

        
        # ===== 创建各个内容页面 =====
        # 页面 0: 扫描结果（默认）
        self.scan_tab = QWidget()
        self.setup_scan_tab()
        self.content_stack.addWidget(self.scan_tab)
        
        # 页面 1: POC 管理
        self.poc_tab = QWidget()
        self.setup_poc_tab()
        self.content_stack.addWidget(self.poc_tab)
        
        # 页面 2: 仪表盘
        self.dashboard_tab = QWidget()
        self.setup_dashboard_tab()
        self.content_stack.addWidget(self.dashboard_tab)
        
        # 页面 3: FOFA 搜索（内嵌页面）
        self.fofa_page = self._create_fofa_page()
        self.content_stack.addWidget(self.fofa_page)
        
        # 页面 4: AI 助手（内嵌页面）
        self.ai_page = self._create_ai_page()
        self.content_stack.addWidget(self.ai_page)
        
        # 页面 5: 设置（内嵌页面）
        self.settings_page = self._create_settings_page()
        self.content_stack.addWidget(self.settings_page)
        
        # 页面 6: 任务管理
        self.task_page = self._create_task_management_page()
        self.content_stack.addWidget(self.task_page)
        
        # 默认显示仪表盘页
        self.content_stack.setCurrentIndex(2)
        self._update_nav_selection(2)
        
        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {FORTRESS_COLORS['nav_bg']};
                border-top: 1px solid {FORTRESS_COLORS['nav_border']};
                color: {FORTRESS_COLORS['text_secondary']};
            }}
        """)
        self.status_bar.showMessage(tr("status.ready_simple"))
    
    def _create_nav_panel(self):
        """创建左侧导航栏（支持 DPI 缩放）"""
        nav = QFrame()
        nav.setFixedWidth(scaled(220))
        nav.setStyleSheet(f"""
            QFrame {{
                background-color: {FORTRESS_COLORS['nav_bg']};
                border-right: 1px solid {FORTRESS_COLORS['nav_border']};
            }}
        """)

        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(scaled(15), scaled(20), scaled(15), scaled(20))
        nav_layout.setSpacing(scaled(8))

        # Logo / 标题区域
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🛡️")
        logo_icon.setStyleSheet(scaled_style("font-size: 24px;"))
        logo_layout.addWidget(logo_icon)

        logo_text = QLabel("Nuclei Scanner")
        logo_text.setStyleSheet(scaled_style(f"""
            font-size: 16px;
            font-weight: bold;
            color: {FORTRESS_COLORS.get('nav_text', FORTRESS_COLORS['text_primary'])};
        """))
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        nav_layout.addLayout(logo_layout)

        nav_layout.addSpacing(scaled(20))

        # 新建扫描按钮（突出显示）
        self.btn_new_scan = QPushButton(tr("scan.new_scan"))
        self.btn_new_scan.setMinimumHeight(scaled(42))
        self.btn_new_scan.setCursor(Qt.PointingHandCursor)
        self.btn_new_scan.setStyleSheet(scaled_style(f"""
            QPushButton {{
                background-color: {FORTRESS_COLORS['btn_primary']};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {FORTRESS_COLORS['btn_primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: #1e40af;
            }}
        """))
        self.btn_new_scan.clicked.connect(self.show_new_scan_dialog)
        nav_layout.addWidget(self.btn_new_scan)

        nav_layout.addSpacing(scaled(20))

        # 导航项列表
        self.nav_items = []
        nav_data = [
            (tr("nav.dashboard"), 2),
            (tr("nav.scan_results"), 0),
            (tr("nav.task_management"), 6),
            (tr("nav.poc_management"), 1),
            (tr("nav.fofa_search"), 3),
            (tr("nav.ai_assistant"), 4),
            (tr("nav.settings"), 5),
        ]

        for text, page_index in nav_data:
            btn = QPushButton(text)
            btn.setMinimumHeight(scaled(40))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._get_nav_item_style(False))
            btn.clicked.connect(lambda checked, idx=page_index: self._switch_page(idx))
            nav_layout.addWidget(btn)
            self.nav_items.append((btn, page_index))

        nav_layout.addStretch()

        # 底部版本信息和 GitHub 链接
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(scaled(10), scaled(5), scaled(10), scaled(5))
        bottom_layout.setSpacing(scaled(8))

        version_label = QLabel(f"v{__version__} - By {__author__}")
        version_label.setStyleSheet(scaled_style(f"color: {FORTRESS_COLORS.get('nav_text_secondary', FORTRESS_COLORS['text_secondary'])}; font-size: 11px;"))
        bottom_layout.addWidget(version_label)

        # GitHub 按钮
        btn_github = QPushButton()
        btn_github.setIcon(QIcon(str(resource_path("resources", "github.svg"))))
        btn_github.setIconSize(QSize(scaled(18), scaled(18)))
        btn_github.setFixedSize(scaled(24), scaled(24))
        btn_github.setCursor(Qt.PointingHandCursor)
        btn_github.setToolTip(tr("common.visit_github"))
        btn_github.setStyleSheet(scaled_style("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """))
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/ChenChen753/Nuclei_Gui")))
        bottom_layout.addWidget(btn_github)

        nav_layout.addWidget(bottom_container)

        return nav
    
    def _get_nav_item_style(self, is_active):
        """获取导航项样式（支持 DPI 缩放）"""
        if is_active:
            return scaled_style(f"""
                QPushButton {{
                    background-color: #eff6ff;
                    color: {FORTRESS_COLORS['nav_active']};
                    border: none;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: bold;
                    text-align: left;
                    padding: 10px 15px;
                }}
            """)
        else:
            return scaled_style(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {FORTRESS_COLORS.get('nav_text', FORTRESS_COLORS['text_primary'])};
                    border: none;
                    border-radius: 8px;
                    font-size: 13px;
                    text-align: left;
                    padding: 10px 15px;
                }}
                QPushButton:hover {{
                    background-color: {FORTRESS_COLORS['nav_hover']};
                }}
            """)
    
    def _switch_page(self, page_index):
        """切换页面"""
        self.content_stack.setCurrentIndex(page_index)
        self._update_nav_selection(page_index)
        
        # 更新页面标题
        titles = {
            0: (tr("nav.scan_results"), tr("page.scan_results_desc")),
            1: (tr("nav.poc_management"), tr("page.poc_management_desc")),
            2: (tr("nav.dashboard"), tr("page.dashboard_desc")),
            3: (tr("nav.fofa_search"), tr("page.fofa_search_desc")),
            4: (tr("nav.ai_assistant"), tr("page.ai_assistant_desc")),
            5: (tr("nav.settings"), tr("page.settings_desc")),
            6: (tr("nav.task_management"), tr("page.task_management_desc")),
        }
        title, subtitle = titles.get(page_index, ("", ""))
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)
    
    def _update_nav_selection(self, active_index):
        """更新导航项选中状态"""
        for btn, page_index in self.nav_items:
            btn.setStyleSheet(self._get_nav_item_style(page_index == active_index))
    
    def _create_fofa_page(self):
        """创建 FOFA 搜索内嵌页面 - 完整功能"""
        from core.fofa_client import FofaSearchThread
        from core.history_manager import get_history_manager
        
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(scaled(15))
        
        # 使用分割器：左侧历史记录，右侧搜索区域
        splitter = QSplitter(Qt.Horizontal)
        
        # ===== 左侧：历史记录 =====
        history_widget = QWidget()
        history_widget.setStyleSheet(scaled_style(f"background-color: {FORTRESS_COLORS['content_bg']}; border-radius: 8px;"))
        history_widget.setMaximumWidth(scaled(280))
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(scaled(15), scaled(15), scaled(15), scaled(15))

        history_title = QLabel(tr("fofa.search_history"))
        history_title.setStyleSheet(scaled_style(f"font-weight: bold; color: {FORTRESS_COLORS['text_primary']}; font-size: 14px;"))
        history_layout.addWidget(history_title)
        
        self.fofa_history_list = QListWidget()
        from core.fortress_style import get_list_stylesheet
        self.fofa_history_list.setStyleSheet(get_list_stylesheet(FORTRESS_COLORS))
        self.fofa_history_list.itemDoubleClicked.connect(self._fofa_load_history_item)
        history_layout.addWidget(self.fofa_history_list)
        
        # 历史记录按钮
        history_btn_row = QHBoxLayout()
        btn_load = self._create_fortress_button(tr("common.load"), "info")
        btn_load.clicked.connect(self._fofa_load_selected_history)
        history_btn_row.addWidget(btn_load)
        
        btn_clear = self._create_fortress_button(tr("common.clear"), "warning")
        btn_clear.clicked.connect(self._fofa_clear_history)
        history_btn_row.addWidget(btn_clear)
        history_layout.addLayout(history_btn_row)
        
        splitter.addWidget(history_widget)
        
        # ===== 右侧：搜索和结果 =====
        right_widget = QWidget()
        right_widget.setStyleSheet(scaled_style(f"background-color: {FORTRESS_COLORS['content_bg']}; border-radius: 8px;"))
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(scaled(15), scaled(15), scaled(15), scaled(15))
        right_layout.setSpacing(scaled(15))

        # 搜索输入行
        search_row = QHBoxLayout()

        self.fofa_query_input = QLineEdit()
        self.fofa_query_input.setPlaceholderText(tr("fofa.query_placeholder"))
        self.fofa_query_input.setStyleSheet(scaled_style(f"""
            QLineEdit {{
                border: 1px solid {FORTRESS_COLORS['nav_border']};
                border-radius: 6px;
                padding: 10px 15px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {FORTRESS_COLORS['btn_primary']};
            }}
        """))
        self.fofa_query_input.returnPressed.connect(self._fofa_do_search)
        search_row.addWidget(self.fofa_query_input, 1)
        
        search_row.addWidget(QLabel(tr("fofa.count_label")))
        self.fofa_size_combo = QComboBox()
        self.fofa_size_combo.addItems(["100", "500", "1000", "5000", "10000"])
        self.fofa_size_combo.setEditable(True)
        self.fofa_size_combo.setFixedWidth(scaled(100))
        search_row.addWidget(self.fofa_size_combo)

        self.fofa_btn_search = self._create_fortress_button(tr("common.search"), "primary")
        self.fofa_btn_search.clicked.connect(self._fofa_do_search)
        search_row.addWidget(self.fofa_btn_search)

        right_layout.addLayout(search_row)

        # 状态和进度
        status_row = QHBoxLayout()
        self.fofa_status_label = QLabel(tr("fofa.status_ready"))
        self.fofa_status_label.setStyleSheet(f"color: {FORTRESS_COLORS['text_secondary']};")
        status_row.addWidget(self.fofa_status_label)

        status_row.addStretch()

        self.fofa_progress = QProgressBar()
        self.fofa_progress.setRange(0, 0)
        self.fofa_progress.setMaximumWidth(scaled(200))
        self.fofa_progress.hide()
        status_row.addWidget(self.fofa_progress)
        right_layout.addLayout(status_row)
        
        # 工具栏
        toolbar = QHBoxLayout()
        btn_select_all = self._create_fortress_button(tr("common.select_all"), "info")
        btn_select_all.clicked.connect(self._fofa_select_all)
        toolbar.addWidget(btn_select_all)
        
        btn_deselect = self._create_fortress_button(tr("common.deselect_all"), "info")
        btn_deselect.clicked.connect(self._fofa_deselect_all)
        toolbar.addWidget(btn_deselect)
        
        toolbar.addStretch()
        
        btn_import = self._create_fortress_button(tr("fofa.import_to_scan"), "primary")
        btn_import.clicked.connect(self._fofa_import_selected)
        toolbar.addWidget(btn_import)
        
        self.fofa_count_label = QLabel(tr("fofa.result_count", count=0))
        self.fofa_count_label.setStyleSheet(f"color: {FORTRESS_COLORS['text_secondary']};")
        toolbar.addWidget(self.fofa_count_label)
        right_layout.addLayout(toolbar)
        
        # 结果表格
        self.fofa_result_table = QTableWidget()
        self.fofa_result_table.setColumnCount(5)
        self.fofa_result_table.setHorizontalHeaderLabels([tr("fofa.col_select"), "URL/Host", "IP", tr("fofa.col_port"), tr("fofa.col_title")])
        self.fofa_result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.fofa_result_table.setColumnWidth(0, scaled(60))
        self.fofa_result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.fofa_result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.fofa_result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.fofa_result_table.setColumnWidth(3, scaled(70))
        self.fofa_result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.fofa_result_table.verticalHeader().setVisible(False)
        self.fofa_result_table.setAlternatingRowColors(True)
        from core.fortress_style import get_table_stylesheet
        self.fofa_result_table.setStyleSheet(get_table_stylesheet(FORTRESS_COLORS))
        right_layout.addWidget(self.fofa_result_table)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([250, 700])
        
        layout.addWidget(splitter)
        
        # 初始化数据
        self.fofa_history_manager = get_history_manager()
        self.fofa_current_results = []
        self._fofa_refresh_history()
        
        return page
    
    def _create_ai_page(self):
        """创建 AI 助手内嵌页面 - 完整功能"""
        from core.ai_client import AIWorkerThreadV2
        from core.history_manager import get_history_manager
        
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(scaled(15))

        # 使用 Tab 切换不同 AI 功能
        ai_tabs = QTabWidget()
        ai_tabs.setStyleSheet(scaled_style(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {FORTRESS_COLORS['content_bg']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {FORTRESS_COLORS['table_header']};
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                color: {FORTRESS_COLORS['text_primary']};
            }}
            QTabBar::tab:selected {{
                background-color: {FORTRESS_COLORS['content_bg']};
                font-weight: bold;
                color: {FORTRESS_COLORS['btn_primary']};
            }}
        """))
        
        # Tab 1: FOFA 语法生成
        fofa_tab = QWidget()
        fofa_layout = QVBoxLayout(fofa_tab)
        fofa_layout.setContentsMargins(scaled(20), scaled(20), scaled(20), scaled(20))

        fofa_layout.addWidget(QLabel(tr("ai.fofa_gen_prompt")))

        self.ai_fofa_input = QLineEdit()
        self.ai_fofa_input.setPlaceholderText(tr("ai.fofa_input_placeholder"))
        self.ai_fofa_input.setStyleSheet(scaled_style(f"""
            QLineEdit {{
                border: 1px solid {FORTRESS_COLORS['nav_border']};
                border-radius: 6px;
                padding: 12px 15px;
                font-size: 14px;
            }}
        """))
        fofa_layout.addWidget(self.ai_fofa_input)

        self.ai_fofa_btn = self._create_fortress_button(tr("ai.generate_fofa"), "primary")
        self.ai_fofa_btn.clicked.connect(lambda: self._ai_do_task("fofa", self.ai_fofa_input, self.ai_fofa_output))
        fofa_layout.addWidget(self.ai_fofa_btn)

        self.ai_fofa_output = QTextEdit()
        self.ai_fofa_output.setReadOnly(True)
        self.ai_fofa_output.setPlaceholderText(tr("ai.fofa_output_placeholder"))
        self.ai_fofa_output.setStyleSheet(scaled_style(f"""
            QTextEdit {{
                border: 1px solid {FORTRESS_COLORS['nav_border']};
                border-radius: 6px;
                padding: 10px;
                background-color: {FORTRESS_COLORS['content_bg']};
            }}
        """))
        fofa_layout.addWidget(self.ai_fofa_output)

        fofa_btn_row = QHBoxLayout()
        btn_copy_fofa = self._create_fortress_button(tr("ai.copy_syntax"), "info")
        btn_copy_fofa.clicked.connect(lambda: self._copy_text(self.ai_fofa_output))
        fofa_btn_row.addWidget(btn_copy_fofa)

        btn_to_fofa = self._create_fortress_button(tr("ai.goto_fofa_search"), "primary")
        btn_to_fofa.clicked.connect(self._ai_copy_fofa_and_open)
        fofa_btn_row.addWidget(btn_to_fofa)
        fofa_btn_row.addStretch()
        fofa_layout.addLayout(fofa_btn_row)

        ai_tabs.addTab(fofa_tab, tr("ai.tab_fofa_gen"))

        # Tab 2: 漏洞分析
        analyze_tab = QWidget()
        analyze_layout = QVBoxLayout(analyze_tab)
        analyze_layout.setContentsMargins(scaled(20), scaled(20), scaled(20), scaled(20))

        analyze_layout.addWidget(QLabel(tr("ai.analyze_prompt")))

        self.ai_analyze_input = QTextEdit()
        self.ai_analyze_input.setPlaceholderText(tr("ai.analyze_input_placeholder"))
        self.ai_analyze_input.setMaximumHeight(scaled(150))
        analyze_layout.addWidget(self.ai_analyze_input)
        
        self.ai_analyze_btn = self._create_fortress_button(tr("ai.analyze_vuln"), "primary")
        self.ai_analyze_btn.clicked.connect(lambda: self._ai_do_task("analyze", self.ai_analyze_input, self.ai_analyze_output))
        analyze_layout.addWidget(self.ai_analyze_btn)
        
        self.ai_analyze_output = QTextEdit()
        self.ai_analyze_output.setReadOnly(True)
        analyze_layout.addWidget(self.ai_analyze_output)
        
        ai_tabs.addTab(analyze_tab, tr("ai.tab_vuln_analysis"))

        layout.addWidget(ai_tabs)
        
        # 初始化
        self.ai_history_manager = get_history_manager()
        
        return page
    
    def _create_settings_page(self):
        """创建设置内嵌页面 - 完整功能"""
        from core.settings_manager import get_settings
        
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(scaled(15))

        # 使用 Tab 分组设置
        settings_tabs = QTabWidget()
        settings_tabs.setStyleSheet(scaled_style(f"""
            QTabWidget::pane {{
                border: none;
                background-color: {FORTRESS_COLORS['content_bg']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {FORTRESS_COLORS['table_header']};
                padding: 10px 25px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                color: {FORTRESS_COLORS['text_primary']};
            }}
            QTabBar::tab:selected {{
                background-color: {FORTRESS_COLORS['content_bg']};
                font-weight: bold;
                color: {FORTRESS_COLORS['btn_primary']};
            }}
        """))
        
        # Tab 1: 扫描参数
        scan_tab = QWidget()
        scan_layout = QVBoxLayout(scan_tab)
        scan_layout.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        scan_layout.setSpacing(scaled(15))

        # 使用表单布局
        form_container = QWidget()
        form_layout = QGridLayout(form_container)
        form_layout.setSpacing(scaled(15))
        
        row = 0
        # 超时时间
        form_layout.addWidget(QLabel(tr("settings.request_timeout")), row, 0)
        self.settings_timeout = QSpinBox()
        self.settings_timeout.setRange(1, 60)
        self.settings_timeout.setValue(5)
        form_layout.addWidget(self.settings_timeout, row, 1)
        
        row += 1
        # 并发数
        form_layout.addWidget(QLabel(tr("settings.concurrent_requests")), row, 0)
        self.settings_rate_limit = QSpinBox()
        self.settings_rate_limit.setRange(1, 1000)
        self.settings_rate_limit.setValue(150)
        form_layout.addWidget(self.settings_rate_limit, row, 1)
        
        row += 1
        # 批量大小
        form_layout.addWidget(QLabel(tr("settings.bulk_size")), row, 0)
        self.settings_bulk_size = QSpinBox()
        self.settings_bulk_size.setRange(1, 100)
        self.settings_bulk_size.setValue(25)
        form_layout.addWidget(self.settings_bulk_size, row, 1)
        
        row += 1
        # 重试次数
        form_layout.addWidget(QLabel(tr("settings.retries")), row, 0)
        self.settings_retries = QSpinBox()
        self.settings_retries.setRange(0, 10)
        self.settings_retries.setValue(0)
        form_layout.addWidget(self.settings_retries, row, 1)
        
        row += 1
        # 代理设置
        form_layout.addWidget(QLabel(tr("settings.proxy_server")), row, 0)
        self.settings_proxy = QLineEdit()
        self.settings_proxy.setPlaceholderText(tr("settings.proxy_placeholder"))
        form_layout.addWidget(self.settings_proxy, row, 1)
        
        row += 1
        # 选项 - 使用水平布局
        options_label = QLabel(tr("settings.advanced_options"))
        options_label.setStyleSheet(f"font-weight: bold; color: {FORTRESS_COLORS['text_primary']};")
        form_layout.addWidget(options_label, row, 0, 1, 2)
        
        row += 1
        options_row1 = QHBoxLayout()
        self.settings_follow_redirects = QCheckBox(tr("settings.follow_redirects"))
        options_row1.addWidget(self.settings_follow_redirects)
        
        self.settings_stop_at_first = QCheckBox(tr("settings.stop_at_first"))
        options_row1.addWidget(self.settings_stop_at_first)
        options_row1.addStretch()
        form_layout.addLayout(options_row1, row, 0, 1, 2)
        
        row += 1
        options_row2 = QHBoxLayout()
        self.settings_no_httpx = QCheckBox(tr("settings.skip_probe"))
        options_row2.addWidget(self.settings_no_httpx)
        
        self.settings_verbose = QCheckBox(tr("settings.verbose_log"))
        options_row2.addWidget(self.settings_verbose)
        options_row2.addStretch()
        form_layout.addLayout(options_row2, row, 0, 1, 2)
        
        row += 1
        self.settings_use_native = QCheckBox(tr("settings.use_native_scanner"))
        form_layout.addWidget(self.settings_use_native, row, 0, 1, 2)

        scan_layout.addWidget(form_container)
        scan_layout.addStretch()
        
        settings_tabs.addTab(scan_tab, tr("settings.tab_scan_params"))

        # Tab 2: DNSLog / OAST
        dnslog_tab = QWidget()
        dnslog_layout = QVBoxLayout(dnslog_tab)
        dnslog_layout.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        dnslog_layout.setSpacing(scaled(15))

        oast_group = QGroupBox(tr("settings.oast.group"))
        oast_layout = QGridLayout()
        oast_layout.setSpacing(scaled(12))
        oast_layout.setColumnStretch(1, 1)
        oast_layout.setColumnStretch(3, 1)

        oast_layout.addWidget(QLabel(tr("settings.oast.mode")), 0, 0)
        self.settings_oast_mode = QComboBox()
        self.settings_oast_mode.addItem(tr("settings.oast.mode_auto"), "auto")
        self.settings_oast_mode.addItem(tr("settings.oast.mode_off"), "off")
        self.settings_oast_mode.addItem(tr("settings.oast.mode_force"), "force")
        oast_layout.addWidget(self.settings_oast_mode, 0, 1, 1, 3)

        oast_layout.addWidget(QLabel(tr("settings.oast.server")), 1, 0)
        self.settings_oast_server = QLineEdit()
        self.settings_oast_server.setPlaceholderText(tr("settings.oast.server_placeholder"))
        oast_layout.addWidget(self.settings_oast_server, 1, 1, 1, 3)

        oast_layout.addWidget(QLabel(tr("settings.oast.token")), 2, 0)
        self.settings_oast_token = QLineEdit()
        self.settings_oast_token.setEchoMode(QLineEdit.Password)
        self.settings_oast_token.setPlaceholderText(tr("settings.oast.token_placeholder"))
        oast_layout.addWidget(self.settings_oast_token, 2, 1, 1, 3)

        oast_layout.addWidget(QLabel(tr("settings.oast.poll_duration")), 3, 0)
        self.settings_oast_poll = QSpinBox()
        self.settings_oast_poll.setRange(1, 300)
        self.settings_oast_poll.setValue(5)
        oast_layout.addWidget(self.settings_oast_poll, 3, 1)

        oast_layout.addWidget(QLabel(tr("settings.oast.cooldown")), 3, 2)
        self.settings_oast_cooldown = QSpinBox()
        self.settings_oast_cooldown.setRange(1, 300)
        self.settings_oast_cooldown.setValue(5)
        oast_layout.addWidget(self.settings_oast_cooldown, 3, 3)

        oast_layout.addWidget(QLabel(tr("settings.oast.cache_size")), 4, 0)
        self.settings_oast_cache = QSpinBox()
        self.settings_oast_cache.setRange(100, 100000)
        self.settings_oast_cache.setValue(5000)
        oast_layout.addWidget(self.settings_oast_cache, 4, 1)

        oast_layout.addWidget(QLabel(tr("settings.oast.eviction")), 4, 2)
        self.settings_oast_eviction = QSpinBox()
        self.settings_oast_eviction.setRange(10, 3600)
        self.settings_oast_eviction.setValue(60)
        oast_layout.addWidget(self.settings_oast_eviction, 4, 3)

        self.settings_oast_adapt_legacy = QCheckBox(tr("settings.oast.adapt_legacy"))
        self.settings_oast_adapt_legacy.setChecked(True)
        oast_layout.addWidget(self.settings_oast_adapt_legacy, 5, 0, 1, 4)

        oast_hint = QLabel(tr("settings.oast.hint"))
        oast_hint.setWordWrap(True)
        oast_hint.setStyleSheet(f"color: {FORTRESS_COLORS['text_secondary']}; font-size: 12px;")
        oast_layout.addWidget(oast_hint, 6, 0, 1, 4)

        oast_group.setLayout(oast_layout)
        dnslog_layout.addWidget(oast_group)
        dnslog_layout.addStretch()

        settings_tabs.addTab(dnslog_tab, tr("settings.tab_dnslog"))
        
        # Tab 3: FOFA 配置
        fofa_tab = QWidget()
        fofa_layout = QVBoxLayout(fofa_tab)
        fofa_layout.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        fofa_layout.setSpacing(scaled(15))

        fofa_form = QGridLayout()
        fofa_form.setSpacing(scaled(15))
        
        fofa_form.addWidget(QLabel("FOFA API URL:"), 0, 0)
        self.settings_fofa_url = QLineEdit()
        self.settings_fofa_url.setPlaceholderText("https://fofa.info/api/v1/search/all")
        fofa_form.addWidget(self.settings_fofa_url, 0, 1)
        
        fofa_form.addWidget(QLabel("Email:"), 1, 0)
        self.settings_fofa_email = QLineEdit()
        fofa_form.addWidget(self.settings_fofa_email, 1, 1)
        
        fofa_form.addWidget(QLabel("API Key:"), 2, 0)
        self.settings_fofa_key = QLineEdit()
        self.settings_fofa_key.setEchoMode(QLineEdit.Password)
        fofa_form.addWidget(self.settings_fofa_key, 2, 1)
        
        fofa_layout.addLayout(fofa_form)
        
        btn_test_fofa = self._create_fortress_button(tr("settings.test_connection"), "info")
        btn_test_fofa.clicked.connect(self._test_fofa_connection)
        fofa_layout.addWidget(btn_test_fofa)

        fofa_layout.addStretch()
        settings_tabs.addTab(fofa_tab, tr("settings.tab_fofa_config"))
        
        # Tab 3: AI 配置
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        ai_layout.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        ai_layout.setSpacing(scaled(15))

        ai_form = QGridLayout()
        ai_form.setSpacing(scaled(15))

        # AI 预设选择行
        ai_form.addWidget(QLabel(tr("settings.ai_preset")), 0, 0)
        preset_row = QHBoxLayout()
        self.settings_ai_preset = QComboBox()
        self.settings_ai_preset.setMinimumWidth(scaled(200))
        self._load_ai_presets_to_settings_combo()
        self.settings_ai_preset.currentIndexChanged.connect(self._on_ai_preset_changed)
        preset_row.addWidget(self.settings_ai_preset)

        btn_add_preset = self._create_fortress_button(tr("common.add"), "info")
        btn_add_preset.clicked.connect(self._add_ai_preset)
        preset_row.addWidget(btn_add_preset)

        btn_rename_preset = self._create_fortress_button(tr("common.rename"), "info")
        btn_rename_preset.clicked.connect(self._rename_ai_preset)
        preset_row.addWidget(btn_rename_preset)

        btn_del_preset = self._create_fortress_button(tr("common.delete"), "warning")
        btn_del_preset.clicked.connect(self._delete_ai_preset)
        preset_row.addWidget(btn_del_preset)

        preset_row.addStretch()
        ai_form.addLayout(preset_row, 0, 1)

        ai_form.addWidget(QLabel("API URL:"), 1, 0)
        self.settings_ai_url = QLineEdit()
        self.settings_ai_url.setPlaceholderText(tr("settings.api_url_placeholder"))
        ai_form.addWidget(self.settings_ai_url, 1, 1)

        ai_form.addWidget(QLabel("API Key:"), 2, 0)
        api_key_row = QHBoxLayout()
        self.settings_ai_key = QLineEdit()
        self.settings_ai_key.setEchoMode(QLineEdit.Password)
        self.settings_ai_key.setPlaceholderText(tr("settings.api_key_placeholder"))
        api_key_row.addWidget(self.settings_ai_key)

        self.btn_toggle_key = QPushButton("👁")
        self.btn_toggle_key.setFixedSize(scaled(30), scaled(30))
        self.btn_toggle_key.setToolTip(tr("settings.toggle_api_key"))
        self.btn_toggle_key.clicked.connect(self._toggle_api_key_visibility)
        api_key_row.addWidget(self.btn_toggle_key)
        ai_form.addLayout(api_key_row, 2, 1)
        
        ai_form.addWidget(QLabel(tr("settings.model")), 3, 0)
        self.settings_ai_model = QComboBox()
        self.settings_ai_model.setEditable(True)
        self.settings_ai_model.addItems([
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "deepseek-chat",
            "deepseek-coder",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "qwen-turbo",
            "qwen-plus",
            "qwen-max",
            "glm-4",
            "glm-3-turbo"
        ])
        self.settings_ai_model.setCurrentText("")
        self.settings_ai_model.lineEdit().setPlaceholderText(tr("settings.model_placeholder"))
        ai_form.addWidget(self.settings_ai_model, 3, 1)

        # 操作按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(scaled(10))

        btn_test_ai = self._create_fortress_button(tr("settings.test_connection"), "info")
        btn_test_ai.clicked.connect(self._test_ai_connection)
        btn_row.addWidget(btn_test_ai)

        btn_save_ai = self._create_fortress_button(tr("settings.save_config"), "primary")
        btn_save_ai.clicked.connect(self._save_ai_preset_config)
        btn_row.addWidget(btn_save_ai)

        btn_row.addStretch()
        ai_form.addLayout(btn_row, 4, 1)

        ai_layout.addLayout(ai_form)
        ai_layout.addStretch()
        settings_tabs.addTab(ai_tab, tr("settings.tab_ai_config"))

        # Tab 4: 主题设置
        theme_tab = QWidget()
        theme_layout = QVBoxLayout(theme_tab)
        theme_layout.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        theme_layout.setSpacing(scaled(15))

        theme_form = QGridLayout()
        theme_form.setSpacing(scaled(15))

        theme_form.addWidget(QLabel(tr("settings.select_theme")), 0, 0)
        self.settings_theme_combo = QComboBox()
        self.settings_theme_combo.setMinimumWidth(scaled(200))
        for theme_key in get_available_themes():
            self.settings_theme_combo.addItem(tr(f"theme.{theme_key}"), theme_key)
        # 设置当前主题
        current_theme = self.settings.get_current_theme()
        index = self.settings_theme_combo.findData(current_theme)
        if index >= 0:
            self.settings_theme_combo.setCurrentIndex(index)
        theme_form.addWidget(self.settings_theme_combo, 0, 1)

        # 主题预览区域
        theme_form.addWidget(QLabel(tr("settings.theme_preview")), 1, 0, Qt.AlignTop)
        self.theme_preview_widget = QWidget()
        self.theme_preview_widget.setFixedSize(scaled(300), scaled(120))
        self._update_theme_preview()
        theme_form.addWidget(self.theme_preview_widget, 1, 1)

        # 连接主题切换信号
        self.settings_theme_combo.currentIndexChanged.connect(
            lambda idx: self._on_theme_preview_changed(self.settings_theme_combo.itemData(idx))
        )

        # 应用主题按钮
        btn_apply_theme = self._create_fortress_button(tr("settings.apply_theme"), "primary")
        btn_apply_theme.clicked.connect(self._apply_selected_theme)
        theme_form.addWidget(btn_apply_theme, 2, 1)

        theme_tip = QLabel(tr("settings.theme_restart_tip"))
        theme_tip.setStyleSheet(f"color: {FORTRESS_COLORS['text_secondary']}; font-style: italic;")
        theme_form.addWidget(theme_tip, 3, 0, 1, 2)

        # UI 缩放设置
        theme_form.addWidget(QLabel(tr("settings.ui_scale")), 4, 0)
        ui_scale_row = QHBoxLayout()
        self.settings_ui_scale_combo = QComboBox()
        self.settings_ui_scale_combo.addItems([tr("settings.auto"), "0.8", "0.85", "0.9", "0.95", "1.0", "1.05", "1.1", "1.15", "1.2"])
        self.settings_ui_scale_combo.setMinimumWidth(scaled(100))
        # 读取当前设置
        current_scale = self.settings.get_ui_scale()
        if current_scale == 0:
            self.settings_ui_scale_combo.setCurrentText(tr("settings.auto"))
        else:
            self.settings_ui_scale_combo.setCurrentText(str(current_scale))
        ui_scale_row.addWidget(self.settings_ui_scale_combo)

        btn_apply_scale = self._create_fortress_button(tr("settings.apply_scale"), "info")
        btn_apply_scale.clicked.connect(self._apply_ui_scale)
        ui_scale_row.addWidget(btn_apply_scale)
        ui_scale_row.addStretch()
        theme_form.addLayout(ui_scale_row, 4, 1)

        scale_tip = QLabel(tr("settings.scale_tip"))
        scale_tip.setStyleSheet(f"color: {FORTRESS_COLORS['text_secondary']}; font-style: italic;")
        scale_tip.setWordWrap(True)
        theme_form.addWidget(scale_tip, 5, 0, 1, 2)

        # 语言设置
        theme_form.addWidget(QLabel(tr("settings.general.ui_language")), 6, 0)
        lang_row = QHBoxLayout()
        self.settings_lang_combo = QComboBox()
        self.settings_lang_combo.setMinimumWidth(scaled(200))
        from i18n import SUPPORTED_LANGUAGES
        for code, name in SUPPORTED_LANGUAGES.items():
            self.settings_lang_combo.addItem(f"{name} ({code})", code)
        # 读取当前语言
        current_lang = self.settings.get_language()
        lang_index = self.settings_lang_combo.findData(current_lang)
        if lang_index >= 0:
            self.settings_lang_combo.setCurrentIndex(lang_index)
        lang_row.addWidget(self.settings_lang_combo)

        btn_apply_lang = self._create_fortress_button(tr("common.apply"), "info")
        btn_apply_lang.clicked.connect(self._apply_language)
        lang_row.addWidget(btn_apply_lang)
        lang_row.addStretch()
        theme_form.addLayout(lang_row, 6, 1)

        lang_tip = QLabel(tr("settings.general.language_restart_hint"))
        lang_tip.setStyleSheet(f"color: {FORTRESS_COLORS['text_secondary']}; font-style: italic;")
        theme_form.addWidget(lang_tip, 7, 0, 1, 2)

        theme_layout.addLayout(theme_form)
        theme_layout.addStretch()
        settings_tabs.addTab(theme_tab, tr("settings.tab_theme"))
        
        # Tab 5: Nuclei 管理
        nuclei_tab = QWidget()
        nuclei_layout = QVBoxLayout(nuclei_tab)
        nuclei_layout.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        nuclei_layout.setSpacing(scaled(15))

        # 系统信息组
        info_group = QGroupBox(tr("nuclei.system_info"))
        info_group.setStyleSheet(scaled_style(f"""
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {FORTRESS_COLORS['text_primary']};
                border: 1px solid {FORTRESS_COLORS['nav_border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }}
        """))
        info_layout = QGridLayout(info_group)
        info_layout.setSpacing(scaled(10))
        
        import platform
        system = platform.system()
        machine = platform.machine()
        info_layout.addWidget(QLabel(tr("nuclei.os")), 0, 0)
        info_layout.addWidget(QLabel(f"{system} {machine}"), 0, 1)
        
        info_layout.addWidget(QLabel(tr("nuclei.status_label")), 1, 0)
        self.nuclei_status_label = QLabel(tr("nuclei.detecting"))
        info_layout.addWidget(self.nuclei_status_label, 1, 1)
        
        nuclei_layout.addWidget(info_group)
        
        # Nuclei 下载管理组
        download_group = QGroupBox(tr("nuclei.download_management"))
        download_group.setStyleSheet(scaled_style(f"""
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {FORTRESS_COLORS['text_primary']};
                border: 1px solid {FORTRESS_COLORS['nav_border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }}
        """))
        download_layout = QVBoxLayout(download_group)
        
        # 说明文本
        desc_label = QLabel(tr("nuclei.download_desc"))
        desc_label.setStyleSheet(scaled_style(f"color: {FORTRESS_COLORS['text_secondary']}; font-size: 12px; padding: 10px;"))
        download_layout.addWidget(desc_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.download_nuclei_btn = self._create_fortress_button(tr("nuclei.download_latest"), "info")
        self.download_nuclei_btn.clicked.connect(self._download_nuclei)
        btn_layout.addWidget(self.download_nuclei_btn)
        
        self.check_nuclei_btn = self._create_fortress_button(tr("nuclei.detect"), "success")
        self.check_nuclei_btn.clicked.connect(self._check_nuclei_status)
        btn_layout.addWidget(self.check_nuclei_btn)
        
        download_layout.addLayout(btn_layout)
        
        # 进度显示
        self.nuclei_progress_label = QLabel("")
        self.nuclei_progress_label.setStyleSheet(scaled_style(f"color: {FORTRESS_COLORS['text_secondary']}; font-size: 11px; padding: 5px;"))
        download_layout.addWidget(self.nuclei_progress_label)
        
        nuclei_layout.addWidget(download_group)
        nuclei_layout.addStretch()

        settings_tabs.addTab(nuclei_tab, tr("settings.tab_nuclei"))

        # 初始检测 Nuclei 状态
        self._check_nuclei_status()

        # Tab 6: 更新设置
        update_tab = QWidget()
        update_layout = QVBoxLayout(update_tab)
        update_layout.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        update_layout.setSpacing(scaled(15))

        # 版本信息组
        version_group = QGroupBox(tr("update.version_info"))
        version_group.setStyleSheet(scaled_style(f"""
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {FORTRESS_COLORS['text_primary']};
                border: 1px solid {FORTRESS_COLORS['nav_border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }}
        """))
        version_layout = QGridLayout(version_group)
        version_layout.setSpacing(scaled(10))

        from core.updater import get_current_version
        version_layout.addWidget(QLabel(tr("update.current_version")), 0, 0)
        self.update_current_version_label = QLabel(f"v{get_current_version()}")
        self.update_current_version_label.setStyleSheet(f"font-weight: bold; color: {FORTRESS_COLORS['btn_primary']};")
        version_layout.addWidget(self.update_current_version_label, 0, 1)

        version_layout.addWidget(QLabel(tr("update.latest_version")), 1, 0)
        self.update_latest_version_label = QLabel(tr("update.not_checked"))
        self.update_latest_version_label.setStyleSheet(f"color: {FORTRESS_COLORS['text_secondary']};")
        version_layout.addWidget(self.update_latest_version_label, 1, 1)

        update_layout.addWidget(version_group)

        # 更新设置组
        update_settings_group = QGroupBox(tr("update.update_settings"))
        update_settings_group.setStyleSheet(version_group.styleSheet())
        update_settings_layout = QVBoxLayout(update_settings_group)

        self.auto_update_checkbox = QCheckBox(tr("update.auto_check_on_startup"))
        self.auto_update_checkbox.setChecked(self.settings.get_auto_check_update())
        self.auto_update_checkbox.setToolTip(tr("update.auto_check_tooltip"))
        update_settings_layout.addWidget(self.auto_update_checkbox)

        preserve_label = QLabel(tr("update.preserve_data_desc"))
        preserve_label.setStyleSheet(scaled_style(f"color: {FORTRESS_COLORS['text_secondary']}; font-size: 11px; padding: 10px; background: {FORTRESS_COLORS['nav_bg']}; border-radius: 4px;"))
        update_settings_layout.addWidget(preserve_label)

        update_layout.addWidget(update_settings_group)

        # 更新操作组
        update_action_group = QGroupBox(tr("update.update_actions"))
        update_action_group.setStyleSheet(version_group.styleSheet())
        update_action_layout = QVBoxLayout(update_action_group)

        btn_row = QHBoxLayout()
        self.check_update_btn = self._create_fortress_button(tr("update.check_update"), "info")
        self.check_update_btn.clicked.connect(self._check_for_updates)
        btn_row.addWidget(self.check_update_btn)

        self.do_update_btn = self._create_fortress_button(tr("update.download_update"), "success")
        self.do_update_btn.setEnabled(False)
        self.do_update_btn.clicked.connect(self._do_update)
        btn_row.addWidget(self.do_update_btn)

        btn_row.addStretch()
        update_action_layout.addLayout(btn_row)

        # 更新进度条
        self.update_progress_bar = QProgressBar()
        self.update_progress_bar.setVisible(False)
        self.update_progress_bar.setStyleSheet(scaled_style(f"""
            QProgressBar {{
                border: 2px solid {FORTRESS_COLORS['nav_border']};
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {FORTRESS_COLORS['btn_success']};
                border-radius: 3px;
            }}
        """))
        update_action_layout.addWidget(self.update_progress_bar)

        # 状态标签
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet(scaled_style(f"color: {FORTRESS_COLORS['text_secondary']}; font-size: 11px; padding: 5px;"))
        update_action_layout.addWidget(self.update_status_label)

        # 更新日志
        self.release_notes_text = QTextEdit()
        self.release_notes_text.setReadOnly(True)
        self.release_notes_text.setMaximumHeight(scaled(120))
        self.release_notes_text.setPlaceholderText(tr("update.release_notes_placeholder"))
        self.release_notes_text.setStyleSheet(scaled_style(f"""
            QTextEdit {{
                border: 1px solid {FORTRESS_COLORS['nav_border']};
                border-radius: 4px;
                padding: 5px;
                font-size: 11px;
                background: {FORTRESS_COLORS['content_bg']};
                color: {FORTRESS_COLORS['text_primary']};
            }}
        """))
        update_action_layout.addWidget(self.release_notes_text)

        update_layout.addWidget(update_action_group)
        update_layout.addStretch()

        settings_tabs.addTab(update_tab, tr("settings.tab_update"))

        # 存储下载信息
        self._update_download_url = None
        self._update_version = None

        layout.addWidget(settings_tabs)


        # 底部保存按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_save = self._create_fortress_button(tr("settings.save_settings"), "primary")
        btn_save.clicked.connect(self._save_all_settings)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)
        
        # 加载当前设置
        self._load_all_settings()
        
        return page
    
    def _create_task_management_page(self):
        """创建任务管理页面 - 管理扫描任务队列"""
        from PyQt5.QtCore import QTimer
        from core.task_queue_manager import get_task_queue_manager, TaskStatus
        
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(scaled(15))
        
        # 顶部描述和操作按钮
        top_row = QHBoxLayout()
        
        desc_label = QLabel(tr("task.description"))
        desc_label.setStyleSheet(scaled_style(f"color: {FORTRESS_COLORS['text_secondary']}; font-size: 13px;"))
        top_row.addWidget(desc_label)

        top_row.addStretch()

        # 状态筛选
        top_row.addWidget(QLabel(tr("task.filter_status")))
        self.task_status_filter = QComboBox()
        _filter_items = [tr("filter.all")]
        for ts in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED,
                    TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            _filter_items.append(ts.display_name())
        self.task_status_filter.addItems(_filter_items)
        self.task_status_filter.setMinimumWidth(scaled(100))
        self.task_status_filter.currentTextChanged.connect(self._filter_task_list)
        top_row.addWidget(self.task_status_filter)

        # 刷新按钮
        btn_refresh = self._create_fortress_button(tr("common.refresh"), "info")
        btn_refresh.clicked.connect(self._refresh_task_list)
        top_row.addWidget(btn_refresh)

        layout.addLayout(top_row)

        # 任务列表表格
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(9)
        self.task_table.setHorizontalHeaderLabels([tr("task.col_id"), tr("task.col_name"), tr("task.col_status"), tr("task.col_progress"), tr("task.col_targets"), tr("task.col_pocs"), tr("task.col_created"), tr("task.col_started"), tr("task.col_duration")])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, 9):
            self.task_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.SingleSelection)
        self.task_table.setAlternatingRowColors(True)

        # 应用表格样式
        from core.fortress_style import get_table_stylesheet
        self.task_table.setStyleSheet(get_table_stylesheet(FORTRESS_COLORS))

        layout.addWidget(self.task_table)

        # 底部操作按钮
        btn_row = QHBoxLayout()

        btn_start = self._create_fortress_button(tr("task.start_selected"), "success")
        btn_start.clicked.connect(self._start_selected_task)
        btn_row.addWidget(btn_start)

        btn_pause = self._create_fortress_button(tr("task.pause"), "warning")
        btn_pause.clicked.connect(self._pause_selected_task)
        btn_row.addWidget(btn_pause)

        btn_resume = self._create_fortress_button(tr("task.resume"), "info")
        btn_resume.clicked.connect(self._resume_selected_task)
        btn_row.addWidget(btn_resume)

        btn_cancel = self._create_fortress_button(tr("common.cancel"), "warning")
        btn_cancel.clicked.connect(self._cancel_selected_task)
        btn_row.addWidget(btn_cancel)

        btn_row.addStretch()

        btn_delete = self._create_fortress_button(tr("task.delete_selected"), "warning")
        btn_delete.clicked.connect(self._delete_selected_task)
        btn_row.addWidget(btn_delete)
        
        btn_clear = self._create_fortress_button(tr("task.clear_completed"), "secondary")
        btn_clear.clicked.connect(self._clear_completed_tasks)
        btn_row.addWidget(btn_clear)

        layout.addLayout(btn_row)

        # 状态栏
        self.task_status_label = QLabel(tr("task.total_count", count=0))
        self.task_status_label.setStyleSheet(scaled_style(f"color: {FORTRESS_COLORS['text_secondary']}; font-size: 12px;"))
        layout.addWidget(self.task_status_label)
        
        # 设置定时器自动刷新
        self.task_refresh_timer = QTimer(self)
        self.task_refresh_timer.timeout.connect(self._refresh_task_list)
        self.task_refresh_timer.start(1000)  # 每秒刷新
        
        # 初始加载
        self._refresh_task_list()
        
        return page
    
    def _refresh_task_list(self):
        """刷新任务列表"""
        from core.task_queue_manager import get_task_queue_manager, TaskStatus
        
        # 保存当前选中的任务ID
        selected_task_id = self._get_selected_task_id() if hasattr(self, 'task_table') else None
        
        queue = get_task_queue_manager()
        tasks = queue.get_all_tasks()
        
        # 获取筛选条件
        status_filter = self.task_status_filter.currentText() if hasattr(self, 'task_status_filter') else tr("filter.all")
        
        # 状态映射（使用显示名到枚举的映射）
        status_map = {}
        for ts in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED,
                    TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            status_map[ts.display_name()] = ts
        
        # 筛选任务
        if status_filter != tr("filter.all") and status_filter in status_map:
            tasks = [t for t in tasks if t.status == status_map[status_filter]]
        
        # 更新表格
        self.task_table.setUpdatesEnabled(False)
        self.task_table.setRowCount(0)
        self.task_table.setRowCount(len(tasks))
        
        for row, task in enumerate(tasks):
            # 任务ID
            id_item = QTableWidgetItem(task.id)
            id_item.setData(Qt.UserRole, task.id)
            self.task_table.setItem(row, 0, id_item)

            # 名称
            self.task_table.setItem(row, 1, QTableWidgetItem(task.name))

            # 状态 (带颜色)
            status_item = QTableWidgetItem(task.status.display_name())
            status_colors = {
                TaskStatus.PENDING: "#f97316",     # 橙色
                TaskStatus.RUNNING: "#3b82f6",    # 蓝色
                TaskStatus.PAUSED: "#eab308",     # 黄色
                TaskStatus.COMPLETED: "#22c55e",  # 绿色
                TaskStatus.FAILED: "#ef4444",     # 红色
                TaskStatus.CANCELLED: "#6b7280",  # 灰色
            }
            from PyQt5.QtGui import QColor
            if task.status in status_colors:
                status_item.setForeground(QColor(status_colors[task.status]))
            self.task_table.setItem(row, 2, status_item)

            # 进度
            progress_text = f"{task.progress}%" if task.status == TaskStatus.RUNNING else "-"
            self.task_table.setItem(row, 3, QTableWidgetItem(progress_text))

            # Targets
            self.task_table.setItem(row, 4, QTableWidgetItem(str(len(task.targets))))

            # POC数
            self.task_table.setItem(row, 5, QTableWidgetItem(str(len(task.templates))))

            # 创建时间
            created_str = task.created_at.strftime("%m-%d %H:%M:%S") if task.created_at else "-"
            self.task_table.setItem(row, 6, QTableWidgetItem(created_str))

            # 开始时间
            started_str = task.started_at.strftime("%m-%d %H:%M:%S") if task.started_at else "-"
            self.task_table.setItem(row, 7, QTableWidgetItem(started_str))

            # 耗时
            duration_str = self._calc_task_duration(task)
            duration_item = QTableWidgetItem(duration_str)
            if task.status == TaskStatus.RUNNING:
                duration_item.setForeground(QColor("#3b82f6"))  # 运行中显示蓝色
            self.task_table.setItem(row, 8, duration_item)
        
        self.task_table.setUpdatesEnabled(True)
        
        # 恢复之前选中的任务
        if selected_task_id:
            for row in range(self.task_table.rowCount()):
                id_item = self.task_table.item(row, 0)
                if id_item and id_item.data(Qt.UserRole) == selected_task_id:
                    self.task_table.selectRow(row)
                    break
        
        # 更新状态栏
        status = queue.get_queue_status()
        self.task_status_label.setText(
            tr("task.status_summary",
               total=status['total'], pending=status['pending'],
               running=status['running'], paused=status['paused'],
               completed=status['completed'], failed=status['failed'],
               cancelled=status['cancelled'])
        )
    
    def _filter_task_list(self):
        """根据状态筛选任务列表"""
        self._refresh_task_list()

    def _calc_task_duration(self, task):
        """计算任务耗时"""
        from datetime import datetime
        from core.task_queue_manager import TaskStatus

        if not task.started_at:
            return "-"

        # 确定结束时间
        if task.completed_at:
            end_time = task.completed_at
        elif task.status in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
            end_time = datetime.now()
        else:
            end_time = datetime.now()

        # 计算时间差
        delta = end_time - task.started_at
        total_seconds = int(delta.total_seconds())

        if total_seconds < 0:
            return "-"

        # 格式化显示
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return tr("time.hms", h=hours, m=minutes, s=seconds)
        elif minutes > 0:
            return tr("time.ms", m=minutes, s=seconds)
        else:
            return tr("time.seconds", s=seconds)
    def _get_selected_task_id(self):
        """获取选中的任务ID"""
        selected = self.task_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        id_item = self.task_table.item(row, 0)
        return id_item.data(Qt.UserRole) if id_item else None
    
    def _start_selected_task(self):
        """启动选中的任务"""
        from core.task_queue_manager import get_task_queue_manager

        task_id = self._get_selected_task_id()
        if not task_id:
            QMessageBox.warning(self, tr("msg.hint"), tr("task.select_task_first"))
            return

        queue = get_task_queue_manager()

        # 设置扫描配置（从设置管理器获取）
        scan_config = self.settings.get_scan_config()
        queue.set_scan_config(scan_config)

        # 定义回调函数绑定 UI
        def bind_ui_callback(tid):
            self._switch_page(0)
            self._bind_running_task_to_ui(tid)

        if queue.start_task(task_id, pre_start_callback=bind_ui_callback):
            self.status_bar.showMessage(tr("task.task_started", task_id=task_id))
            self._refresh_task_list()
        else:
            QMessageBox.warning(self, tr("msg.failure"), tr("task.cannot_start", task_id=task_id))

    def _bind_running_task_to_ui(self, task_id):
        """将后台运行的任务绑定到主界面 UI 显示"""
        from core.task_queue_manager import get_task_queue_manager
        queue = get_task_queue_manager()
        worker = queue.get_worker(task_id)
        
        if not worker:
            return

        # 1. UI 初始化
        self.scan_results_data.clear()
        self.result_table.setRowCount(0)
        self.log_output.clear()
        self.progress_bar.setRange(0, 100)  # 设置确定模式
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.current_task_id = task_id

        # 禁用开始按钮，启用停止/暂停按钮
        self.btn_start.setEnabled(False)
        self.btn_start.setText(tr("scan.scanning"))

        # 记录开始时间
        import time
        self.scan_start_time = time.time()

        # 获取任务信息用于后续保存历史
        task = queue.get_task(task_id)
        if task:
            self.current_scan_targets = task.targets
            self.current_scan_templates = task.templates
            self.current_scan_config = {}

            # 恢复已有进度
            if task.progress > 0:
                self.progress_bar.setValue(task.progress)

            # 尝试恢复已有的结果（如果任务已经在跑了一会儿）
            if hasattr(task, 'results') and task.results:
                for res in task.results:
                    self.add_scan_result(res)

        # 2. 绑定信号
        try:
            # log_signal -> append_log
            worker.log_signal.connect(self.append_log)
            # 测试日志，验证绑定成功
            self.append_log(f"[DEBUG] UI signals bound (TaskID: {task_id})")
            
            # result_found -> add_scan_result
            worker.result_found.connect(self._on_worker_result_found)

            # task_progress -> update_progress
            worker.task_progress.connect(self._on_worker_progress)
            
            # task_completed -> scan_finished
            worker.task_completed.connect(self._on_worker_completed)
            
            # task_failed -> 日志 + 结束
            worker.task_failed.connect(self._on_worker_failed)
            
        except TypeError as e:
            QMessageBox.critical(self, tr("msg.error"), tr("task.signal_bindng_failed", error=str(e)))
            return
        
        # 3. 启用控制按钮
        self.btn_stop.setEnabled(True)
        self.btn_pause.setEnabled(True)

        # 更新状态指示
        self.status_indicator.setText(tr("status.scanning"))
        # 简单设置样式
        self.status_indicator.setStyleSheet(scaled_style(f"""
            color: #f97316;
            background-color: #fff7ed;
            border-radius: 12px;
            padding: 5px 12px;
        """))

    # --- Worker 信号处理槽函数 ---
    
    def _on_worker_progress(self, task_id, progress):
        """处理 Worker 进度信号"""
        try:
            self.update_progress(progress, 100, tr("task.in_progress"))
        except Exception as e:
            self.append_log(f"\n[UI Error] Update progress failed: {e}")

    def _on_worker_result_found(self, task_id, result):
        """处理 Worker 发现漏洞信号"""
        try:
            self.add_scan_result(result)
        except Exception as e:
            import traceback
            self.append_log(f"\n[UI Error] Add result failed: {e}\n{traceback.format_exc()}")

    def _on_worker_completed(self, task_id, result):
        """处理 Worker 完成信号"""
        try:
            self.append_log(f"[DEBUG] _on_worker_completed called for task: {task_id}")
            self.scan_finished()
            # 刷新任务列表
            self._refresh_task_list()
        except Exception as e:
            self.append_log(f"\n[UI Error] Completion handling failed: {e}")

    def _on_worker_failed(self, task_id, error):
        """处理 Worker 失败信号"""
        try:
            self.append_log(f"\n[Error] Task failed: {error}")
            self.scan_finished("failed")
            # 刷新任务列表
            self._refresh_task_list()
        except Exception as e:
            self.append_log(f"\n[UI Error] Failure handling failed: {e}")

    def add_scan_result(self, result):
        """添加扫描结果"""
        # DEBUG LOG
        # self.append_log(f"[DEBUG] add_scan_result called: {result.get('info', {}).get('name')}")
        
        # 更新数据
        self.scan_results_data.append(result)

        
        # 更新表格
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        # 1. 状态图标
        status_item = QTableWidgetItem("✅")
        status_item.setTextAlignment(Qt.AlignCenter)
        self.result_table.setItem(row, 0, status_item)
        
        # 2. 漏洞名称
        info = result.get('info', {})
        name = info.get('name', 'Unknown')
        name_item = QTableWidgetItem(name)
        # 存储完整数据以便查看详情
        name_item.setData(Qt.UserRole, result)
        self.result_table.setItem(row, 1, name_item)
        
        # 3. 严重程度
        severity = info.get('severity', 'unknown').lower()
        sev_item = QTableWidgetItem(display_severity(severity))
        
        # 设置颜色
        sev_colors = {
            'critical': ('#ef4444', '#ffffff'),
            'high': ('#f97316', '#ffffff'),
            'medium': ('#f59e0b', '#ffffff'),
            'low': ('#22c55e', '#ffffff'),
            'info': ('#3b82f6', '#ffffff'),
            'unknown': ('#9ca3af', '#ffffff'),
        }
        bg, fg = sev_colors.get(severity, ('#9ca3af', '#ffffff'))
        sev_item.setBackground(QColor(bg))
        sev_item.setForeground(QColor(fg))
        sev_item.setTextAlignment(Qt.AlignCenter)
        sev_item.setFont(QFont("Arial", scaled(9), QFont.Bold))
        self.result_table.setItem(row, 2, sev_item)
        
        # 4. 目标
        host = result.get('host', '')
        self.result_table.setItem(row, 3, QTableWidgetItem(host))
        
        # 5. 发现时间
        timestamp = result.get('timestamp', '')
        # 格式化时间
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M:%S")
            else:
                time_str = datetime.now().strftime("%H:%M:%S")
        except (ValueError, AttributeError):
            time_str = datetime.now().strftime("%H:%M:%S")
        self.result_table.setItem(row, 4, QTableWidgetItem(time_str))
        
        # 6. 操作按钮
        btn_detail = QPushButton(tr("common.detail"))
        btn_detail.setCursor(Qt.PointingHandCursor)
        # 强制指定样式
        btn_detail.setStyleSheet(scaled_style(f"""
            QPushButton {{
                background-color: {FORTRESS_COLORS['btn_info']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {FORTRESS_COLORS['btn_info_hover']};
            }}
        """))
        # 绑定点击事件，使用闭包保存 result
        btn_detail.clicked.connect(lambda checked, r=result: self._show_vuln_detail(r, json.dumps(r, indent=2, ensure_ascii=False)))

        # 创建容器居中按钮
        w_detail = QWidget()
        l_detail = QHBoxLayout(w_detail)
        l_detail.setContentsMargins(scaled(5), scaled(2), scaled(5), scaled(2))
        l_detail.addWidget(btn_detail)
        self.result_table.setCellWidget(row, 5, w_detail)
        
        # 滚动到底部
        self.result_table.scrollToBottom()
        
        # 更新实时统计
        self._update_dashboard_vuln_count_realtime()

    def scan_finished(self, status="completed"):
        """扫描完成处理"""
        # 防止重复调用
        if self.btn_start.isEnabled():
            self.append_log("[DEBUG] scan_finished skipped (already finished)")
            return

        self.append_log(f"[DEBUG] scan_finished called with status: {status}")
        self.append_log(f"[DEBUG] Current scan_results_data count: {len(self.scan_results_data)}")

        # 先将进度条设置为100%，然后再隐藏
        self.progress_bar.setValue(100)

        # 恢复 UI 状态
        self.btn_start.setEnabled(True)
        self.btn_start.setText(tr("scan.start_scan"))  # 恢复按钮文本
        self.btn_stop.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText(tr("task.pause"))  # 重置按钮文本
        self.progress_bar.hide()

        result_count = len(self.scan_results_data)
        self.lbl_progress.setText(tr("scan.completed_found", count=result_count))
        self.status_indicator.setText(tr("status.status_label", status=display_scan_status(status)))
        self.status_indicator.setStyleSheet(scaled_style(f"""
            color: {FORTRESS_COLORS['status_low']};
            font-size: 13px;
            padding: 5px 12px;
            background-color: #f0fdf4;
            border-radius: 12px;
        """))

        # 计算耗时
        import time
        duration = 0
        if hasattr(self, 'scan_start_time'):
            duration = time.time() - self.scan_start_time
        duration_str = tr("time.ms", m=int(duration // 60), s=int(duration % 60)) if duration >= 60 else tr("time.seconds", s=int(duration))

        # 获取当前任务信息
        from core.task_queue_manager import get_task_queue_manager, TaskStatus
        queue = get_task_queue_manager()
        targets = getattr(self, 'current_scan_targets', [])
        pocs = getattr(self, 'current_scan_templates', [])

        if hasattr(self, 'current_task_id') and self.current_task_id:
            task = queue.get_task(self.current_task_id)
            if task:
                targets = task.targets or targets
                pocs = task.templates or pocs
                target_task_status = {
                    "completed": TaskStatus.COMPLETED,
                    "failed": TaskStatus.FAILED,
                    "stopped": TaskStatus.CANCELLED,
                    "cancelled": TaskStatus.CANCELLED,
                }.get(status, TaskStatus.COMPLETED)
                if task.status != target_task_status:
                    queue.update_task_status(self.current_task_id, target_task_status)

        # 将结果写入数据库
        from core.scan_history import get_scan_history
        history = get_scan_history()

        # 添加扫描记录
        scan_id = history.add_scan_record(
            target_count=len(targets),
            poc_count=len(pocs),
            vuln_count=result_count,
            duration=duration,
            targets=targets,
            pocs=pocs,
            config=getattr(self, 'current_scan_config', {}),
            status=status
        )

        # 添加漏洞结果
        for result in self.scan_results_data:
            history.add_vuln_result(scan_id, result)

        # 刷新仪表盘
        self.refresh_dashboard()

        # 提示用户
        if result_count > 0:
            QMessageBox.information(self, tr("scan.scan_complete"), message_text(tr("scan.complete_with_vulns", count=result_count, duration=duration_str)))
        else:
            QMessageBox.information(self, tr("scan.scan_complete"), message_text(tr("scan.complete_no_vulns", duration=duration_str)))

    def stop_scan(self):
        """停止当前扫描"""
        self.append_log("[DEBUG] stop_scan called")
        if hasattr(self, 'current_task_id') and self.current_task_id:

            from core.task_queue_manager import get_task_queue_manager
            queue = get_task_queue_manager()
            queue.cancel_task(self.current_task_id)
            
            self.append_log("[INFO] Stopping scan...")
            # self.btn_stop.setEnabled(False) # 不要在这里禁用，等待 scan_finished 处理，确保 _on_task_status_changed 能通过检查
            # self.btn_pause.setEnabled(False)
            
            # QTimer removed to allow signal handler to manage completion



    def pause_scan(self):
        """暂停/恢复当前扫描"""
        if hasattr(self, 'current_task_id') and self.current_task_id:
            from core.task_queue_manager import get_task_queue_manager
            queue = get_task_queue_manager()
            
            if self.btn_pause.text() == tr("task.pause"):
                if queue.pause_task(self.current_task_id):
                    self.btn_pause.setText(tr("task.continue"))
                    self.status_bar.showMessage(tr("scan.paused"))
                    self.append_log("[INFO] Scan paused")
            else:
                if queue.resume_task(self.current_task_id):
                    self.btn_pause.setText(tr("task.pause"))
                    self.status_bar.showMessage(tr("scan.resumed"))
                    self.append_log("[INFO] Scan resumed")

    def start_scan(self):
        """开始新的扫描"""
        # 如果有正在运行的任务，提示
        if self.btn_stop.isEnabled():
            QMessageBox.warning(self, tr("msg.warning"), tr("scan.already_running"))
            return
            
        # 获取待扫描目标
        targets = parse_targets_text(self.txt_targets.toPlainText() if hasattr(self, "txt_targets") else "")
        if not targets:
            QMessageBox.warning(self, tr("msg.hint"), tr("scan.add_targets_first"))
            self._switch_page(0) # 扫描结果页
            return
            
        # 获取待扫描 POC
        pocs = list(self.pending_scan_pocs)
        if not pocs:
            QMessageBox.warning(self, tr("msg.hint"), tr("scan.select_pocs_first"))
            self._switch_page(1) # POC 管理页
            return
            
        # 记录开始时间
        self.scan_start_time = datetime.now()
        
        # 添加并启动任务
        # self._add_task_to_queue(targets, pocs, priority=None)  <-- Removed redundant call

        
        # 自动启动刚添加的任务（假设它是唯一的或排在最前）
        # 这里需要获取刚添加的任务ID，_add_task_to_queue 会弹窗提示ID，但我们想自动开始
        # 优化流程：直接调用 task_queue.add_task 并设置 auto_start=True

        # 由于 _add_task_to_queue 已经封装了 add_task 且不可控 auto_start，
        # 我们这里查找 pending 任务并手动启动
        from core.task_queue_manager import get_task_queue_manager
        queue = get_task_queue_manager()

        # 设置扫描配置（从设置管理器获取）
        scan_config = self.settings.get_scan_config()
        queue.set_scan_config(scan_config)

        # 这里简化处理：直接启动队列中第一个 pending 的任务
        # 更好的做法是 _add_task_to_queue 返回 task_id
        # 我们可以稍微修改逻辑，或者直接依赖 _add_task_to_queue 的逻辑，用户需要在任务列表点击开始
        # 但这里是 "开始扫描" 按钮，应该直接开始

        # 重新实现 _add_task_to_queue 的部分逻辑以获取 ID 并启动
        from core.task_queue_manager import TaskPriority
        task_name = tr("task.scan_task_name", targets=len(targets), pocs=len(pocs))
        task_id = queue.add_task(
            name=task_name,
            targets=targets,
            templates=pocs,
            priority=TaskPriority.NORMAL,
            auto_start=True  # 自动启动
        )
        
        self.current_task_id = task_id
        
        # 绑定 UI
        self._batch_bind_ui = lambda tid=task_id: self._bind_running_task_to_ui(tid)
        # queue.start_task(task_id, pre_start_callback=self._batch_bind_ui) # add_task(auto_start=True) 已经启动了
        # 但我们需要手动绑定 UI，因为 auto_start 内部启动时没有 callback
        # 这其实是 TaskQueueManager 的一个小设计问题，auto_start 没法传 callback
        # 所以我们这里手动绑定
        self._bind_running_task_to_ui(task_id)
        
        self._switch_page(0)

    def _on_task_status_changed(self, task_id, status):
        """处理任务状态变更"""
        # self.append_log(f"[DEBUG] _on_task_status_changed: {task_id} -> {status}")
        if hasattr(self, 'current_task_id') and task_id == self.current_task_id:

            from core.task_queue_manager import TaskStatus
            if status == TaskStatus.COMPLETED.value:
                self.scan_finished(status="completed")
            elif status == TaskStatus.FAILED.value:
                self.scan_finished(status="failed")
            elif status == TaskStatus.CANCELLED.value:
                # 已经由 stop_scan 的 singleShot 处理了，这里可能无需重复
                # 但为了保险，如果不是 stop_scan 触发的取消（比如任务管理页取消）
                # 我们也应该处理
                # if self.btn_stop.isEnabled(): # 移除此检查，确保总是尝试处理
                self.scan_finished(status="stopped")

    def _check_update_on_startup(self):
        """启动时检查更新"""
        # 检查是否启用自动更新检查
        auto_check = self.settings.get_auto_check_update()
        if not auto_check:
            return

        from core.updater import UpdateCheckThread, get_current_version

        self._startup_update_thread = UpdateCheckThread(timeout=5)
        self._startup_update_thread.check_finished.connect(self._on_startup_update_check)
        self._startup_update_thread.start()

    def _on_startup_update_check(self, has_update, latest_version, download_url, release_notes):
        """启动时更新检查完成"""
        if has_update:
            from core.updater import get_current_version
            reply = QMessageBox.question(
                self,
                tr("update.new_version_found"),
                tr("update.new_version_prompt", latest=latest_version, current=get_current_version(), notes=release_notes[:200] + ('...' if len(release_notes) > 200 else '')),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                # 切换到主界面的设置页面，并选中更新设置 Tab
                self._switch_page(5)  # 设置页面索引
                # 找到设置页面中的 Tab 控件并切换到更新设置
                if hasattr(self, 'settings_page'):
                    tabs = self.settings_page.findChild(QTabWidget)
                    if tabs:
                        tabs.setCurrentIndex(5)  # 更新设置 Tab 索引

    def _pause_selected_task(self):
        """暂停选中的任务"""
        from core.task_queue_manager import get_task_queue_manager, TaskStatus

        
        task_id = self._get_selected_task_id()
        if not task_id:
            QMessageBox.warning(self, tr("msg.hint"), tr("task.select_task_first"))
            return
        
        queue = get_task_queue_manager()
        task = queue.get_task(task_id)
        
        if not task:
            QMessageBox.warning(self, tr("msg.failure"), tr("task.not_found", task_id=task_id))
            return

        # 如果是当前正在运行的任务，统一走扫描页的暂停逻辑
        if hasattr(self, 'current_task_id') and task_id == self.current_task_id:
            if task.status == TaskStatus.PAUSED:
                QMessageBox.information(self, tr("msg.hint"), tr("task.already_paused", task_id=task_id))
            elif self.pause_scan():
                QMessageBox.information(self, tr("msg.success"), tr("task.paused", task_id=task_id))
            else:
                QMessageBox.warning(self, tr("msg.failure"), tr("task.cannot_pause", task_id=task_id))
            self._refresh_task_list()
            return
        
        # 尝试通过队列管理器暂停（队列内部任务）
        if queue.pause_task(task_id):
            QMessageBox.information(self, tr("msg.success"), tr("task.paused", task_id=task_id))
            self._refresh_task_list()
        else:
            QMessageBox.warning(self, tr("msg.failure"), tr("task.cannot_pause", task_id=task_id))
    
    def _resume_selected_task(self):
        """恢复选中的任务"""
        from core.task_queue_manager import get_task_queue_manager, TaskStatus
        
        task_id = self._get_selected_task_id()
        if not task_id:
            QMessageBox.warning(self, tr("msg.hint"), tr("task.select_task_first"))
            return
        
        queue = get_task_queue_manager()
        task = queue.get_task(task_id)
        
        if not task:
            QMessageBox.warning(self, tr("msg.failure"), tr("task.not_found", task_id=task_id))
            return

        # 如果是当前任务，统一走扫描页的恢复逻辑
        if hasattr(self, 'current_task_id') and task_id == self.current_task_id:
            if task.status == TaskStatus.RUNNING:
                QMessageBox.information(self, tr("msg.hint"), tr("task.already_running", task_id=task_id))
            elif self.pause_scan():
                QMessageBox.information(self, tr("msg.success"), tr("task.resumed", task_id=task_id))
            else:
                QMessageBox.warning(self, tr("msg.failure"), tr("task.cannot_resume", task_id=task_id))
            self._refresh_task_list()
            return
        
        # 尝试通过队列管理器恢复（队列内部任务）
        if queue.resume_task(task_id):
            QMessageBox.information(self, tr("msg.success"), tr("task.resumed", task_id=task_id))
            self._refresh_task_list()
        else:
            QMessageBox.warning(self, tr("msg.failure"), tr("task.cannot_resume", task_id=task_id))
    
    def _cancel_selected_task(self):
        """取消选中的任务"""
        from core.task_queue_manager import get_task_queue_manager, TaskStatus
        
        task_id = self._get_selected_task_id()
        if not task_id:
            QMessageBox.warning(self, tr("msg.hint"), tr("task.select_task_first"))
            return
        
        reply = QMessageBox.question(
            self, tr("msg.confirm"), tr("task.confirm_cancel", task_id=task_id),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            queue = get_task_queue_manager()
            
            # 如果是当前正在运行的外部扫描任务，使用主窗口的停止方法
            if hasattr(self, 'current_task_id') and task_id == self.current_task_id:
                if hasattr(self, 'scan_thread') and self.scan_thread and self.scan_thread.isRunning():
                    self.stop_scan()  # 调用主窗口的停止方法（会更新任务状态为CANCELLED）
                    QMessageBox.information(self, tr("msg.success"), tr("task.cancelled", task_id=task_id))
                    self._refresh_task_list()
                    return
            
            # 尝试通过队列管理器取消（队列内部任务或等待中的任务）
            if queue.cancel_task(task_id):
                QMessageBox.information(self, tr("msg.success"), tr("task.cancelled", task_id=task_id))
                self._refresh_task_list()
            else:
                QMessageBox.warning(self, tr("msg.failure"), tr("task.cannot_cancel", task_id=task_id))
    
    def _delete_selected_task(self):
        """删除选中的任务"""
        from core.task_queue_manager import get_task_queue_manager
        
        task_id = self._get_selected_task_id()
        if not task_id:
            QMessageBox.warning(self, tr("msg.hint"), tr("task.select_task_first"))
            return
        
        reply = QMessageBox.question(
            self, tr("msg.confirm"), tr("task.confirm_delete", task_id=task_id),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            queue = get_task_queue_manager()
            if queue.remove_task(task_id):
                QMessageBox.information(self, tr("msg.success"), tr("task.deleted", task_id=task_id))
                self._refresh_task_list()
            else:
                QMessageBox.warning(self, tr("msg.failure"), tr("task.cannot_delete", task_id=task_id))
    
    def _clear_completed_tasks(self):
        """清理所有已完成的任务"""
        from core.task_queue_manager import get_task_queue_manager
        
        reply = QMessageBox.question(
            self, tr("msg.confirm"), tr("task.confirm_clear_completed"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            queue = get_task_queue_manager()
            queue.clear_completed()
            self._refresh_task_list()
            QMessageBox.information(self, tr("msg.success"), tr("task.completed_cleared"))
    
    def _create_fortress_button(self, text, btn_type='primary'):
        """创建 FORTRESS 风格按钮（支持 DPI 缩放）"""
        btn = QPushButton(text)
        btn.setMinimumHeight(scaled(38))
        btn.setCursor(Qt.PointingHandCursor)

        if btn_type == 'primary':
            btn.setStyleSheet(scaled_style(f"""
                QPushButton {{
                    background-color: {FORTRESS_COLORS['btn_primary']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 20px;
                }}
                QPushButton:hover {{
                    background-color: {FORTRESS_COLORS['btn_primary_hover']};
                }}
            """))
        elif btn_type == 'warning':
            btn.setStyleSheet(scaled_style(f"""
                QPushButton {{
                    background-color: {FORTRESS_COLORS['btn_warning']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 20px;
                }}
                QPushButton:hover {{
                    background-color: {FORTRESS_COLORS['btn_warning_hover']};
                }}
            """))
        elif btn_type == 'info':
            btn.setStyleSheet(scaled_style(f"""
                QPushButton {{
                    background-color: {FORTRESS_COLORS['btn_info']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 20px;
                }}
                QPushButton:hover {{
                    background-color: {FORTRESS_COLORS['btn_info_hover']};
                }}
            """))
        elif btn_type == 'success':
            btn.setStyleSheet(scaled_style(f"""
                QPushButton {{
                    background-color: {FORTRESS_COLORS['btn_success']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 20px;
                }}
                QPushButton:hover {{
                    background-color: {FORTRESS_COLORS['btn_success_hover']};
                }}
            """))
        elif btn_type == 'purple':
            btn.setStyleSheet(scaled_style(f"""
                QPushButton {{
                    background-color: {FORTRESS_COLORS['btn_purple']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 20px;
                }}
                QPushButton:hover {{
                    background-color: {FORTRESS_COLORS['btn_purple_hover']};
                }}
            """))
        elif btn_type == 'secondary':
            # 次要按钮：边框样式，与界面风格一致
            text_color = FORTRESS_COLORS.get('text_primary', '#1f2937')
            border_color = FORTRESS_COLORS.get('nav_border', '#e5e7eb')
            hover_bg = FORTRESS_COLORS.get('nav_hover', '#f3f4f6')
            btn.setStyleSheet(scaled_style(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_color};
                    border: 1px solid {border_color};
                    border-radius: 6px;
                    font-size: 13px;
                    padding: 8px 20px;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                }}
            """))
        
        return btn
    
    def _create_scan_stat_card(self, title, value, color):
        """创建扫描统计卡片（支持 DPI 缩放）"""
        card = QWidget()
        card.setFixedSize(scaled(90), scaled(60))
        card.setStyleSheet(scaled_style(f"""
            QWidget {{
                background-color: {FORTRESS_COLORS.get('table_header', '#f1f5f9')};
                border-radius: 8px;
                border-left: 3px solid {color};
            }}
        """))

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(scaled(10), scaled(5), scaled(10), scaled(5))
        card_layout.setSpacing(scaled(2))

        # 数值
        value_label = QLabel(value)
        value_label.setStyleSheet(scaled_style(f"""
            font-size: 18px;
            font-weight: bold;
            color: {color};
        """))
        value_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(value_label)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(scaled_style(f"""
            font-size: 11px;
            color: {FORTRESS_COLORS.get('text_secondary', '#6b7280')};
        """))
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)

        # 存储引用以便更新
        card.value_label = value_label

        return card
    
    def _update_scan_stats(self, targets=0, pocs=0, vulns=None):
        """更新扫描统计面板"""
        if hasattr(self, 'scan_stat_targets'):
            self.scan_stat_targets.value_label.setText(str(targets))
        if hasattr(self, 'scan_stat_pocs'):
            self.scan_stat_pocs.value_label.setText(str(pocs))
        
        if vulns is not None:
            # 统计各严重程度的Vulns量
            severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
            for v in vulns:
                sev = v.get('info', {}).get('severity', 'unknown').lower()
                if sev in severity_counts:
                    severity_counts[sev] += 1
            
            if hasattr(self, 'scan_stat_vulns'):
                self.scan_stat_vulns.value_label.setText(str(len(vulns)))
            if hasattr(self, 'scan_stat_critical'):
                self.scan_stat_critical.value_label.setText(str(severity_counts['critical']))
            if hasattr(self, 'scan_stat_high'):               self.scan_stat_high.value_label.setText(str(severity_counts['high']))
            if hasattr(self, 'scan_stat_medium'):
                self.scan_stat_medium.value_label.setText(str(severity_counts['medium']))
            if hasattr(self, 'scan_stat_low'):
                self.scan_stat_low.value_label.setText(str(severity_counts['low']))
    
    def _update_dashboard_vuln_count_realtime(self):
        """实时更新仪表盘的Vulns量卡片（扫描过程中）"""
        if hasattr(self, 'card_vulns') and hasattr(self, 'scan_results_data'):
            # 获取当前扫描发现的Vulns量
            current_vuln_count = len(self.scan_results_data)
            
            # 获取历史漏洞总数
            from core.scan_history import get_scan_history
            stats = get_scan_history().get_statistics()
            historical_vulns = stats.get('total_vulns', 0)
            
            # 显示：历史总数 + 当前扫描发现数
            total_display = historical_vulns + current_vuln_count
            self._update_card_value(self.card_vulns, str(total_display))
            
            # 同时更新严重程度分布条形图
            if hasattr(self, 'severity_bars') and self.scan_results_data:
                severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
                for v in self.scan_results_data:
                    sev = v.get('info', {}).get('severity', 'unknown').lower()
                    if sev in severity_counts:
                        severity_counts[sev] += 1
                
                # 获取历史严重程度分布
                hist_dist = stats.get('severity_distribution', {})
                
                for sev, bar in self.severity_bars.items():
                    hist_count = hist_dist.get(sev, 0)
                    current_count = severity_counts.get(sev, 0)
                    total = hist_count + current_count
                    bar.setRange(0, max(total, 10))
                    bar.setValue(total)
                    bar.setFormat(f"{total}")
    
    def show_new_scan_dialog(self):
        """显示新建扫描配置弹窗"""
        from dialogs.new_scan_dialog import NewScanDialog
        
        # 使用队列中的 POC 作为初始选中项
        initial_pocs = list(self.pending_scan_pocs)
        dialog = NewScanDialog(self, self.poc_library, initial_pocs=initial_pocs, colors=FORTRESS_COLORS)
        
        if dialog.exec_() == QDialog.Accepted:
            # 获取配置
            targets = dedupe_targets(dialog.get_targets())
            pocs = dialog.get_selected_pocs()
            action_mode = dialog.get_action_mode()
            
            print(f"[DEBUG] action_mode = '{action_mode}'")  # 调试输出
            
            if targets and pocs:
                self.txt_targets.setPlainText("\n".join(targets))
                self._set_selected_pocs(pocs)
                
                if action_mode == 'queue':
                    # 加入任务队列（不自动启动）
                    self._add_task_to_queue(targets, pocs)
                    self._switch_page(6)  # 切换到任务管理页面
                elif action_mode == 'scan':
                    # 立即扫描 (action_mode == 'scan')
                    self._switch_page(0)
                    self.start_scan(targets=targets, templates=pocs)
                
                # 清空待选队列
                self.pending_scan_pocs.clear()
    
    def _add_task_to_queue(self, targets, pocs, priority=None):
        """添加任务到扫描队列"""
        from core.task_queue_manager import get_task_queue_manager, TaskPriority

        targets = dedupe_targets(targets)
        if not targets:
            QMessageBox.warning(self, tr("msg.hint"), tr("scan.please_input_targets"))
            return

        # 调试日志 - 写入文件
        try:
            with open("debug_ui.log", "a", encoding="utf-8") as f:
                from datetime import datetime
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] _add_task_to_queue: targets_type={type(targets)}, targets_count={len(targets)}, pocs_count={len(pocs)}\n")
                if targets:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] First target: {targets[0]}, type: {type(targets[0])}\n")
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] All targets: {targets[:5]}...\n")  # 只打印前5个
                if pocs:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] First POC path: {pocs[0]}\n")
        except:
            pass

        queue = get_task_queue_manager()
        queue.set_scan_config(self.settings.get_scan_config())
        task_name = tr("task.scan_task_name", targets=len(targets), pocs=len(pocs))

        task_id = queue.add_task(
            name=task_name,
            targets=targets,
            templates=pocs,
            priority=priority or TaskPriority.NORMAL,
            auto_start=False  # 明确禁止自动启动
        )

        QMessageBox.information(
            self,
            tr("task.added_to_queue"),
            tr("task.added_to_queue_detail", task_id=task_id, targets=len(targets), pocs=len(pocs))
        )
    
    def _set_selected_pocs(self, poc_paths):
        """设置选中的 POC"""
        # 先取消所有选择
        for row in range(self.list_scan_pocs.rowCount()):
            item = self.list_scan_pocs.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        
        # 选中指定的 POC
        for row in range(self.list_scan_pocs.rowCount()):
            path_item = self.list_scan_pocs.item(row, 1)  # ID 列
            if path_item:
                poc_id = path_item.text()
                for poc_path in poc_paths:
                    if poc_id in poc_path or poc_path.endswith(poc_id + '.yaml'):
                        check_item = self.list_scan_pocs.item(row, 0)
                        if check_item:
                            check_item.setCheckState(Qt.Checked)
                        break

    # ================= FOFA 内嵌页面操作 =================
    
    def _fofa_refresh_history(self):
        """刷新 FOFA 历史记录列表"""
        if not hasattr(self, 'fofa_history_list'):
            return
        self.fofa_history_list.clear()
        histories = self.fofa_history_manager.get_fofa_history(limit=30)
        
        for h in histories:
            query = h.get('query', '')
            count = h.get('result_count', 0)
            time_str = h.get('search_time', '')[:16]
            
            item = QListWidgetItem(f"[{count}] {query[:30]}...")
            item.setToolTip(tr("fofa.history_tooltip", time=time_str, count=count, query=query))
            item.setData(Qt.UserRole, h)
            self.fofa_history_list.addItem(item)
    
    def _fofa_load_history_item(self, item):
        """双击加载 FOFA 历史记录"""
        history = item.data(Qt.UserRole)
        if history:
            self.fofa_query_input.setText(history.get('query', ''))
            history_id = history.get('id')
            if history_id:
                results = self.fofa_history_manager.get_fofa_results(history_id)
                if results:
                    self._fofa_display_results(results)
                    self.fofa_status_label.setText(tr("fofa.history_loaded", count=len(results)))
    
    def _fofa_load_selected_history(self):
        """加载选中的历史记录"""
        item = self.fofa_history_list.currentItem()
        if item:
            self._fofa_load_history_item(item)
        else:
            QMessageBox.information(self, tr("msg.hint"), tr("fofa.select_history_first"))
    
    def _fofa_clear_history(self):
        """清空 FOFA 历史记录"""
        reply = QMessageBox.question(
            self, tr("msg.confirm"), tr("fofa.confirm_clear_history"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.fofa_history_manager.clear_fofa_history()
            self._fofa_refresh_history()
    
    def _fofa_do_search(self):
        """执行 FOFA 搜索"""
        from core.fofa_client import FofaSearchThread
        
        query = self.fofa_query_input.text().strip()
        if not query:
            QMessageBox.warning(self, tr("msg.hint"), tr("fofa.enter_query"))
            return
        
        fofa_config = self.settings.get_fofa_config()
        if not fofa_config.get("api_key"):
            QMessageBox.warning(self, tr("msg.hint"), tr("fofa.configure_api_first"))
            self._switch_page(5)  # 切换到设置页
            return
        
        try:
            size = int(self.fofa_size_combo.currentText())
        except ValueError:
            size = 100
        
        self.fofa_btn_search.setEnabled(False)
        self.fofa_btn_search.setText(tr("fofa.searching"))
        self.fofa_progress.show()
        self.fofa_status_label.setText(tr("fofa.searching_with_size", size=size))
        
        self.fofa_search_thread = FofaSearchThread(
            fofa_config.get("api_url", ""),
            fofa_config.get("email", ""),
            fofa_config.get("api_key", ""),
            query, size
        )
        self.fofa_search_thread.result_signal.connect(self._fofa_on_search_result)
        self.fofa_search_thread.error_signal.connect(self._fofa_on_search_error)
        self.fofa_search_thread.start()
    
    def _fofa_on_search_result(self, results):
        """FOFA 搜索完成"""
        self.fofa_btn_search.setEnabled(True)
        self.fofa_btn_search.setText(tr("common.search"))
        self.fofa_progress.hide()

        query = self.fofa_query_input.text().strip()
        self.fofa_history_manager.add_fofa_history(query, len(results), results)
        self._fofa_refresh_history()

        self.fofa_current_results = results
        self._fofa_display_results(results)

        self.fofa_status_label.setText(tr("fofa.search_complete", count=len(results)))
        self.fofa_count_label.setText(tr("fofa.result_count", count=len(results)))
    
    def _fofa_on_search_error(self, error):
        """FOFA 搜索出错"""
        self.fofa_btn_search.setEnabled(True)
        self.fofa_btn_search.setText(tr("common.search"))
        self.fofa_progress.hide()
        self.fofa_status_label.setText(tr("fofa.search_failed", error=error))
        QMessageBox.critical(self, tr("msg.error"), error)
    
    def _fofa_display_results(self, results):
        """显示 FOFA 搜索结果"""
        self.fofa_result_table.setUpdatesEnabled(False)
        self.fofa_result_table.setRowCount(0)
        self.fofa_result_table.setRowCount(len(results))
        
        for row, item in enumerate(results):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked)
            
            host = item.get("host", "")
            chk_item.setData(Qt.UserRole, host)
            
            self.fofa_result_table.setItem(row, 0, chk_item)
            self.fofa_result_table.setItem(row, 1, QTableWidgetItem(host))
            self.fofa_result_table.setItem(row, 2, QTableWidgetItem(item.get("ip", "")))
            self.fofa_result_table.setItem(row, 3, QTableWidgetItem(str(item.get("port", ""))))
            self.fofa_result_table.setItem(row, 4, QTableWidgetItem(item.get("title", "")))
        
        self.fofa_result_table.setUpdatesEnabled(True)
        self.fofa_count_label.setText(tr("fofa.result_count", count=len(results)))
    
    def _fofa_select_all(self):
        """FOFA 全选"""
        for i in range(self.fofa_result_table.rowCount()):
            item = self.fofa_result_table.item(i, 0)
            if item:
                item.setCheckState(Qt.Checked)
    
    def _fofa_deselect_all(self):
        """FOFA 取消全选"""
        for i in range(self.fofa_result_table.rowCount()):
            item = self.fofa_result_table.item(i, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
    
    def _fofa_import_selected(self):
        """导入 FOFA 选中目标到扫描"""
        targets = []
        for i in range(self.fofa_result_table.rowCount()):
            item = self.fofa_result_table.item(i, 0)
            if item and item.checkState() == Qt.Checked:
                target = item.data(Qt.UserRole)
                if target:
                    targets.append(target)
        targets = dedupe_targets(targets)
        
        if not targets:
            QMessageBox.warning(self, tr("msg.hint"), tr("fofa.select_at_least_one"))
            return
        
        # 打开新建扫描弹窗并预填充目标
        from dialogs.new_scan_dialog import NewScanDialog
        
        # 使用队列中的 POC 作为初始选中项
        initial_pocs = list(self.pending_scan_pocs)
        dialog = NewScanDialog(self, self.poc_library, initial_pocs=initial_pocs, colors=FORTRESS_COLORS)
        dialog.txt_targets.setPlainText("\n".join(targets))
        
        if dialog.exec_() == QDialog.Accepted:
            # 获取配置并开始扫描
            # 获取配置
            final_targets = dedupe_targets(dialog.get_targets())
            pocs = dialog.get_selected_pocs()
            action_mode = dialog.get_action_mode()
            
            if final_targets and pocs:
                self.txt_targets.setPlainText("\n".join(final_targets))
                self._set_selected_pocs(pocs)
                
                if action_mode == 'queue':
                    # 加入任务队列（不自动启动）
                    self._add_task_to_queue(final_targets, pocs)
                    self._switch_page(6)  # 切换到任务管理页面
                elif action_mode == 'scan':
                    # 立即扫描
                    self._switch_page(0)  # 切换到扫描结果页
                    # 直接传递参数，避免 UI 同步失败导致无法扫描
                    self.start_scan(targets=final_targets, templates=pocs)
                
                # 开始扫描/加入队列后，清空待选队列
                self.pending_scan_pocs.clear()
    
    # ================= AI 内嵌页面操作 =================
    
    def _load_ai_presets_to_combo(self):
        """加载 AI 预设到下拉框"""
        if not hasattr(self, 'ai_preset_combo'):
            return
        self.ai_preset_combo.clear()
        presets = self.settings.get_ai_presets()
        for preset in presets:
            self.ai_preset_combo.addItem(preset.get("name", tr("settings.unnamed")), preset)
    
    def _load_ai_presets_to_settings_combo(self):
        """加载 AI 预设到设置页下拉框"""
        if not hasattr(self, 'settings_ai_preset'):
            return
        self.settings_ai_preset.blockSignals(True)  # 阻止信号防止触发changed事件
        self.settings_ai_preset.clear()
        presets = self.settings.get_ai_presets()
        for preset in presets:
            self.settings_ai_preset.addItem(preset.get("name", tr("settings.unnamed")), preset)
        self.settings_ai_preset.blockSignals(False)
    
    def _on_ai_preset_changed(self, index):
        """当AI预设下拉框选择改变时，更新表单"""
        if index < 0 or not hasattr(self, 'settings_ai_url'):
            return

        presets = self.settings.get_ai_presets()
        if index < len(presets):
            preset = presets[index]
            self.settings_ai_url.setText(preset.get("api_url", ""))
            self.settings_ai_key.setText(preset.get("api_key", ""))
            self.settings_ai_model.setCurrentText(preset.get("model", ""))
    
    def _add_ai_preset(self):
        """添加新的AI预设"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout
        from core.fortress_style import apply_fortress_style
        
        # 自定义弹窗以适配主题
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("settings.add_preset"))
        dialog.resize(scaled(400), scaled(180))
        apply_fortress_style(dialog, FORTRESS_COLORS)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(scaled(15))
        layout.setContentsMargins(scaled(20), scaled(20), scaled(20), scaled(20))

        # 提示标签
        label = QLabel(tr("settings.enter_preset_name"))
        label.setStyleSheet(scaled_style(f"font-size: 14px; font-weight: bold; color: {FORTRESS_COLORS.get('text_primary', '#333')};"))
        layout.addWidget(label)

        # 输入框
        name_input = QLineEdit()
        name_input.setPlaceholderText(tr("settings.preset_name_placeholder"))

        # 根据深浅色模式决定输入框背景
        is_dark = FORTRESS_COLORS.get('is_dark', False)
        if not is_dark and 'content_bg' in FORTRESS_COLORS:
             is_dark = FORTRESS_COLORS.get('content_bg', '').lower() in ['#1e293b', '#1a2332', '#111827']

        input_bg = FORTRESS_COLORS.get('table_header', '#334155') if is_dark else 'white'

        name_input.setStyleSheet(scaled_style(f"""
            QLineEdit {{
                border: 1px solid {FORTRESS_COLORS.get('nav_border', '#e5e7eb')};
                border-radius: 6px;
                padding: 10px;
                background-color: {input_bg};
                color: {FORTRESS_COLORS.get('text_primary', '#333')};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {FORTRESS_COLORS.get('btn_primary', '#2563eb')};
            }}
        """))
        layout.addWidget(name_input)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = self._create_fortress_button(tr("common.cancel"), "warning")
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = self._create_fortress_button(tr("common.confirm"), "primary")
        btn_ok.clicked.connect(dialog.accept)
        btn_layout.addWidget(btn_ok)
        
        layout.addLayout(btn_layout)
        
        # 显示弹窗
        if dialog.exec_() == QDialog.Accepted:
            name = name_input.text().strip()
            if name:
                # 获取当前预设列表
                presets = self.settings.get_ai_presets()
                
                # 检查是否重名
                for preset in presets:
                    if preset.get("name") == name:
                        QMessageBox.warning(self, tr("msg.hint"), tr("settings.preset_exists", name=name))
                        return
                
                # 创建新预设
                new_preset = {
                    "name": name,
                    "api_url": "",
                    "model": "",
                    "api_key": ""
                }
                presets.append(new_preset)
                
                # 保存并刷新
                self.settings.save_ai_presets(presets)
                self._load_ai_presets_to_settings_combo()
                
                # 选中新添加的预设
                self.settings_ai_preset.setCurrentIndex(len(presets) - 1)
                
                # 同时刷新AI页的预设下拉框
                self._load_ai_presets_to_combo()
                
                QMessageBox.information(self, tr("msg.success"), tr("settings.preset_added", name=name))
    
    def _delete_ai_preset(self):
        """删除当前选中的AI预设"""
        if not hasattr(self, 'settings_ai_preset'):
            return
        
        current_index = self.settings_ai_preset.currentIndex()
        if current_index < 0:
            QMessageBox.warning(self, tr("msg.hint"), tr("settings.select_preset_to_delete"))
            return
        
        presets = self.settings.get_ai_presets()
        if len(presets) <= 1:
            QMessageBox.warning(self, tr("msg.hint"), tr("settings.keep_at_least_one"))
            return
        
        preset_name = presets[current_index].get("name", tr("settings.unnamed"))
        reply = QMessageBox.question(
            self, tr("msg.confirm"),
            tr("settings.confirm_delete_preset", name=preset_name),
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del presets[current_index]
            self.settings.save_ai_presets(presets)
            
            # 刷新下拉框
            self._load_ai_presets_to_settings_combo()
            
            # 选中第一个预设
            if self.settings_ai_preset.count() > 0:
                self.settings_ai_preset.setCurrentIndex(0)
            
            # 同时刷新AI页的预设下拉框
            self._load_ai_presets_to_combo()
            
            QMessageBox.information(self, tr("msg.success"), tr("settings.preset_deleted", name=preset_name))

    def _rename_ai_preset(self):
        """重命名当前选中的AI预设"""
        if not hasattr(self, 'settings_ai_preset'):
            return

        current_index = self.settings_ai_preset.currentIndex()
        if current_index < 0:
            QMessageBox.warning(self, tr("msg.hint"), tr("settings.select_preset_to_rename"))
            return

        presets = self.settings.get_ai_presets()
        old_name = presets[current_index].get("name", tr("settings.unnamed"))

        from PyQt5.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, tr("settings.rename_preset"), tr("settings.enter_new_preset_name"), text=old_name
        )

        if ok and new_name.strip():
            new_name = new_name.strip()
            # 检查名称是否重复
            for i, p in enumerate(presets):
                if i != current_index and p.get("name") == new_name:
                    QMessageBox.warning(self, tr("msg.hint"), tr("settings.preset_exists", name=new_name))
                    return

            presets[current_index]["name"] = new_name
            self.settings.save_ai_presets(presets)

            # 刷新下拉框
            self._load_ai_presets_to_settings_combo()
            self.settings_ai_preset.setCurrentIndex(current_index)

            # 同时刷新AI页的预设下拉框
            self._load_ai_presets_to_combo()

            QMessageBox.information(self, tr("msg.success"), tr("settings.preset_renamed", name=new_name))

    def _toggle_api_key_visibility(self):
        """切换API Key的显示/隐藏"""
        if self.settings_ai_key.echoMode() == QLineEdit.Password:
            self.settings_ai_key.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_key.setText("🙈")
        else:
            self.settings_ai_key.setEchoMode(QLineEdit.Password)
            self.btn_toggle_key.setText("👁")

    def _test_ai_connection(self):
        """测试AI API连接"""
        api_url = self.settings_ai_url.text().strip()
        api_key = self.settings_ai_key.text().strip()
        model = self.settings_ai_model.currentText().strip()

        if not api_url:
            QMessageBox.warning(self, tr("msg.hint"), tr("settings.fill_api_url"))
            return
        if not api_key:
            QMessageBox.warning(self, tr("msg.hint"), tr("settings.fill_api_key"))
            return
        if not model:
            QMessageBox.warning(self, tr("msg.hint"), tr("settings.select_model"))
            return

        # 显示测试中提示
        QMessageBox.information(self, tr("settings.testing"), tr("settings.testing_connection"))

        try:
            import requests
            # 构建请求
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            }

            # 确保URL格式正确
            url = api_url.rstrip("/")
            if not url.endswith("/chat/completions"):
                url = f"{url}/chat/completions"

            response = requests.post(url, headers=headers, json=data, timeout=15)

            if response.status_code == 200:
                QMessageBox.information(self, tr("msg.success"), tr("settings.api_test_success"))
            else:
                error_msg = response.text[:200] if response.text else tr("msg.unknown_error")
                QMessageBox.warning(self, tr("msg.failure"), tr("settings.api_test_failed", code=response.status_code, error=error_msg))
        except requests.exceptions.Timeout:
            QMessageBox.warning(self, tr("msg.failure"), tr("settings.connection_timeout"))
        except Exception as e:
            QMessageBox.warning(self, tr("msg.failure"), tr("settings.connection_failed", error=str(e)))

    def _save_ai_preset_config(self):
        """保存当前AI预设配置"""
        if not hasattr(self, 'settings_ai_preset'):
            return

        current_index = self.settings_ai_preset.currentIndex()
        if current_index < 0:
            QMessageBox.warning(self, tr("msg.hint"), tr("settings.select_preset_first"))
            return

        presets = self.settings.get_ai_presets()
        presets[current_index]["api_url"] = self.settings_ai_url.text().strip()
        presets[current_index]["api_key"] = self.settings_ai_key.text().strip()
        presets[current_index]["model"] = self.settings_ai_model.currentText().strip()

        self.settings.save_ai_presets(presets)
        # 保存当前选中的预设索引
        self.settings.set_current_ai_preset_index(current_index)

        # 刷新下拉框
        self._load_ai_presets_to_settings_combo()
        self.settings_ai_preset.setCurrentIndex(current_index)

        # 同时刷新AI页的预设下拉框
        self._load_ai_presets_to_combo()

        QMessageBox.information(self, tr("msg.success"), tr("settings.ai_config_saved"))

    def _update_theme_preview(self, theme_name=None):
        """更新主题预览区域"""
        if not hasattr(self, 'theme_preview_widget'):
            return
        
        if theme_name is None:
            theme_name = self.settings.get_current_theme()
        
        colors = get_theme_colors(theme_name)
        
        # 设置预览样式
        self.theme_preview_widget.setStyleSheet(scaled_style(f"""
            QWidget {{
                background-color: {colors['content_bg']};
                border: 1px solid {colors['nav_border']};
                border-radius: 8px;
            }}
        """))

        # 清除旧的布局
        if self.theme_preview_widget.layout():
            old_layout = self.theme_preview_widget.layout()
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(self.theme_preview_widget)
            layout.setContentsMargins(scaled(10), scaled(10), scaled(10), scaled(10))

        layout = self.theme_preview_widget.layout()

        # 添加预览标题
        title = QLabel(tr("settings.theme_label", theme_name=tr(f"theme.{theme_name}")))
        title.setStyleSheet(f"color: {colors['text_primary']}; font-weight: bold; border: none;")
        layout.addWidget(title)

        # 添加预览按钮行
        btn_row = QHBoxLayout()

        btn1 = QPushButton(tr("settings.preview_primary"))
        btn1.setStyleSheet(scaled_style(f"""
            QPushButton {{
                background-color: {colors['btn_primary']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }}
        """))
        btn_row.addWidget(btn1)

        btn2 = QPushButton(tr("settings.preview_info"))
        btn2.setStyleSheet(scaled_style(f"""
            QPushButton {{
                background-color: {colors['btn_info']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }}
        """))
        btn_row.addWidget(btn2)

        btn3 = QPushButton(tr("settings.preview_success"))
        btn3.setStyleSheet(scaled_style(f"""
            QPushButton {{
                background-color: {colors['btn_success']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
            }}
        """))
        btn_row.addWidget(btn3)
        btn_row.addStretch()

        layout.addLayout(btn_row)

        # 添加文字预览
        text_label = QLabel(tr("settings.preview_secondary_text"))
        text_label.setStyleSheet(f"color: {colors['text_secondary']}; border: none;")
        layout.addWidget(text_label)
    
    def _on_theme_preview_changed(self, theme_name):
        """当主题选择改变时更新预览"""
        self._update_theme_preview(theme_name)
    
    def _apply_selected_theme(self):
        """应用选中的主题"""
        if not hasattr(self, 'settings_theme_combo'):
            return

        theme_name = self.settings_theme_combo.currentData()
        if theme_name not in THEME_PRESETS:
            QMessageBox.warning(self, tr("msg.error"), tr("settings.invalid_theme", name=theme_name))
            return

        # 保存主题设置
        self.settings.save_current_theme(theme_name)

        # 更新全局颜色（部分组件会立即生效）
        global FORTRESS_COLORS
        FORTRESS_COLORS.clear()
        FORTRESS_COLORS.update(THEME_PRESETS[theme_name])

        QMessageBox.information(
            self, tr("msg.success"),
            tr("settings.theme_applied", name=tr(f"theme.{theme_name}"))
        )

    def _apply_ui_scale(self):
        """应用 UI 缩放设置"""
        if not hasattr(self, 'settings_ui_scale_combo'):
            return

        scale_text = self.settings_ui_scale_combo.currentText()
        if scale_text == tr("settings.auto"):
            scale_value = 0.0
        else:
            try:
                scale_value = float(scale_text)
            except ValueError:
                QMessageBox.warning(self, tr("msg.error"), tr("settings.invalid_scale"))
                return

        # 保存设置
        self.settings.set_ui_scale(scale_value)

        QMessageBox.information(
            self, tr("msg.success"),
            tr("settings.scale_applied", scale=scale_text)
        )

    def _apply_language(self):
        """应用语言设置"""
        if not hasattr(self, 'settings_lang_combo'):
            return
        from i18n import get_current_language, init_language
        new_lang = self.settings_lang_combo.currentData()
        old_lang = get_current_language()
        self.settings.set_language(new_lang)
        if new_lang != old_lang:
            init_language(new_lang)
            QMessageBox.information(self, tr("msg.success"), tr("settings.saved_restart_hint"))
        else:
            QMessageBox.information(self, tr("msg.success"), tr("settings.saved"))

    def _ai_do_task(self, task_type, input_widget, output_widget):
        """执行 AI 任务"""
        from core.ai_client import AIWorkerThreadV2
        
        # 获取输入
        if isinstance(input_widget, QLineEdit):
            user_input = input_widget.text().strip()
        else:
            user_input = input_widget.toPlainText().strip()
        
        if not user_input:
            QMessageBox.warning(self, tr("msg.hint"), tr("ai.enter_content"))
            return
        
        # 获取 AI 配置
        ai_config = self._get_current_ai_config()
        if not ai_config.get("api_key"):
            QMessageBox.warning(self, tr("msg.hint"), tr("ai.configure_api_first"))
            self._switch_page(5)
            return
        
        output_widget.setText(tr("ai.generating"))
        
        try:
            self.ai_worker = AIWorkerThreadV2(
                ai_config.get("api_url", ""),
                ai_config.get("api_key", ""),
                ai_config.get("model", "gpt-3.5-turbo"),
                task_type,
                user_input
            )
            self.ai_worker.result_signal.connect(lambda r: self._ai_on_result(r, output_widget, task_type))
            self.ai_worker.error_signal.connect(lambda e: self._ai_on_error(e, output_widget))
            self.ai_worker.start()
        except Exception as e:
            QMessageBox.warning(self, tr("msg.error"), tr("ai.start_failed", error=e))
            output_widget.setText(tr("msg.error_prefix", error=e))
    
    def _ai_on_result(self, result, output_widget, task_type):
        """AI 返回结果"""
        try:
            output_widget.setText(result)
            
            # 保存到历史记录
            if hasattr(self, 'ai_history_manager'):
                # 只有 FOFA 语法生成才保存输入内容
                input_text = ""
                if hasattr(self, 'ai_fofa_input') and task_type == "fofa":
                    input_text = self.ai_fofa_input.text()
                
                # 如果是漏洞分析，保存输入内容
                if hasattr(self, 'ai_analyze_input') and task_type == "analyze":
                    input_text = self.ai_analyze_input.toPlainText()

                if input_text:
                    self.ai_history_manager.add_ai_history(
                        task_type, input_text, result
                    )
        except Exception as e:
            print(f"Error in _ai_on_result: {e}")
            # 不弹窗，避免由于非关键功能（如历史记录）失败打断用户
    
    def _ai_on_error(self, error, output_widget):
        """AI 返回错误"""
        output_widget.setText(tr("msg.error_prefix", error=error))
    
    def _get_current_ai_config(self):
        """获取当前 AI 配置"""
        presets = self.settings.get_ai_presets()
        if not presets:
            return {}
        # 使用设置中保存的当前预设索引
        current_index = self.settings.get_current_ai_preset_index()
        if current_index < 0 or current_index >= len(presets):
            current_index = 0
        return presets[current_index]
    
    def _copy_text(self, widget):
        """复制文本框内容"""
        text = widget.toPlainText().strip()
        if text:
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, tr("msg.success"), tr("common.copied_to_clipboard"))
    
    def _ai_copy_fofa_and_open(self):
        """复制 FOFA 语法并跳转到 FOFA 搜索"""
        if hasattr(self, 'ai_fofa_output'):
            text = self.ai_fofa_output.toPlainText().strip()
            # 尝试提取 FOFA 语法
            import re
            matches = re.findall(r'`([^`]+)`', text)
            if matches:
                query = matches[0]
            else:
                # 尝试提取引号内容
                matches = re.findall(r'"([^"]+)"', text)
                query = matches[0] if matches else text[:100]
            
            # 设置到 FOFA 输入框并切换页面
            if hasattr(self, 'fofa_query_input'):
                self.fofa_query_input.setText(query)
                self._switch_page(3)  # 切换到 FOFA 搜索页
    
    # ================= 设置内嵌页面操作 =================
    
    def _load_all_settings(self):
        """加载所有设置到内嵌页面"""
        # 扫描参数
        scan_config = self.settings.get_scan_config()
        if hasattr(self, 'settings_timeout'):
            self.settings_timeout.setValue(scan_config.get("timeout", 5))
            self.settings_rate_limit.setValue(scan_config.get("rate_limit", 150))
            self.settings_bulk_size.setValue(scan_config.get("bulk_size", 25))
            self.settings_retries.setValue(scan_config.get("retries", 0))
            self.settings_proxy.setText(scan_config.get("proxy", ""))
            self.settings_follow_redirects.setChecked(scan_config.get("follow_redirects", False))
            self.settings_stop_at_first.setChecked(scan_config.get("stop_at_first_match", False))
            self.settings_no_httpx.setChecked(scan_config.get("no_httpx", False))
            self.settings_verbose.setChecked(scan_config.get("verbose", False))
            self.settings_use_native.setChecked(scan_config.get("use_native_scanner", False))
            if hasattr(self, 'settings_oast_mode'):
                mode_index = self.settings_oast_mode.findData(scan_config.get("oast_mode", "auto"))
                self.settings_oast_mode.setCurrentIndex(mode_index if mode_index >= 0 else 0)
                self.settings_oast_server.setText(scan_config.get("oast_server", ""))
                self.settings_oast_token.setText(scan_config.get("oast_token", ""))
                self.settings_oast_poll.setValue(scan_config.get("oast_poll_duration", 5))
                self.settings_oast_cooldown.setValue(scan_config.get("oast_cooldown_period", 5))
                self.settings_oast_cache.setValue(scan_config.get("oast_cache_size", 5000))
                self.settings_oast_eviction.setValue(scan_config.get("oast_eviction", 60))
                self.settings_oast_adapt_legacy.setChecked(scan_config.get("oast_adapt_legacy", True))
        
        # FOFA 配置
        fofa_config = self.settings.get_fofa_config()
        if hasattr(self, 'settings_fofa_url'):
            self.settings_fofa_url.setText(fofa_config.get("api_url", "https://fofa.info/api/v1/search/all"))
            self.settings_fofa_email.setText(fofa_config.get("email", ""))
            self.settings_fofa_key.setText(fofa_config.get("api_key", ""))
        
        # AI 配置 - 恢复保存的预设选择
        if hasattr(self, 'settings_ai_preset') and self.settings_ai_preset.count() > 0:
            saved_index = self.settings.get_current_ai_preset_index()
            if 0 <= saved_index < self.settings_ai_preset.count():
                self.settings_ai_preset.setCurrentIndex(saved_index)
            else:
                self.settings_ai_preset.setCurrentIndex(0)
            
            # 触发表单更新
            self._on_ai_preset_changed(self.settings_ai_preset.currentIndex())

    
    def _save_all_settings(self):
        """保存所有设置"""
        # 保存扫描参数
        if hasattr(self, 'settings_timeout'):
            self.settings.save_scan_config({
                "timeout": self.settings_timeout.value(),
                "rate_limit": self.settings_rate_limit.value(),
                "bulk_size": self.settings_bulk_size.value(),
                "retries": self.settings_retries.value(),
                "proxy": self.settings_proxy.text().strip(),
                "follow_redirects": self.settings_follow_redirects.isChecked(),
                "stop_at_first_match": self.settings_stop_at_first.isChecked(),
                "no_httpx": self.settings_no_httpx.isChecked(),
                "verbose": self.settings_verbose.isChecked(),
                "use_native_scanner": self.settings_use_native.isChecked(),
                "oast_mode": self.settings_oast_mode.currentData() if hasattr(self, 'settings_oast_mode') else "auto",
                "oast_server": self.settings_oast_server.text().strip() if hasattr(self, 'settings_oast_server') else "",
                "oast_token": self.settings_oast_token.text().strip() if hasattr(self, 'settings_oast_token') else "",
                "oast_poll_duration": self.settings_oast_poll.value() if hasattr(self, 'settings_oast_poll') else 5,
                "oast_cooldown_period": self.settings_oast_cooldown.value() if hasattr(self, 'settings_oast_cooldown') else 5,
                "oast_cache_size": self.settings_oast_cache.value() if hasattr(self, 'settings_oast_cache') else 5000,
                "oast_eviction": self.settings_oast_eviction.value() if hasattr(self, 'settings_oast_eviction') else 60,
                "oast_adapt_legacy": self.settings_oast_adapt_legacy.isChecked() if hasattr(self, 'settings_oast_adapt_legacy') else True,
            })
        
        # 保存 FOFA 配置
        if hasattr(self, 'settings_fofa_url'):
            self.settings.save_fofa_config({
                "api_url": self.settings_fofa_url.text().strip(),
                "email": self.settings_fofa_email.text().strip(),
                "api_key": self.settings_fofa_key.text().strip(),
            })
        
        # 保存 AI 配置 - 更新当前选中的预设
        if hasattr(self, 'settings_ai_preset') and self.settings_ai_preset.count() > 0:
            current_index = self.settings_ai_preset.currentIndex()
            if current_index >= 0:
                presets = self.settings.get_ai_presets()
                if current_index < len(presets):
                    # 更新当前预设的配置
                    presets[current_index]["api_url"] = self.settings_ai_url.text().strip()
                    presets[current_index]["api_key"] = self.settings_ai_key.text().strip()
                    presets[current_index]["model"] = self.settings_ai_model.currentText().strip()

                    # 保存到设置
                    self.settings.save_ai_presets(presets)

                    # 保存当前选中的预设索引
                    self.settings.set_current_ai_preset_index(current_index)

                    # 刷新下拉框以反映更新
                    self._load_ai_presets_to_settings_combo()
                    self.settings_ai_preset.setCurrentIndex(current_index)

                    # 同时刷新AI页的预设下拉框
                    self._load_ai_presets_to_combo()

        # 保存更新设置
        if hasattr(self, 'auto_update_checkbox'):
            self.settings.set_auto_check_update(self.auto_update_checkbox.isChecked())

        QMessageBox.information(self, tr("msg.success"), tr("settings.settings_saved"))

    def _check_for_updates(self):
        """检查更新"""
        self.check_update_btn.setEnabled(False)
        self.update_status_label.setText(tr("update.checking"))
        self.update_latest_version_label.setText(tr("update.checking_short"))
        self.update_latest_version_label.setStyleSheet(f"color: {FORTRESS_COLORS['btn_warning']};")

        from core.updater import UpdateCheckThread
        self._update_check_thread = UpdateCheckThread()
        self._update_check_thread.check_finished.connect(self._on_update_check_finished)
        self._update_check_thread.error_signal.connect(self._on_update_check_error)
        self._update_check_thread.start()

    def _on_update_check_finished(self, has_update, latest_version, download_url, release_notes):
        """检查更新完成"""
        self.check_update_btn.setEnabled(True)
        self.update_latest_version_label.setText(f"v{latest_version}")

        if has_update:
            self.update_latest_version_label.setStyleSheet(f"color: {FORTRESS_COLORS['btn_success']}; font-weight: bold;")
            self.update_status_label.setText(tr("update.new_version_available", version=latest_version))
            self.do_update_btn.setEnabled(True)
            self._update_download_url = download_url
            self._update_version = latest_version
        else:
            self.update_latest_version_label.setStyleSheet(f"color: {FORTRESS_COLORS['text_secondary']};")
            self.update_status_label.setText(tr("update.already_latest"))
            self.do_update_btn.setEnabled(False)

        self.release_notes_text.setText(release_notes if release_notes else tr("update.no_release_notes"))

    def _on_update_check_error(self, error_msg):
        """检查更新出错"""
        self.check_update_btn.setEnabled(True)
        self.update_latest_version_label.setText(tr("update.check_failed", error=error_msg))
        self.update_latest_version_label.setStyleSheet(f"color: {FORTRESS_COLORS['status_critical']};")
        self.update_status_label.setText(error_msg)

    def _do_update(self):
        """执行更新"""
        if not self._update_download_url:
            QMessageBox.warning(self, tr("msg.warning"), tr("update.no_download_url"))
            return

        reply = QMessageBox.question(
            self, tr("update.confirm_update"),
            tr("update.confirm_update_msg", version=self._update_version),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.check_update_btn.setEnabled(False)
        self.do_update_btn.setEnabled(False)
        self.update_progress_bar.setVisible(True)
        self.update_progress_bar.setValue(0)

        from core.updater import UpdateDownloadThread
        self._update_download_thread = UpdateDownloadThread(
            self._update_download_url,
            self._update_version
        )
        self._update_download_thread.progress_signal.connect(self._on_update_progress)
        self._update_download_thread.finished_signal.connect(self._on_update_finished)
        self._update_download_thread.start()

    def _on_update_progress(self, percent, message):
        """更新进度"""
        self.update_progress_bar.setValue(percent)
        self.update_status_label.setText(message)

    def _on_update_finished(self, success, message):
        """更新完成"""
        self.check_update_btn.setEnabled(True)
        self.update_progress_bar.setVisible(False)

        if success:
            QMessageBox.information(self, tr("update.update_success"), message)
            self.update_status_label.setText(tr("update.restart_needed"))
            reply = QMessageBox.question(
                self, tr("update.restart_app"),
                tr("update.restart_confirm"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._restart_application()
        else:
            QMessageBox.critical(self, tr("update.update_failure"), message)
            self.update_status_label.setText(tr("update.update_failed"))
            self.do_update_btn.setEnabled(True)

    def _restart_application(self):
        """重启应用程序"""
        import sys
        import os
        python = sys.executable
        if is_frozen():
            os.execl(python, python)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        os.execl(python, python, script)

    
    def _test_fofa_connection(self):
        """测试 FOFA API 连接"""
        from core.fofa_client import FofaSearchThread
        
        api_url = self.settings_fofa_url.text().strip() if hasattr(self, 'settings_fofa_url') else ""
        email = self.settings_fofa_email.text().strip() if hasattr(self, 'settings_fofa_email') else ""
        api_key = self.settings_fofa_key.text().strip() if hasattr(self, 'settings_fofa_key') else ""
        
        if not api_key:
            QMessageBox.warning(self, tr("msg.hint"), tr("fofa.fill_api_key"))
            return
        
        # 简单测试
        try:
            self.fofa_test_thread = FofaSearchThread(api_url, email, api_key, 'port="80"', 1)
            self.fofa_test_thread.result_signal.connect(
                lambda r: QMessageBox.information(self, tr("msg.success"), tr("fofa.connection_ok"))
            )
            self.fofa_test_thread.error_signal.connect(
                lambda e: QMessageBox.critical(self, tr("msg.failure"), tr("fofa.connection_failed", error=e))
            )
            self.fofa_test_thread.start()
        except Exception as e:
            QMessageBox.critical(self, tr("msg.error"), tr("fofa.test_failed", error=str(e)))

    # ================= 工具栏按钮事件 =================

    def open_settings_dialog(self):
        """打开设置弹窗"""
        self._settings_dialog = SettingsDialog(self)
        if self._settings_dialog.exec_() == QDialog.Accepted:
            # 重新加载扫描参数
            self.load_scan_config()

    def show_settings_dialog(self):
        """显示设置弹窗（别名方法）"""
        self.open_settings_dialog()
    
    def open_fofa_dialog(self, query=None):
        """打开 FOFA 搜索弹窗"""
        dialog = FofaDialog(self, query)
        if dialog.exec_() == QDialog.Accepted:
            # 将选中的目标导入到扫描目标（替换模式）
            targets = dialog.get_selected_targets()
            if targets:
                new_targets = "\n".join(targets)
                self.txt_targets.setPlainText(new_targets)  # 替换而不是追加
                QMessageBox.information(self, tr("msg.success"), tr("fofa.imported_targets", count=len(targets)))
    
    def _check_nuclei_status(self):
        """检测 Nuclei 状态"""
        try:
            from core.nuclei_runner import get_nuclei_path
            import os
            
            nuclei_path = get_nuclei_path()
            
            if os.path.exists(nuclei_path):
                self.nuclei_status_label.setText(tr("nuclei.status_installed"))
                self.nuclei_status_label.setStyleSheet(f"color: {FORTRESS_COLORS['btn_success']}; font-weight: bold;")
                self.download_nuclei_btn.setText(tr("nuclei.update_latest"))
            else:
                self.nuclei_status_label.setText(tr("nuclei.status_not_installed"))
                self.nuclei_status_label.setStyleSheet(f"color: {FORTRESS_COLORS['status_critical']}; font-weight: bold;")
                self.download_nuclei_btn.setText(tr("nuclei.download_latest"))

        except Exception as e:
            self.nuclei_status_label.setText(tr("nuclei.detect_failed", error=str(e)))
            self.nuclei_status_label.setStyleSheet(f"color: {FORTRESS_COLORS['status_critical']}; font-weight: bold;")
    
    def _download_nuclei(self):
        """下载 Nuclei"""
        try:
            import subprocess
            import sys
            import os
            from PyQt5.QtCore import QThread, pyqtSignal
            from PyQt5.QtWidgets import QMessageBox
            
            # 创建下载线程
            class NucleiDownloadThread(QThread):
                progress_signal = pyqtSignal(str)
                finished_signal = pyqtSignal(bool, str)
                
                def run(self):
                    try:
                        self.progress_signal.emit(tr("nuclei.downloading"))
                        from download_nuclei_with_progress import download_with_callback

                        def on_progress(message, percent=None):
                            self.progress_signal.emit(str(message))

                        if download_with_callback(on_progress):
                            self.finished_signal.emit(True, tr("nuclei.download_complete"))
                        else:
                            self.finished_signal.emit(False, tr("nuclei.download_failed"))
                            
                    except Exception as e:
                        self.finished_signal.emit(False, tr("nuclei.download_error", error=str(e)))
            
            # 禁用按钮并启动下载
            self.download_nuclei_btn.setEnabled(False)
            self.nuclei_progress_label.setText(tr("nuclei.preparing_download"))
            
            self.nuclei_download_thread = NucleiDownloadThread()
            self.nuclei_download_thread.progress_signal.connect(self.nuclei_progress_label.setText)
            self.nuclei_download_thread.finished_signal.connect(self._on_nuclei_download_finished)
            self.nuclei_download_thread.start()
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, tr("msg.error"), tr("nuclei.start_download_failed", error=str(e)))
            self.download_nuclei_btn.setEnabled(True)
    
    def _on_nuclei_download_finished(self, success, message):
        """Nuclei 下载完成回调"""
        from PyQt5.QtWidgets import QMessageBox
        self.download_nuclei_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, tr("msg.success"), message)
            self.nuclei_progress_label.setText(tr("nuclei.download_done"))
            self._check_nuclei_status()  # 重新检测状态
        else:
            QMessageBox.critical(self, tr("msg.failure"), message)
            self.nuclei_progress_label.setText(tr("nuclei.download_failed_status"))
    
    def open_ai_dialog(self):
        """打开 AI 助手弹窗"""
        dialog = AIAssistantDialog(self)
        dialog.exec_()

    # ================= 仪表盘页面 =================
    def setup_dashboard_tab(self):
        layout = QVBoxLayout(self.dashboard_tab)
        layout.setSpacing(scaled(10))
        
        # 统计数据
        from core.scan_history import get_scan_history
        stats = get_scan_history().get_statistics()
        
        # ===== 顶部统计卡片（紧凑型）=====
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(scaled(10))
        
        poc_count = self.poc_library.get_poc_count() if hasattr(self, 'poc_library') else 0
        
        self.card_scans = self._create_mini_card(tr("dashboard.scan_count"), str(stats.get('total_scans', 0)), "#3498db")
        self.card_vulns = self._create_mini_card(tr("dashboard.vuln_found"), str(stats.get('total_vulns', 0)), "#e74c3c")
        self.card_pocs = self._create_mini_card(tr("dashboard.poc_count"), str(poc_count), "#27ae60")
        self.card_critical = self._create_mini_card(tr("dashboard.critical_vulns"), str(stats.get('severity_distribution', {}).get('critical', 0)), "#9b59b6")
        self.card_high = self._create_mini_card(tr("dashboard.high_vulns"), str(stats.get('severity_distribution', {}).get('high', 0)), "#e67e22")
        
        cards_layout.addWidget(self.card_scans)
        cards_layout.addWidget(self.card_vulns)
        cards_layout.addWidget(self.card_pocs)
        cards_layout.addWidget(self.card_critical)
        cards_layout.addWidget(self.card_high)
        
        layout.addLayout(cards_layout)
        
        # ===== 主内容区：左中右三栏 =====
        content_splitter = QSplitter(Qt.Horizontal)
        
        # 左栏：漏洞分布
        left_panel = QGroupBox(tr("dashboard.vuln_distribution"))
        left_layout = QVBoxLayout()
        left_layout.setSpacing(scaled(5))
        
        # 保存漏洞分布条形图的引用，以便后续刷新时更新
        self.severity_bars = {}
        severity_dist = stats.get('severity_distribution', {})
        for sev, (color, label) in [('critical', ('#9b59b6', tr("severity.critical"))), ('high', ('#e74c3c', tr("severity.high"))),
                                     ('medium', ('#e67e22', tr("severity.medium"))), ('low', ('#3498db', tr("severity.low"))),
                                     ('info', ('#1abc9c', tr("severity.info")))]:
            bar_widget, bar = self._create_severity_bar(label, severity_dist.get(sev, 0), color)
            self.severity_bars[sev] = bar  # 保存 QProgressBar 引用
            left_layout.addWidget(bar_widget)
        
        left_layout.addStretch()
        
        # TOP 漏洞模板
        top_group = QLabel(tr("dashboard.top_templates"))
        top_group.setStyleSheet(scaled_style("font-weight: bold; margin-top: 10px;"))
        left_layout.addWidget(top_group)
        
        for tpl in stats.get('top_templates', [])[:5]:
            tpl_label = QLabel(f"• {tpl['template'][:30]}... ({tpl['count']})")
            tpl_label.setStyleSheet(scaled_style("color: #7f8c8d; font-size: 11px;"))
            left_layout.addWidget(tpl_label)
        
        if not stats.get('top_templates'):
            left_layout.addWidget(QLabel(tr("dashboard.no_data")))
        
        left_panel.setLayout(left_layout)
        content_splitter.addWidget(left_panel)
        
        # 中栏：扫描历史
        center_panel = QGroupBox(tr("dashboard.scan_history"))
        center_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        # 应用 FORTRESS 表格样式（美化表头和序号）
        from core.fortress_style import get_table_stylesheet
        self.history_table.setStyleSheet(get_table_stylesheet(FORTRESS_COLORS))
        
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([tr("history.time"), tr("history.target"), tr("history.poc"), tr("history.vuln"), tr("history.status"), tr("common.detail"), tr("common.export")])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            self.history_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
        # 详情和导出列：设置固定宽度以适配按钮
        for i in [5, 6]:
            self.history_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
            self.history_table.setColumnWidth(i, scaled(100))
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        # 增加行高，让按钮显示不拥挤
        self.history_table.verticalHeader().setDefaultSectionSize(scaled(45))
        self.history_table.verticalHeader().setVisible(False) # 隐藏垂直表头，统一风格
        # 移除高度限制，让表格自动填充可用空间
        self.history_table.setMinimumHeight(scaled(200))
        center_layout.addWidget(self.history_table, 1)  # stretch factor = 1，让表格优先获取空间
        
        btn_row = QHBoxLayout()
        btn_refresh = self._create_fortress_button(tr("common.refresh"), "info")
        btn_refresh.clicked.connect(self.refresh_dashboard)
        btn_row.addWidget(btn_refresh)

        btn_clear = self._create_fortress_button(tr("dashboard.clear"), "warning")
        btn_clear.clicked.connect(self.clear_scan_history)
        btn_row.addWidget(btn_clear)
        
        # 查看全部按钮
        btn_view_all = self._create_fortress_button(tr("dashboard.view_all"), "primary")
        btn_view_all.setToolTip(tr("dashboard.view_all_tooltip"))
        btn_view_all.clicked.connect(self.open_all_scan_history_dialog)
        btn_row.addWidget(btn_view_all)
        
        btn_row.addStretch()
        center_layout.addLayout(btn_row)
        
        center_panel.setLayout(center_layout)
        content_splitter.addWidget(center_panel)

        # 右栏：快捷操作
        right_panel = QGroupBox(tr("dashboard.quick_actions"))
        right_layout = QVBoxLayout()
        right_layout.setSpacing(scaled(15))  # 增加间距

        btn_new_scan = self._create_fortress_button(tr("scan.new_scan"), "primary")
        btn_new_scan.setMinimumHeight(scaled(45))
        btn_new_scan.clicked.connect(self.show_new_scan_dialog)
        right_layout.addWidget(btn_new_scan)

        btn_sync_poc = self._create_fortress_button(tr("poc.sync_library"), "purple")
        btn_sync_poc.setMinimumHeight(scaled(45))
        btn_sync_poc.clicked.connect(self.open_poc_sync_dialog)
        right_layout.addWidget(btn_sync_poc)

        btn_ai = self._create_fortress_button(tr("nav.ai_assistant"), "warning")
        btn_ai.setMinimumHeight(scaled(45))
        btn_ai.clicked.connect(lambda: self._switch_page(4)) # 切换到 AI 助手页 (index 4)
        right_layout.addWidget(btn_ai)

        btn_fofa = self._create_fortress_button(tr("nav.fofa_search"), "success")
        btn_fofa.setMinimumHeight(scaled(45))
        btn_fofa.clicked.connect(lambda: self._switch_page(3))
        right_layout.addWidget(btn_fofa)

        right_layout.addStretch()

        # 今日统计
        today_label = QLabel(tr("dashboard.today_stats"))
        today_label.setStyleSheet(scaled_style("font-weight: bold; margin-top: 15px;"))
        right_layout.addWidget(today_label)
        
        trend = stats.get('trend_7days', [])
        today_scans = trend[-1]['scans'] if trend else 0
        today_vulns = trend[-1]['vulns'] if trend else 0
        right_layout.addWidget(QLabel(tr("dashboard.today_scans", count=today_scans)))
        right_layout.addWidget(QLabel(tr("dashboard.today_vulns", count=today_vulns)))
        
        right_panel.setLayout(right_layout)
        content_splitter.addWidget(right_panel)
        
        content_splitter.setSizes([250, 450, 200])
        layout.addWidget(content_splitter)
        
        self.refresh_dashboard()
    
    def _create_mini_card(self, title, value, color):
        """创建紧凑型统计卡片（支持 DPI 缩放）"""
        card = QFrame()
        card.setFixedHeight(scaled(70))
        card.setStyleSheet(scaled_style(f"""
            QFrame {{
                background-color: {color};
                border-radius: 8px;
            }}
        """))

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(scaled(10), scaled(5), scaled(10), scaled(5))
        card_layout.setSpacing(scaled(2))

        title_label = QLabel(title)
        title_label.setStyleSheet(scaled_style("color: rgba(255,255,255,0.85); font-size: 11px;"))
        card_layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet(scaled_style("color: white; font-size: 22px; font-weight: bold;"))
        card_layout.addWidget(value_label)

        return card

    def _create_severity_bar(self, label, count, color):
        """创建严重程度进度条，返回包含控件的容器和进度条本身"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, scaled(2), 0, scaled(2))

        label_widget = QLabel(f"{label}:")
        label_widget.setFixedWidth(scaled(50))
        layout.addWidget(label_widget)

        bar = QProgressBar()
        bar.setRange(0, max(count, 10))
        bar.setValue(count)
        bar.setFormat(f"{count}")
        bar.setStyleSheet(scaled_style(f"""
            QProgressBar {{
                border: none;
                border-radius: 5px;
                background-color: %PLACEHOLDER%;
                text-align: center;
                color: {FORTRESS_COLORS.get('nav_text', '#f1f5f9')}; /* 增加文字颜色定义，确保深色模式下可见 */
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 5px;
            }}
        """.replace("%PLACEHOLDER%", FORTRESS_COLORS.get('nav_border', '#ecf0f1'))))
        layout.addWidget(bar)

        return widget, bar  # 同时返回容器和进度条
    
    def refresh_dashboard(self):
        """刷新仪表盘数据"""
        from core.scan_history import get_scan_history
        
        history_mgr = get_scan_history()
        
        # 刷新统计卡片数据
        stats = history_mgr.get_statistics()
        poc_count = self.poc_library.get_poc_count() if hasattr(self, 'poc_library') else 0
        
        # 更新卡片值 - 找到卡片内的值标签并更新
        self._update_card_value(self.card_scans, str(stats.get('total_scans', 0)))
        self._update_card_value(self.card_vulns, str(stats.get('total_vulns', 0)))
        self._update_card_value(self.card_pocs, str(poc_count))
        self._update_card_value(self.card_critical, str(stats.get('severity_distribution', {}).get('critical', 0)))
        self._update_card_value(self.card_high, str(stats.get('severity_distribution', {}).get('high', 0)))
        
        # 更新漏洞分布条形图
        if hasattr(self, 'severity_bars'):
            severity_dist = stats.get('severity_distribution', {})
            for sev, bar in self.severity_bars.items():
                count = severity_dist.get(sev, 0)
                bar.setRange(0, max(count, 10))
                bar.setValue(count)
                bar.setFormat(f"{count}")
        

        
        # 刷新表格样式以适应可能的主题变化
        from core.fortress_style import get_table_stylesheet
        self.history_table.setStyleSheet(get_table_stylesheet(FORTRESS_COLORS))

        # 刷新历史表格
        history = history_mgr.get_recent_scans(20)
        
        self.history_table.setUpdatesEnabled(False)
        self.history_table.setRowCount(0)
        self.history_table.setRowCount(len(history))
        
        for row, record in enumerate(history):
            # 时间
            scan_time = record.get('scan_time', '')[:19]  # 截取日期时间
            self.history_table.setItem(row, 0, QTableWidgetItem(scan_time))
            
            # Targets
            self.history_table.setItem(row, 1, QTableWidgetItem(str(record.get('target_count', 0))))
            
            # POC 数
            self.history_table.setItem(row, 2, QTableWidgetItem(str(record.get('poc_count', 0))))
            
            # Vulns
            vuln_count = record.get('vuln_count', 0)
            vuln_item = QTableWidgetItem(str(vuln_count))
            if vuln_count > 0:
                vuln_item.setForeground(QColor('#e74c3c'))
                vuln_item.setFont(QFont("Arial", scaled(10), QFont.Bold))
            self.history_table.setItem(row, 3, vuln_item)
            
            # 状态
            status = record.get('status', 'completed')
            status_item = QTableWidgetItem(display_scan_status(status))
            if status == 'stopped':
                status_item.setForeground(QColor('#e67e22'))
            else:
                status_item.setForeground(QColor('#27ae60'))
            self.history_table.setItem(row, 4, status_item)
            
            # 查看详情按钮
            btn_detail = QPushButton(tr("common.detail"))
            btn_detail.setCursor(Qt.PointingHandCursor)
            # 强制指定 QPushButton#ID 选择器，优先级最高
            btn_detail.setStyleSheet(scaled_style(f"""
                QPushButton {{
                    background-color: {FORTRESS_COLORS['btn_info']};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-family: "Microsoft YaHei", sans-serif;
                    font-size: 12px;
                    font-weight: normal;
                    padding: 0px;
                    min-height: 0px;
                    min-width: 0px;
                }}
                QPushButton:hover {{
                    background-color: {FORTRESS_COLORS['btn_info_hover']};
                }}
            """))
            btn_detail.setProperty("scan_id", record.get('id'))
            btn_detail.clicked.connect(lambda checked, sid=record.get('id'): self.show_scan_detail(sid))
            # 创建容器居中按钮
            w_detail = QWidget()
            w_detail.setObjectName("cell_container")
            w_detail.setStyleSheet("#cell_container { background: transparent; }")
            l_detail = QHBoxLayout(w_detail)
            l_detail.setContentsMargins(scaled(2), scaled(2), scaled(2), scaled(2))
            l_detail.addWidget(btn_detail)
            self.history_table.setCellWidget(row, 5, w_detail)

            # 导出按钮
            btn_export = QPushButton(tr("common.export"))
            btn_export.setCursor(Qt.PointingHandCursor)
            btn_export.setStyleSheet(scaled_style(f"""
                QPushButton {{
                    background-color: {FORTRESS_COLORS['btn_warning']};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-family: "Microsoft YaHei", sans-serif;
                    font-size: 12px;
                    font-weight: normal;
                    padding: 0px;
                    min-height: 0px;
                    min-width: 0px;
                }}
                QPushButton:hover {{
                    background-color: {FORTRESS_COLORS['btn_warning_hover']};
                }}
            """))
            btn_export.setProperty("scan_id", record.get('id'))
            btn_export.clicked.connect(lambda checked, sid=record.get('id'): self.export_scan_record(sid))
            # 创建容器居中按钮
            w_export = QWidget()
            w_export.setObjectName("cell_container")
            w_export.setStyleSheet("#cell_container { background: transparent; }")
            l_export = QHBoxLayout(w_export)
            l_export.setContentsMargins(scaled(2), scaled(2), scaled(2), scaled(2))
            l_export.addWidget(btn_export)
            self.history_table.setCellWidget(row, 6, w_export)
        
        self.history_table.setUpdatesEnabled(True)
    
    def _update_card_value(self, card, value):
        """更新统计卡片的值"""
        # 卡片布局中第二个 widget 是值标签
        layout = card.layout()
        if layout and layout.count() >= 2:
            value_label = layout.itemAt(1).widget()
            if value_label:
                value_label.setText(value)
    
    def open_all_scan_history_dialog(self):
        """打开全部扫描历史弹窗"""
        from dialogs.all_scan_history_dialog import AllScanHistoryDialog
        dialog = AllScanHistoryDialog(self, colors=FORTRESS_COLORS)
        dialog.exec_()
    
    def show_scan_detail(self, scan_id):
        """显示扫描详情"""
        from core.scan_history import get_scan_history
        import json  # 需要 json 解析 raw_json
        from core.fortress_style import apply_fortress_style, get_table_stylesheet
        
        vulns = get_scan_history().get_scan_vulns(scan_id)
        
        if not vulns:
            QMessageBox.information(self, tr("history.scan_detail"), tr("history.no_vulns_found"))
            return
        
        # 使用 QDialog + QTableWidget 显示
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("history.scan_detail"))
        dialog.resize(scaled(1000), scaled(600))  # 稍微加宽以容纳新列
        apply_fortress_style(dialog, FORTRESS_COLORS)
        
        layout = QVBoxLayout(dialog)
        
        # 信息标签
        lbl_info = QLabel(tr("history.vulns_found", count=len(vulns)))
        lbl_info.setStyleSheet(scaled_style(f"font-weight: bold; font-size: 14px; color: {FORTRESS_COLORS['text_primary']};"))
        layout.addWidget(lbl_info)
        
        # 详情列表
        table = QTableWidget()
        table.setStyleSheet(get_table_stylesheet(FORTRESS_COLORS))
        table.setColumnCount(6)  # 增加 Payload 列
        table.setHorizontalHeaderLabels([tr("scan.col_severity"), "POC ID", tr("scan.col_target"), "Payload / Request", tr("scan.col_poc_path"), tr("scan.col_action")])
        
        # 优化表格样式和行高
        table.verticalHeader().setDefaultSectionSize(scaled(45))  # 增加行高，防止按钮被压缩
        table.verticalHeader().setVisible(False)          # 隐藏垂直表头，使界面更整洁且无色差
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)      # 目标
        header.setSectionResizeMode(3, QHeaderView.Stretch)      # Payload
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # POC 路径
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        table.setColumnWidth(5, scaled(140))  # 操作列稍宽
        
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setRowCount(len(vulns))
        
        from dialogs.poc_editor_dialog import POCEditorDialog

        for row, v in enumerate(vulns):
            # 解析 raw_json 获取请求详情
            raw_data = {}
            try:
                if v.get('raw_json'):
                    raw_data = json.loads(v['raw_json'])
            except:
                pass
            
            # 解析请求信息 - 兼容 nuclei.exe 和 native_scanner 两种格式
            method = "GET"
            body = ""
            full_request = ""
            curl_command = ""
            response_data = ""
            
            if raw_data:
                # 优先使用 nuclei.exe 的格式 (request 字段包含Full request)
                if raw_data.get('request'):
                    full_request = raw_data['request']
                    # 解析请求方法
                    first_line = full_request.split('\r\n')[0] if '\r\n' in full_request else full_request.split('\n')[0]
                    if first_line:
                        parts = first_line.split(' ')
                        if parts:
                            method = parts[0]
                    # 解析请求 body (在空行之后)
                    if '\r\n\r\n' in full_request:
                        body = full_request.split('\r\n\r\n', 1)[1] if len(full_request.split('\r\n\r\n')) > 1 else ""
                    elif '\n\n' in full_request:
                        body = full_request.split('\n\n', 1)[1] if len(full_request.split('\n\n')) > 1 else ""
                else:
                    # native_scanner 格式
                    method = raw_data.get('request_method', 'GET')
                    body = raw_data.get('request_body', '')
                
                # 获取其他有用字段
                curl_command = raw_data.get('curl-command', '')
                response_data = raw_data.get('response', '')
            
            # 严重程度
            sev = v.get('severity', 'unknown')
            sev_item = QTableWidgetItem(sev)
            if sev == 'critical':
                sev_item.setForeground(QColor('#9b59b6'))
                sev_item.setFont(QFont("Arial", scaled(9), QFont.Bold))
            elif sev == 'high':
                sev_item.setForeground(QColor('#e74c3c'))
                sev_item.setFont(QFont("Arial", scaled(9), QFont.Bold))
            elif sev == 'medium':
                sev_item.setForeground(QColor('#e67e22'))
            elif sev == 'low':
                sev_item.setForeground(QColor('#3498db'))
            elif sev == 'info':
                sev_item.setForeground(QColor('#1abc9c'))
            table.setItem(row, 0, sev_item)
            
            # POC ID
            table.setItem(row, 1, QTableWidgetItem(v.get('template_id', '')))
            
            # 目标
            table.setItem(row, 2, QTableWidgetItem(v.get('matched_at', '')))
            
            # Payload / 请求
            payload_text = method
            if body:
                # 如果有 body，显示部分内容
                clean_body = body.strip().replace('\r\n', ' ').replace('\n', ' ')
                if len(clean_body) > 50:
                    payload_text += f": {clean_body[:50]}..."
                else:
                    payload_text += f": {clean_body}"
            
            payload_item = QTableWidgetItem(payload_text)
            if full_request or body:
                payload_item.setToolTip(f"Full request:\n\n{full_request if full_request else body}")
            table.setItem(row, 3, payload_item)

            # 路径
            path = v.get('template_path')
            display_path = path if path else ""
            path_item = QTableWidgetItem(os.path.basename(display_path) if display_path else "") # 只显示文件名，完整路径放 tooltip
            path_item.setToolTip(display_path)
            table.setItem(row, 4, path_item)
            
            # 操作按钮 - 只保留一个详情按钮，POC编辑在详情窗口中
            btn_detail = QPushButton(tr("common.detail"))
            btn_detail.setToolTip(tr("report.detail_tooltip"))
            btn_detail.setStyleSheet(scaled_style(f"""
                QPushButton {{
                    background-color: {FORTRESS_COLORS['btn_info']};
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 3px 10px;
                }}
                QPushButton:hover {{
                    background-color: {FORTRESS_COLORS['btn_info_hover']};
                }}
            """))
            btn_detail.clicked.connect(lambda checked, vd=v, rd=raw_data: self._show_vuln_detail(vd, rd))
            table.setCellWidget(row, 5, btn_detail)
        
        layout.addWidget(table)
        
        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_copy = self._create_fortress_button(tr("report.copy_all"), "primary")
        btn_copy.clicked.connect(lambda: self._copy_vulns_to_clipboard(vulns))
        btn_row.addWidget(btn_copy)
        
        btn_close = self._create_fortress_button("OK", "warning")
        btn_close.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_close)
        
        layout.addLayout(btn_row)
        
        dialog.exec_()

    def _show_payload_detail(self, method, body):
        """显示完整 Payload 详情 - 类似编辑器的窗口"""
        from PyQt5.QtWidgets import QTextEdit, QSplitter
        from PyQt5.QtGui import QFont
        from core.fortress_style import apply_fortress_style
        
        d = QDialog(self)
        d.setWindowTitle(tr("report.request_detail", method=method))
        d.resize(scaled(700), scaled(500))
        apply_fortress_style(d, FORTRESS_COLORS)
        
        layout = QVBoxLayout(d)
        
        # 标题
        title = QLabel(tr("report.request_payload", method=method))
        title.setStyleSheet(scaled_style(f"font-weight: bold; font-size: 14px; margin-bottom: 10px; color: {FORTRESS_COLORS['text_primary']};"))
        layout.addWidget(title)

        # 内容编辑器（只读，但可选择复制）
        editor = QTextEdit()
        editor.setPlainText(body)
        editor.setReadOnly(True)
        editor.setFont(QFont("Consolas", scaled(10)))
        editor.setStyleSheet(scaled_style("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }
        """))
        layout.addWidget(editor)
        
        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_copy = self._create_fortress_button(tr("common.copy"), "primary")
        btn_copy.clicked.connect(lambda: (
            QApplication.clipboard().setText(body),
            QMessageBox.information(d, tr("msg.success"), tr("common.copied_to_clipboard"))
        ))
        btn_row.addWidget(btn_copy)
        
        btn_close = self._create_fortress_button(tr("common.close"), "warning")
        btn_close.clicked.connect(d.accept)
        btn_row.addWidget(btn_close)
        
        layout.addLayout(btn_row)
        d.exec_()

    def _show_vuln_detail(self, vuln_data, raw_data):
        """显示完整漏洞详情 - 类似编辑器的窗口，可复制粘贴"""
        from PyQt5.QtWidgets import QTextEdit
        from PyQt5.QtGui import QFont
        from core.fortress_style import apply_fortress_style
        
        d = QDialog(self)
        d.setWindowTitle(tr("report.vuln_detail", id=vuln_data.get('template_id', 'Unknown')))
        d.resize(scaled(900), scaled(700))
        apply_fortress_style(d, FORTRESS_COLORS)
        
        layout = QVBoxLayout(d)
        
        # 标题
        sev = vuln_data.get('severity', 'unknown')
        title = QLabel(f"🔴 [{sev.upper()}] {vuln_data.get('template_id', 'Unknown')}")
        title.setStyleSheet(scaled_style(f"font-weight: bold; font-size: 16px; margin-bottom: 10px; color: {FORTRESS_COLORS['text_primary']};"))
        layout.addWidget(title)
        
        # 解析请求信息 - 兼容 nuclei.exe 和 native_scanner 两种格式
        method = "GET"
        body = ""
        full_request = ""
        curl_command = ""
        response_data = ""
        
        if raw_data:
            # 优先使用 nuclei.exe 的格式
            if raw_data.get('request'):
                full_request = raw_data['request']
                first_line = full_request.split('\r\n')[0] if '\r\n' in full_request else full_request.split('\n')[0]
                if first_line:
                    parts = first_line.split(' ')
                    if parts:
                        method = parts[0]
                if '\r\n\r\n' in full_request:
                    body = full_request.split('\r\n\r\n', 1)[1] if len(full_request.split('\r\n\r\n')) > 1 else ""
                elif '\n\n' in full_request:
                    body = full_request.split('\n\n', 1)[1] if len(full_request.split('\n\n')) > 1 else ""
            else:
                method = raw_data.get('request_method', 'GET')
                body = raw_data.get('request_body', '')
            
            curl_command = raw_data.get('curl-command', '')
            response_data = raw_data.get('response', '')
        
        # === 从 POC 文件解析Full request链 ===
        poc_requests_text = ""
        poc_path = vuln_data.get('template_path') or (raw_data.get('template-path') if raw_data else None)
        
        # 从 matched_at 提取实际的 Hostname
        matched_url = vuln_data.get('matched_at', '')
        actual_hostname = ""
        actual_base_url = ""
        if matched_url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(matched_url)
                # 获取 host:port 格式
                if parsed.port and parsed.port not in [80, 443]:
                    actual_hostname = f"{parsed.hostname}:{parsed.port}"
                else:
                    actual_hostname = parsed.hostname or ""
                # 获取完整的 base URL (scheme://host:port)
                actual_base_url = f"{parsed.scheme}://{actual_hostname}"
            except:
                pass
        
        if poc_path and os.path.exists(poc_path):
            try:
                import yaml
                with open(poc_path, 'r', encoding='utf-8') as f:
                    poc_content = yaml.safe_load(f)
                
                # 解析 http 部分的请求
                http_section = poc_content.get('http', [])
                if http_section:
                    request_steps = []
                    step_num = 1
                    
                    for item in http_section:
                        # 检查 raw 请求
                        raw_requests = item.get('raw', [])
                        if raw_requests:
                            for raw_req in raw_requests:
                                # 替换模板变量
                                req_content = raw_req.strip()
                                if actual_hostname:
                                    req_content = req_content.replace('{{Hostname}}', actual_hostname)
                                    req_content = req_content.replace('{{BaseURL}}', actual_base_url)
                                    req_content = req_content.replace('{{Host}}', actual_hostname)
                                
                                request_steps.append({
                                    'step': step_num,
                                    'type': 'raw',
                                    'content': req_content
                                })
                                step_num += 1
                        
                        # 检查 path/method 形式的请求
                        if item.get('path') or item.get('method'):
                            req_method = item.get('method', 'GET')
                            paths = item.get('path', [])
                            if isinstance(paths, str):
                                paths = [paths]
                            for path in paths:
                                # 替换模板变量
                                actual_path = path
                                actual_body = item.get('body', '')
                                if actual_hostname:
                                    actual_path = actual_path.replace('{{Hostname}}', actual_hostname)
                                    actual_path = actual_path.replace('{{BaseURL}}', actual_base_url)
                                    if actual_body:
                                        actual_body = actual_body.replace('{{Hostname}}', actual_hostname)
                                        actual_body = actual_body.replace('{{BaseURL}}', actual_base_url)
                                
                                request_steps.append({
                                    'step': step_num,
                                    'type': 'standard',
                                    'method': req_method,
                                    'path': actual_path,
                                    'body': actual_body
                                })
                                step_num += 1
                    
                    # 生成请求链文本
                    if len(request_steps) > 1:
                        poc_requests_text = f"\n⚠️ This POC contains {len(request_steps)} request steps, execute in order：\n\n"
                        
                        for req in request_steps:
                            poc_requests_text += f"────────── Step {req['step']} ──────────\n"
                            if req['type'] == 'raw':
                                poc_requests_text += f"{req['content']}\n\n"
                            else:
                                poc_requests_text += f"{req['method']} {req['path']}\n"
                                if req.get('body'):
                                    poc_requests_text += f"\n{req['body']}\n"
                                poc_requests_text += "\n"
                    elif len(request_steps) == 1:
                        # 单步骤，使用 POC 中的原始请求替代
                        req = request_steps[0]
                        if req['type'] == 'raw' and not full_request:
                            full_request = req['content']
            except Exception as e:
                # 解析失败，忽略
                pass
        
        # 构建详情内容
        detail_content = f"""════════════════════════════════════════════════════════════════
                            Vulnerability Detail
════════════════════════════════════════════════════════════════

[Severity]{sev}

【POC ID】{vuln_data.get('template_id', 'N/A')}

[Target]
{vuln_data.get('matched_at', 'N/A')}

[POC Path]
{poc_path or 'Unknown'}

"""
        
        # 如果有多步骤请求链，优先显示
        if poc_requests_text:
            detail_content += f"""════════════════════════════════════════════════════════════════
                     POC Full Request Chain (parsed from POC file)
════════════════════════════════════════════════════════════════
{poc_requests_text}
"""
        
        # 添加 Nuclei 记录的最后一次请求
        detail_content += f"""════════════════════════════════════════════════════════════════
                    Trigger Request (Nuclei recorded)
════════════════════════════════════════════════════════════════

{full_request if full_request else f"[{method}] (no full request data)"}

"""

        # 如果有 curl 命令，添加到详情中
        if curl_command:
            detail_content += f"""════════════════════════════════════════════════════════════════
                            CURL Command (for reproduction)
════════════════════════════════════════════════════════════════

{curl_command}

"""

        # 如果有Response Data，添加到详情中
        if response_data:
            detail_content += f"""════════════════════════════════════════════════════════════════
                            Response Data
════════════════════════════════════════════════════════════════

{response_data}

"""

        detail_content += """════════════════════════════════════════════════════════════════
                            Reproduction Steps
════════════════════════════════════════════════════════════════

1. Copy the target URL above or use the CURL command to reproduce
2. If full request data is available, use Burp Suite or similar tools to replay
3. 可点击"编辑 POC"按钮查看完整 POC 内容

"""
        
        # 内容编辑器（只读，但可选择复制）
        editor = QTextEdit()
        editor.setPlainText(detail_content)
        editor.setReadOnly(True)
        editor.setFont(QFont("Consolas", scaled(10)))
        editor.setStyleSheet(scaled_style("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }
        """))
        layout.addWidget(editor)
        
        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        # 复制目标
        btn_copy_url = self._create_fortress_button(tr("report.copy_target"), "primary")
        btn_copy_url.clicked.connect(lambda: (
            QApplication.clipboard().setText(vuln_data.get('matched_at', '')),
            QMessageBox.information(d, tr("msg.success"), tr("report.target_copied"))
        ))
        btn_row.addWidget(btn_copy_url)
        
        # 复制 CURL 命令
        if curl_command:
            btn_copy_curl = self._create_fortress_button(tr("report.copy_curl"), "primary")
            btn_copy_curl.clicked.connect(lambda: (
                QApplication.clipboard().setText(curl_command),
                QMessageBox.information(d, tr("msg.success"), tr("report.curl_copied"))
            ))
            btn_row.addWidget(btn_copy_curl)
        
        # 复制Full request
        if full_request:
            btn_copy_req = self._create_fortress_button(tr("report.copy_request"), "primary")
            btn_copy_req.clicked.connect(lambda: (
                QApplication.clipboard().setText(full_request),
                QMessageBox.information(d, tr("msg.success"), tr("report.request_copied"))
            ))
            btn_row.addWidget(btn_copy_req)
        
        # 复制全部
        btn_copy_all = self._create_fortress_button(tr("report.copy_all"), "info")
        btn_copy_all.clicked.connect(lambda: (
            QApplication.clipboard().setText(detail_content),
            QMessageBox.information(d, tr("msg.success"), tr("common.copied_to_clipboard"))
        ))
        btn_row.addWidget(btn_copy_all)
        
        # 编辑 POC
        poc_path = vuln_data.get('template_path') or raw_data.get('template-path')
        if poc_path and os.path.exists(poc_path):
            from dialogs.poc_editor_dialog import POCEditorDialog
            btn_edit = self._create_fortress_button(tr("report.edit_poc"), "info")
            btn_edit.clicked.connect(lambda: POCEditorDialog(poc_path, d).exec_())
            btn_row.addWidget(btn_edit)
        
        # 生成补天报告
        btn_report = self._create_fortress_button(tr("report.generate_report"), "purple")
        btn_report.setToolTip(tr("report.generate_src_tooltip"))
        btn_report.clicked.connect(lambda: self._open_vuln_report_dialog(vuln_data, poc_path))
        btn_row.addWidget(btn_report)
        
        btn_close = self._create_fortress_button(tr("common.close"), "warning")
        btn_close.clicked.connect(d.accept)
        btn_row.addWidget(btn_close)
        
        layout.addLayout(btn_row)
        d.exec_()

    def _copy_vulns_to_clipboard(self, vulns):
        """复制漏洞详情到剪贴板"""
        msg = ""
        for v in vulns:
            msg += f"• [{v.get('severity', 'N/A')}] {v.get('template_id', 'N/A')}\n"
            msg += f"  Target: {v.get('matched_at', 'N/A')}\n"
            if v.get('template_path'):
                msg += f"  POC: {v.get('template_path')}\n"
            msg += "\n"
        
        QApplication.clipboard().setText(msg)
        QMessageBox.information(self, tr("msg.success"), tr("common.copied_to_clipboard"))
    
    def _open_vuln_report_dialog(self, vuln_data, poc_path=None):
        """打开漏洞报告生成对话框"""
        from dialogs.vuln_report_dialog import VulnReportDialog
        dialog = VulnReportDialog(vuln_data, poc_path, self)
        dialog.exec_()
    
    def clear_scan_history(self):
        """清空扫描历史"""
        reply = QMessageBox.warning(
            self, tr("msg.confirm_clear"),
            tr("history.confirm_clear"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            from core.scan_history import get_scan_history
            get_scan_history().clear_history()
            try:
                self.history_manager.clear_scan_history()
            except Exception as e:
                print(f"[WARN] Failed to clear legacy scan history: {e}")
            self.refresh_dashboard()
            QMessageBox.information(self, tr("msg.done"), tr("history.cleared"))
    
    def export_scan_record(self, scan_id):
        """导出单次扫描记录"""
        from core.scan_history import get_scan_history
        from core.export_manager import export_to_csv, export_to_html
        
        # 获取扫描记录和Vulns据
        history = get_scan_history()
        scan_record = history.get_scan_record(scan_id)
        vulns = history.get_scan_vulns(scan_id)
        
        if not scan_record:
            QMessageBox.warning(self, tr("msg.error"), tr("history.record_not_found"))
            return
        
        # 弹出格式选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("export.title"))
        dialog.resize(scaled(350), scaled(150))
        
        from core.fortress_style import apply_fortress_style
        apply_fortress_style(dialog, FORTRESS_COLORS)
        
        layout = QVBoxLayout(dialog)
        
        # 提示信息
        info_label = QLabel(f"Scan time: {scan_record.get('scan_time', '')[:19]}\n" +
                           tr("export.target_count", count=scan_record.get('target_count', 0)) + " | " +
                           tr("export.vuln_count", count=scan_record.get('vuln_count', 0)))
        info_label.setStyleSheet(scaled_style(f"font-size: 12px; color: {FORTRESS_COLORS.get('text_secondary', '#7f8c8d')}; margin-bottom: 10px;"))
        layout.addWidget(info_label)
        
        # 格式选择
        format_label = QLabel(tr("export.select_format"))
        format_label.setStyleSheet(f"color: {FORTRESS_COLORS.get('text_primary', '#333')};")
        layout.addWidget(format_label)
        
        format_combo = QComboBox()
        format_combo.addItems([tr("export.html_recommended"), tr("export.csv_excel")])
        layout.addWidget(format_combo)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = self._create_fortress_button(tr("common.cancel"), "warning")
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_export = self._create_fortress_button(tr("common.export"), "success")
        btn_export.clicked.connect(dialog.accept)
        btn_layout.addWidget(btn_export)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # 获取选择的格式
        is_html = format_combo.currentIndex() == 0
        
        # 选择保存路径
        scan_time_str = scan_record.get('scan_time', '')[:10].replace('-', '')
        default_name = f"scan_report_{scan_time_str}_{scan_id}"
        
        if is_html:
            file_path, _ = QFileDialog.getSaveFileName(
                self, tr("export.save_html"), 
                default_name + ".html",
                "HTML Files (*.html)"
            )
            if file_path:
                if export_to_html(scan_record, vulns, file_path):
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Question)
                    msg_box.setWindowTitle(tr("export.export_success"))
                    msg_box.setText(tr("report.exported_to", filepath=file_path))
                    msg_box.setInformativeText(tr("report.open_now"))
                    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg_box.setDefaultButton(QMessageBox.Yes)
                    msg_box.button(QMessageBox.Yes).setText(tr("common.yes"))
                    msg_box.button(QMessageBox.No).setText(tr("common.no"))
                    reply = msg_box.exec_()
                    if reply == QMessageBox.Yes:
                        import os
                        os.startfile(file_path)
                else:
                    QMessageBox.warning(self, tr("msg.error"), tr("export.failed_permission"))
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self, tr("export.save_csv"), 
                default_name + ".csv",
                "CSV Files (*.csv)"
            )
            if file_path:
                if export_to_csv(scan_record, vulns, file_path):
                    QMessageBox.information(self, tr("msg.success"), f"CSV exported to:\n{file_path}")
                else:
                    QMessageBox.warning(self, tr("msg.error"), tr("export.failed_permission"))

    # ================= POC 管理页面 =================
    def setup_poc_tab(self):
        layout = QVBoxLayout(self.poc_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(scaled(15))

        # ===== 工具栏区域 =====
        toolbar_container = QWidget()
        toolbar_container.setStyleSheet(scaled_style(f"background-color: {FORTRESS_COLORS['content_bg']}; border-radius: 8px;"))
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(scaled(15), scaled(15), scaled(15), scaled(15))
        
        btn_import_file = self._create_fortress_button(tr("poc.import_file"), "info")
        btn_import_file.clicked.connect(self.import_poc_file)
        toolbar_layout.addWidget(btn_import_file)
        
        btn_import_dir = self._create_fortress_button(tr("poc.import_dir"), "info")
        btn_import_dir.clicked.connect(self.import_poc_dir)
        toolbar_layout.addWidget(btn_import_dir)
        
        btn_sync = self._create_fortress_button(tr("poc.online_sync"), "primary")
        btn_sync.setToolTip(tr("poc.sync_tooltip"))
        btn_sync.clicked.connect(self.open_poc_sync_dialog)
        toolbar_layout.addWidget(btn_sync)
        
        btn_generate = self._create_fortress_button(tr("poc.generate"), "warning")
        btn_generate.setToolTip(tr("poc.generate_tooltip"))
        btn_generate.clicked.connect(self.open_poc_generator)
        toolbar_layout.addWidget(btn_generate)
        
        toolbar_layout.addStretch()
        
        btn_edit = self._create_fortress_button(tr("common.edit"), "info")
        btn_edit.clicked.connect(self.open_poc_editor)
        toolbar_layout.addWidget(btn_edit)
        
        btn_test = self._create_fortress_button(tr("poc.quick_test"), "info")
        btn_test.clicked.connect(self.open_poc_test)
        toolbar_layout.addWidget(btn_test)
        
        btn_refresh = self._create_fortress_button(tr("common.refresh"), "info")
        btn_refresh.clicked.connect(self.refresh_poc_list)
        toolbar_layout.addWidget(btn_refresh)
        
        btn_open_folder = self._create_fortress_button(tr("poc.open_folder"), "info")
        btn_open_folder.clicked.connect(lambda: os.startfile(str(self.poc_library.library_path)))
        toolbar_layout.addWidget(btn_open_folder)
        
        layout.addWidget(toolbar_container)
        
        # ===== 搜索和筛选区域 =====
        filter_container = QWidget()
        filter_container.setStyleSheet(scaled_style(f"background-color: {FORTRESS_COLORS['content_bg']}; border-radius: 8px;"))
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(scaled(15), scaled(10), scaled(15), scaled(10))

        self.poc_search_input = QLineEdit()
        self.poc_search_input.setPlaceholderText(tr("poc.search_placeholder"))
        self.poc_search_input.setStyleSheet(scaled_style(f"""
            QLineEdit {{
                border: 1px solid {FORTRESS_COLORS['nav_border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {FORTRESS_COLORS['btn_primary']};
            }}
        """))
        self.poc_search_input.textChanged.connect(self.filter_poc_table)
        filter_layout.addWidget(self.poc_search_input, 1)
        
        # POC 来源分类筛选
        filter_layout.addWidget(QLabel(tr("poc.filter_source")))
        self.poc_source_filter = QComboBox()
        self.poc_source_filter.addItems([tr("common.all"), tr("poc.source_user"), tr("poc.source_cloud"), tr("poc.source_local")])
        self.poc_source_filter.setFixedWidth(scaled(100))
        self.poc_source_filter.currentTextChanged.connect(self.filter_poc_table)
        filter_layout.addWidget(self.poc_source_filter)

        filter_layout.addWidget(QLabel(tr("poc.filter_type")))
        self.poc_type_filter = QComboBox()
        self.poc_type_filter.addItems([tr("common.all"), "RCE", "SQLi", "XSS", "SSRF", "LFI", tr("poc.type_unauth"), tr("poc.type_info_leak"), tr("poc.type_other")])
        self.poc_type_filter.setFixedWidth(scaled(100))
        self.poc_type_filter.currentTextChanged.connect(self.filter_poc_table)
        filter_layout.addWidget(self.poc_type_filter)

        filter_layout.addWidget(QLabel(tr("poc.filter_severity")))
        self.poc_severity_filter = QComboBox()
        self.poc_severity_filter.addItems([tr("common.all"), "critical", "high", "medium", "low", "info"])
        self.poc_severity_filter.setFixedWidth(scaled(100))
        self.poc_severity_filter.currentTextChanged.connect(self.filter_poc_table)
        filter_layout.addWidget(self.poc_severity_filter)

        layout.addWidget(filter_container)

        # ===== POC 列表表格 =====
        table_container = QWidget()
        table_container.setStyleSheet(scaled_style(f"background-color: {FORTRESS_COLORS['content_bg']}; border-radius: 8px;"))
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(scaled(15), scaled(15), scaled(15), scaled(15))
        
        self.poc_table = QTableWidget()
        self.poc_table.setColumnCount(5)
        self.poc_table.setHorizontalHeaderLabels(["ID", tr("poc.col_name"), tr("poc.col_severity"), tr("poc.col_type"), tr("poc.col_source")])
        self.poc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.poc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.poc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.poc_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.poc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.poc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.poc_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.poc_table.setAlternatingRowColors(True)
        self.poc_table.verticalHeader().setVisible(False)
        self.poc_table.doubleClicked.connect(self.on_poc_double_clicked)
        from core.fortress_style import get_table_stylesheet
        self.poc_table.setStyleSheet(get_table_stylesheet(FORTRESS_COLORS))
        
        # 右键菜单
        self.poc_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.poc_table.customContextMenuRequested.connect(self.show_poc_context_menu)
        
        table_layout.addWidget(self.poc_table)
        
        # 提示
        tips = QLabel(tr("poc.tips"))
        tips.setStyleSheet(scaled_style(f"color: {FORTRESS_COLORS['text_secondary']}; font-size: 12px;"))
        table_layout.addWidget(tips)
        
        layout.addWidget(table_container, 1)

    def refresh_poc_list(self):
        """刷新 POC 表格"""
        try:
            self.poc_library.invalidate_cache()
            self.all_poc_data = self.poc_library.get_all_pocs()
            self._render_poc_table(self.all_poc_data)
            
            self.status_bar.showMessage(tr("poc.loaded_count", count=len(self.all_poc_data)))
            # 同步更新扫描页面的列表
            self.update_scan_poc_list(self.all_poc_data)
        except Exception as e:
            QMessageBox.warning(self, tr("poc.refresh_failed"), tr("poc.refresh_error", error=str(e)))
            import traceback
            traceback.print_exc()
    
    def _get_poc_type(self, poc):
        """根据 tags 判断漏洞类型"""
        tags = str(poc.get('tags', '')).lower()
        poc_id = str(poc.get('id', '')).lower()
        name = str(poc.get('name', '')).lower()
        all_text = f"{tags} {poc_id} {name}"
        
        # 按优先级匹配
        if any(k in all_text for k in ['rce', 'remote-code', 'command-execution', 'code-execution']):
            return "RCE"
        elif any(k in all_text for k in ['sqli', 'sql-injection', 'sql_injection']):
            return "SQLi"
        elif any(k in all_text for k in ['xss', 'cross-site-scripting']):
            return "XSS"
        elif any(k in all_text for k in ['ssrf']):
            return "SSRF"
        elif any(k in all_text for k in ['lfi', 'rfi', 'file-inclusion', 'path-traversal', 'file-read']):
            return "LFI"
        elif any(k in all_text for k in ['unauth', 'unauthorized', 'bypass', 'default-login', 'default-password']):
            return tr("poc.type_unauth")
        elif any(k in all_text for k in ['exposure', 'disclosure', 'leak', 'info']):
            return tr("poc.type_info_leak")
        else:
            return tr("poc.type_other")
    
    def _render_poc_table(self, pocs):
        """渲染 POC 表格"""
        self.poc_table.setUpdatesEnabled(False)
        self.poc_table.setRowCount(0)
        self.poc_table.setRowCount(len(pocs))
        
        for row, poc in enumerate(pocs):
            # ID
            id_item = QTableWidgetItem(poc['id'])
            id_item.setData(Qt.UserRole, poc['path'])  # 存储路径
            self.poc_table.setItem(row, 0, id_item)
            
            # 名称
            self.poc_table.setItem(row, 1, QTableWidgetItem(poc['name']))
            
            # 严重程度
            severity_item = QTableWidgetItem(poc['severity'])
            if poc['severity'] == 'critical':
                severity_item.setForeground(QColor('#9b59b6'))
                severity_item.setFont(QFont("Arial", scaled(9), QFont.Bold))
            elif poc['severity'] == 'high':
                severity_item.setForeground(QColor('#e74c3c'))
            elif poc['severity'] == 'medium':
                severity_item.setForeground(QColor('#e67e22'))
            elif poc['severity'] == 'low':
                severity_item.setForeground(QColor('#3498db'))
            self.poc_table.setItem(row, 2, severity_item)
            
            # 类型
            poc_type = self._get_poc_type(poc)
            type_item = QTableWidgetItem(poc_type)
            type_colors = {
                "RCE": "#e74c3c", "SQLi": "#f39c12", "XSS": "#27ae60",
                "SSRF": "#3498db", "LFI": "#9b59b6", "未授权": "#e67e22",
                tr("poc.type_info_leak"): "#1abc9c", tr("poc.type_other"): "#7f8c8d"
            }
            type_item.setForeground(QColor(type_colors.get(poc_type, "#7f8c8d")))
            self.poc_table.setItem(row, 3, type_item)
            
            # 来源（根据路径更准确判断）
            path = poc.get('path', '')
            source = poc.get('source', 'legacy')
            if 'user_generated' in path:
                source_text = tr("poc.source_user_icon")
            elif source == 'cloud':
                source_text = tr("poc.source_cloud_icon")
            elif source == 'custom':
                source_text = tr("poc.source_local_icon")
            else:
                source_text = tr("poc.source_local_icon2")
            self.poc_table.setItem(row, 4, QTableWidgetItem(source_text))
        
        self.poc_table.setUpdatesEnabled(True)
    
    def filter_poc_table(self):
        """筛选 POC 表格 - 增强版，支持来源分类和 CVE 搜索"""
        if not hasattr(self, 'all_poc_data'):
            return
        
        keyword = self.poc_search_input.text().lower().strip()
        type_filter = self.poc_type_filter.currentText()
        severity_filter = self.poc_severity_filter.currentText()
        source_filter = self.poc_source_filter.currentText() if hasattr(self, 'poc_source_filter') else tr("common.all")
        
        # 来源分类映射
        source_mapping = {
            tr("poc.source_user"): lambda p: 'user_generated' in p.get('path', ''),
            tr("poc.source_cloud"): lambda p: p.get('source') == 'cloud',
            tr("poc.source_local"): lambda p: p.get('source') in ['custom', 'legacy'] and 'user_generated' not in p.get('path', ''),
        }
        
        filtered = []
        for poc in self.all_poc_data:
            # 来源分类匹配
            if source_filter != tr("common.all"):
                filter_func = source_mapping.get(source_filter)
                if filter_func and not filter_func(poc):
                    continue
            
            # 关键词匹配（增强版：支持 CVE 编号搜索）
            if keyword:
                search_text = f"{poc['id']} {poc['name']} {poc.get('tags', '')} {poc.get('description', '')}".lower()
                if keyword not in search_text:
                    continue
            
            # 类型匹配
            if type_filter != tr("common.all"):
                poc_type = self._get_poc_type(poc)
                if poc_type != type_filter:
                    continue
            
            # 严重程度匹配
            if severity_filter != tr("common.all"):
                if poc.get('severity', '').lower() != severity_filter.lower():
                    continue
            
            filtered.append(poc)
        
        self._render_poc_table(filtered)
        
        # 更新状态栏显示筛选结果数
        if hasattr(self, 'status_bar'):
            total = len(self.all_poc_data)
            shown = len(filtered)
            if shown < total:
                self.status_bar.showMessage(tr("poc.filtered_count", shown=shown, total=total))
            else:
                self.status_bar.showMessage(tr("poc.total_count", total=total))
    
    def show_poc_context_menu(self, pos):
        """显示右键菜单"""
        from PyQt5.QtWidgets import QMenu
        
        selected_rows = self.poc_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        menu = QMenu(self)
        
        # 应用样式
        from core.fortress_style import get_menu_stylesheet
        menu.setAttribute(Qt.WA_TranslucentBackground) # 配合圆角
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint) # 去除系统边框
        menu.setStyleSheet(get_menu_stylesheet())
        
        add_action = menu.addAction(tr("poc.add_to_scan"))
        add_action.triggered.connect(self.add_selected_pocs_to_scan)
        
        copy_action = menu.addAction(tr("poc.copy_name"))
        copy_action.triggered.connect(self.copy_poc_ids)
        
        menu.addSeparator()
        
        # AI 分析（只对单选有效）
        if len(selected_rows) == 1:
            ai_action = menu.addAction(tr("poc.ai_analyze"))
            ai_action.triggered.connect(self.ai_analyze_poc)
        
        edit_action = menu.addAction(tr("common.edit"))
        edit_action.triggered.connect(self.open_poc_editor)
        
        test_action = menu.addAction(tr("poc.quick_test"))
        test_action.triggered.connect(self.open_poc_test)
        
        menu.addSeparator()
        
        delete_action = menu.addAction(tr("common.delete"))
        delete_action.triggered.connect(self.delete_selected_pocs)
        
        menu.exec_(self.poc_table.viewport().mapToGlobal(pos))
    
    def delete_selected_pocs(self):
        """删除选中的 POC（二次确认）"""
        selected_rows = self.poc_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # 获取选中的 POC 信息
        pocs_to_delete = []
        for index in selected_rows:
            row = index.row()
            item = self.poc_table.item(row, 0)
            if item:
                poc_id = item.text()
                poc_path = item.data(Qt.UserRole)
                if poc_path:
                    pocs_to_delete.append((poc_id, poc_path))
        
        if not pocs_to_delete:
            return
        
        # 二次确认
        msg = f"Confirm delete {len(pocs_to_delete)}  POCs?\n\n"
        msg += "\n".join([f"• {pid}" for pid, _ in pocs_to_delete[:5]])
        if len(pocs_to_delete) > 5:
            msg += f"\n... and {len(pocs_to_delete) - 5}  more"
        msg += "\n\nThis action cannot be undone!"
        
        reply = QMessageBox.warning(
            self, tr("msg.confirm_delete"), msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 执行删除
        deleted = 0
        for poc_id, poc_path in pocs_to_delete:
            if self.poc_library.delete_poc(poc_path):
                deleted += 1
        
        QMessageBox.information(self, tr("msg.done"), tr("poc.deleted_count", count=deleted))
        self.refresh_poc_list()
    
    def add_selected_pocs_to_scan(self):
        """将选中的 POC 添加到扫描列表"""
        selected_rows = self.poc_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # 获取选中的 POC 路径
        poc_paths = []
        for index in selected_rows:
            row = index.row()
            item = self.poc_table.item(row, 0)
            if item:
                path = item.data(Qt.UserRole)
                if path:
                    poc_paths.append(path)
        
        if not poc_paths:
            return
        
        # 将选中的 POC 加入待选队列
        added_count = 0
        for path in poc_paths:
            if path not in self.pending_scan_pocs:
                self.pending_scan_pocs.add(path)
                added_count += 1
        
        # 显示提示信息（状态栏）
        current_total = len(self.pending_scan_pocs)
        added_key = "poc.added_to_queue.single" if added_count == 1 else "poc.added_to_queue.multiple"
        msg = tr(added_key, count=added_count, current_total=current_total)
        self.status_bar.showMessage(msg, 5000)  # 显示 5 秒
        QMessageBox.information(self, tr("msg.success"), msg)
    
    def copy_poc_ids(self):
        """复制选中的 POC 名称"""
        from PyQt5.QtWidgets import QApplication
        
        selected_rows = self.poc_table.selectionModel().selectedRows()
        names = []
        for index in selected_rows:
            row = index.row()
            # 名称在第2列
            item = self.poc_table.item(row, 1)
            if item:
                names.append(item.text())
        
        if names:
            QApplication.clipboard().setText("\n".join(names))
            QMessageBox.information(self, tr("msg.success"), tr("poc.names_copied", count=len(names)))
    
    def ai_analyze_poc(self):
        """AI 分析 POC - 打开 AI 弹窗并预填充 POC 名称到 FOFA 生成框"""
        selected_rows = self.poc_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # 获取 POC 名称（第 2 列）
        row = selected_rows[0].row()
        name_item = self.poc_table.item(row, 1)
        poc_name = name_item.text() if name_item else ""
        
        # 打开 AI 对话框并传入 POC 名称
        dialog = AIAssistantDialog(self, initial_poc_name=poc_name)
        dialog.exec_()

    def import_poc_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr("poc.select_file"), "", "YAML Files (*.yaml *.yml)")
        if file_path:
            result = self.poc_library.import_poc(file_path, auto_sync=True)
            if result['success']:
                QMessageBox.information(self, tr("msg.success"), tr("poc.import_success", name=result['name']))
                self.refresh_poc_list()
            else:
                QMessageBox.warning(self, tr("msg.failure"), tr("poc.import_failed", error=result['error']))

    def import_poc_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, tr("poc.select_dir"))
        if dir_path:
            count = 0
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if file.endswith(('.yaml', '.yml')):
                        full_path = os.path.join(root, file)
                        if self.poc_library.import_poc(full_path, auto_sync=True)['success']:
                            count += 1
            QMessageBox.information(self, tr("msg.done"), tr("poc.batch_import_done", count=count))
            self.refresh_poc_list()
    
    def open_poc_sync_dialog(self):
        """打开 POC 在线同步弹窗"""
        from dialogs.poc_sync_dialog import POCSyncDialog
        # 同步到 cloud 目录
        dialog = POCSyncDialog(str(self.poc_library.cloud_path), self, colors=FORTRESS_COLORS)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_poc_list()
    
    def open_poc_editor(self):
        """打开 POC 编辑器"""
        from dialogs.poc_editor_dialog import POCEditorDialog
        
        # 获取选中的 POC
        selected_rows = self.poc_table.selectionModel().selectedRows()
        poc_path = None
        if selected_rows:
            row = selected_rows[0].row()
            item = self.poc_table.item(row, 0)
            if item:
                poc_path = item.data(Qt.UserRole)  # 从 UserRole 获取路径
        
        dialog = POCEditorDialog(poc_path, self, colors=FORTRESS_COLORS)
        dialog.exec_()
    
    def open_poc_test(self):
        """打开 POC 快速测试弹窗"""
        from dialogs.poc_test_dialog import POCTestDialog
        
        # 获取选中的 POC
        selected_rows = self.poc_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, tr("msg.hint"), tr("poc.select_poc_first"))
            return
        
        row = selected_rows[0].row()
        item = self.poc_table.item(row, 0)
        poc_path = item.data(Qt.UserRole) if item else None  # 从 UserRole 获取路径
        poc_name = item.text() if item else ""
        
        dialog = POCTestDialog(poc_path, poc_name, self, colors=FORTRESS_COLORS)
        dialog.exec_()
    
    def open_poc_generator(self):
        """打开 POC 生成器"""
        from dialogs.poc_generator_dialog import POCGeneratorDialog
        
        dialog = POCGeneratorDialog(self, colors=FORTRESS_COLORS)
        if dialog.exec_() == QDialog.Accepted:
            # 刷新 POC 列表以显示新生成的 POC
            self.refresh_poc_list()
    
    def on_poc_double_clicked(self, index):
        """双击 POC 打开编辑器"""
        row = index.row()
        item = self.poc_table.item(row, 0)
        poc_path = item.data(Qt.UserRole) if item else None  # 从 UserRole 获取路径
        
        from dialogs.poc_editor_dialog import POCEditorDialog
        dialog = POCEditorDialog(poc_path, self, colors=FORTRESS_COLORS)
        dialog.exec_()

    # ================= 扫描任务页面 =================
    def setup_scan_tab(self):
        """设置扫描结果页面 - FORTRESS 风格"""
        layout = QVBoxLayout(self.scan_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(scaled(15))
        
        # ===== 顶部操作栏 =====
        action_bar = QWidget()
        action_bar.setStyleSheet(scaled_style(f"""
            QWidget {{
                background-color: {FORTRESS_COLORS['content_bg']};
                border-radius: 8px;
            }}
        """))
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(scaled(15), scaled(12), scaled(15), scaled(12))
        
        # 快捷新建扫描按钮
        btn_quick_scan = self._create_fortress_button(tr("scan.new_scan"), "primary")
        btn_quick_scan.clicked.connect(self.show_new_scan_dialog)
        action_layout.addWidget(btn_quick_scan)
        
        # 导出结果按钮
        btn_export = self._create_fortress_button(tr("scan.export_results"), "info")
        btn_export.clicked.connect(self.export_results)
        action_layout.addWidget(btn_export)
        
        # 查看日志按钮
        btn_log = self._create_fortress_button(tr("scan.view_log"), "info")
        btn_log.clicked.connect(self.show_log_dialog)
        action_layout.addWidget(btn_log)
        
        action_layout.addStretch()

        # 进度区域
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v/%m (%p%)")
        self.progress_bar.setMinimumWidth(scaled(200))
        self.progress_bar.setMaximumWidth(scaled(300))
        self.progress_bar.setStyleSheet(scaled_style(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: #e5e7eb;
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {FORTRESS_COLORS['btn_primary']};
                border-radius: 4px;
            }}
        """))
        self.progress_bar.hide()
        action_layout.addWidget(self.progress_bar)

        self.lbl_progress = QLabel(tr("status.ready_simple"))
        self.lbl_progress.setStyleSheet(scaled_style(f"""
            font-weight: bold;
            color: {FORTRESS_COLORS['text_secondary']};
            font-size: 13px;
        """))
        self.lbl_progress.setMinimumWidth(scaled(130))
        self.lbl_progress.setMaximumWidth(scaled(190))
        self.lbl_progress.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        action_layout.addWidget(self.lbl_progress)

        # 开始/停止按钮
        self.btn_start = self._create_fortress_button(tr("scan.start_scan"), "primary")
        self.btn_start.clicked.connect(self.start_scan)
        action_layout.addWidget(self.btn_start)

        # 暂停/继续按钮
        self.btn_pause = self._create_fortress_button(tr("task.pause"), "info")
        self.btn_pause.clicked.connect(self.pause_scan)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setToolTip(tr("scan.pause_tooltip"))
        action_layout.addWidget(self.btn_pause)

        self.btn_stop = self._create_fortress_button(tr("scan.stop_scan"), "warning")
        self.btn_stop.clicked.connect(self.stop_scan)
        self.btn_stop.setEnabled(False)
        action_layout.addWidget(self.btn_stop)

        layout.addWidget(action_bar)

        # ===== 实时扫描统计面板 =====
        stats_panel = QWidget()
        stats_panel.setStyleSheet(scaled_style(f"""
            QWidget {{
                background-color: {FORTRESS_COLORS['content_bg']};
                border-radius: 8px;
            }}
        """))
        stats_layout = QHBoxLayout(stats_panel)
        stats_layout.setContentsMargins(scaled(15), scaled(10), scaled(15), scaled(10))
        stats_layout.setSpacing(scaled(20))
        
        # 统计卡片
        self.scan_stat_targets = self._create_scan_stat_card(tr("scan.stat_targets"), "0", "#3b82f6")
        self.scan_stat_pocs = self._create_scan_stat_card(tr("scan.stat_pocs"), "0", "#8b5cf6")
        self.scan_stat_vulns = self._create_scan_stat_card(tr("scan.stat_vulns"), "0", "#ef4444")
        self.scan_stat_critical = self._create_scan_stat_card(tr("severity.critical"), "0", "#9b59b6")
        self.scan_stat_high = self._create_scan_stat_card(tr("severity.high"), "0", "#e74c3c")
        self.scan_stat_medium = self._create_scan_stat_card(tr("severity.medium"), "0", "#f97316")
        self.scan_stat_low = self._create_scan_stat_card(tr("severity.low"), "0", "#3b82f6")
        
        stats_layout.addWidget(self.scan_stat_targets)
        stats_layout.addWidget(self.scan_stat_pocs)
        stats_layout.addWidget(self.scan_stat_vulns)
        stats_layout.addWidget(self.scan_stat_critical)
        stats_layout.addWidget(self.scan_stat_high)
        stats_layout.addWidget(self.scan_stat_medium)
        stats_layout.addWidget(self.scan_stat_low)
        stats_layout.addStretch()
        
        layout.addWidget(stats_panel)
        
        # ===== 隐藏的配置区域（用于保存目标和 POC 数据）=====
        self._setup_hidden_scan_config()
        
        # ===== 结果表格 =====
        table_container = QWidget()
        table_container.setStyleSheet(scaled_style(f"""
            QWidget {{
                background-color: {FORTRESS_COLORS['content_bg']};
                border-radius: 8px;
            }}
        """))
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels([tr("scan.col_status"), tr("scan.col_vuln_name"), tr("scan.col_severity"), tr("scan.col_target"), tr("scan.col_found_time"), tr("scan.col_action")])

        # 设置表格样式 - FORTRESS 风格
        from core.fortress_style import get_table_stylesheet
        self.result_table.setStyleSheet(get_table_stylesheet(FORTRESS_COLORS))

        # 设置列宽
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 状态列
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 漏洞名称
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 严重程度
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 目标
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 发现时间
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.result_table.setColumnWidth(5, scaled(184))  # 操作列 - 预留两个按钮和间距，避免挤压
        self.result_table.verticalHeader().setDefaultSectionSize(scaled(50)) # 再次增加默认行高
        
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setToolTip(tr("scan.double_click_tooltip"))
        self.result_table.doubleClicked.connect(self.show_result_detail)
        
        # 设置交替行颜色
        palette = self.result_table.palette()
        palette.setColor(palette.AlternateBase, QColor(FORTRESS_COLORS['table_row_alt']))
        self.result_table.setPalette(palette)
        
        table_layout.addWidget(self.result_table)
        layout.addWidget(table_container, 1)
        
        # 存储完整结果数据
        self.scan_results_data = []
        
        # ===== 日志区域 =====
        log_container = QWidget()
        log_container.setMaximumHeight(scaled(150))
        log_container.setStyleSheet(scaled_style(f"""
            QWidget {{
                background-color: {FORTRESS_COLORS['content_bg']};
                border-radius: 8px;
            }}
        """))
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(scaled(10), scaled(10), scaled(10), scaled(10))

        log_header = QLabel(tr("scan.scan_log"))
        log_header.setStyleSheet(scaled_style(f"font-weight: bold; color: {FORTRESS_COLORS['text_secondary']}; font-size: 12px;"))
        log_layout.addWidget(log_header)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(scaled_style(f"""
            QTextEdit {{
                background-color: #1e293b;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 11px;
                padding: 8px;
            }}
        """))
        log_layout.addWidget(self.log_output)

        layout.addWidget(log_container)
        
        # 完整日志存储
        self.full_log = []
    
    def _setup_hidden_scan_config(self):
        """设置隐藏的扫描配置组件（用于数据存储）"""
        # 目标输入（隐藏）
        self.txt_targets = PlainPasteTextEdit()
        self.txt_targets.hide()
        
        # POC 列表（隐藏）
        self.list_scan_pocs = QTableWidget()
        self.list_scan_pocs.setColumnCount(4)
        self.list_scan_pocs.hide()
        
        # 搜索和筛选组件（隐藏）
        self.txt_search_poc = QLineEdit()
        self.txt_search_poc.hide()
        
        self.cmb_severity_filter = QComboBox()
        self.cmb_severity_filter.addItems([tr("common.all"), "critical", "high", "medium", "low", "info"])
        self.cmb_severity_filter.hide()
        
        # Selected按钮（隐藏）
        self.btn_selected_pocs = QPushButton()
        self.btn_selected_pocs.hide()
    
    def load_scan_config(self):
        """从设置管理器加载扫描参数（供其他地方调用）"""
        # UI 组件已移除，此方法保留用于兼容性
        pass

    def export_results(self):
        """导出扫描结果"""
        row_count = self.result_table.rowCount()
        if row_count == 0:
            QMessageBox.warning(self, tr("msg.hint"), tr("scan.no_results_to_export"))
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, tr("scan.save_results"), "scan_results.csv", "CSV Files (*.csv);;JSON Files (*.json)")
        if not file_path:
            return
            
        try:
            import csv
            
            # 收集数据
            data = []
            headers = [tr("scan.col_time"), tr("scan.col_vuln_id"), tr("scan.col_target"), tr("scan.col_severity"), tr("scan.col_details")]
            
            for i in range(row_count):
                row_data = []
                for j in range(5):
                    item = self.result_table.item(i, j)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            if file_path.endswith('.csv'):
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(data)
                    
            elif file_path.endswith('.json'):
                import json
                json_data = []
                for row in data:
                    json_data.append(dict(zip(headers, row)))
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                    
            QMessageBox.information(self, tr("msg.success"), f"Results saved to:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, tr("msg.error"), tr("export.failed", error=str(e)))


    def import_targets_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr("scan.select_target_file"), "", "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 简单的追加还是覆盖？这里选择追加，体验更好
                    current_text = self.txt_targets.toPlainText()
                    targets = parse_targets_text(current_text + "\n" + content)
                    self.txt_targets.setPlainText("\n".join(targets))
                QMessageBox.information(self, tr("msg.success"), tr("scan.targets_imported", file=os.path.basename(file_path)))
            except Exception as e:
                QMessageBox.warning(self, tr("msg.failure"), tr("scan.read_file_failed", error=str(e)))

    def update_scan_poc_list(self, pocs):
        """更新扫描页面的 POC 选择列表"""
        self.all_scan_pocs = pocs # 保存完整列表供搜索使用
        self.filter_scan_poc_list()
        
    def filter_scan_poc_list(self):
        """根据搜索框和严重级别过滤 POC"""
        keyword = self.txt_search_poc.text().lower()
        severity_filter = self.cmb_severity_filter.currentText()
        
        if not hasattr(self, 'all_scan_pocs'):
            return
        
        # 先过滤数据
        filtered_pocs = []
        for poc in self.all_scan_pocs:
            # 关键词匹配
            if keyword:
                keywords = keyword.split()
                search_text = f"{poc['id']} {poc['name']} {poc.get('tags', '')} {poc.get('description', '')}".lower()
                if not all(kw in search_text for kw in keywords):
                    continue
            
            # 严重级别匹配
            if severity_filter != tr("common.all") and poc.get('severity', '').lower() != severity_filter.lower():
                continue
            
            filtered_pocs.append(poc)
        
        # 暂停界面更新和信号，提升性能
        self.list_scan_pocs.blockSignals(True)
        self.list_scan_pocs.setUpdatesEnabled(False)
        self.list_scan_pocs.setRowCount(0)
        self.list_scan_pocs.setRowCount(len(filtered_pocs))
        
        for row, poc in enumerate(filtered_pocs):
            # 复选框
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Unchecked)
            chk_item.setData(Qt.UserRole, poc['path'])
            
            self.list_scan_pocs.setItem(row, 0, chk_item)
            self.list_scan_pocs.setItem(row, 1, QTableWidgetItem(poc['id']))
            self.list_scan_pocs.setItem(row, 2, QTableWidgetItem(poc['name']))
            
            # 严重级别 (带颜色)
            severity = poc.get('severity', 'unknown')
            severity_item = QTableWidgetItem(severity)
            if severity == 'critical':
                severity_item.setForeground(QColor('#9b59b6'))
            elif severity == 'high':
                severity_item.setForeground(QColor('#e74c3c'))
            elif severity == 'medium':
                severity_item.setForeground(QColor('#e67e22'))
            elif severity == 'low':
                severity_item.setForeground(QColor('#3498db'))
            self.list_scan_pocs.setItem(row, 3, severity_item)
        
        # 恢复界面更新和信号
        self.list_scan_pocs.setUpdatesEnabled(True)
        self.list_scan_pocs.blockSignals(False)
        
        # 更新Selected按钮文本
        if hasattr(self, 'btn_selected_pocs'):
            count = len(self.get_selected_pocs())
            self.btn_selected_pocs.setText(f"📋 Selected ({count})")

    def toggle_select_all_pocs(self):
        """全选/反选"""
        count = self.list_scan_pocs.rowCount()
        if count == 0: return
        
        # 检查第一个是否选中，决定全选还是全不选
        first_state = self.list_scan_pocs.item(0, 0).checkState()
        new_state = Qt.Unchecked if first_state == Qt.Checked else Qt.Checked
        
        for i in range(count):
            self.list_scan_pocs.item(i, 0).setCheckState(new_state)

    def get_selected_pocs(self):
        """获取选中的 POC 路径"""
        selected_pocs = []
        for i in range(self.list_scan_pocs.rowCount()):
            item = self.list_scan_pocs.item(i, 0)
            if item.checkState() == Qt.Checked:
                path = item.data(Qt.UserRole)
                selected_pocs.append(path)
        return selected_pocs
    
    def on_poc_selection_changed(self, item):
        """POC 选择变化时更新按钮文本"""
        if item.column() == 0:  # 只响应复选框列的变化
            if hasattr(self, 'btn_selected_pocs'):
                count = len(self.get_selected_pocs())
                self.btn_selected_pocs.setText(f"📋 Selected ({count})")
    
    def show_selected_pocs_dialog(self):
        """显示Selected的 POC 弹窗"""
        selected = []
        for i in range(self.list_scan_pocs.rowCount()):
            item = self.list_scan_pocs.item(i, 0)
            if item and item.checkState() == Qt.Checked:
                poc_id = self.list_scan_pocs.item(i, 1).text() if self.list_scan_pocs.item(i, 1) else ""
                poc_name = self.list_scan_pocs.item(i, 2).text() if self.list_scan_pocs.item(i, 2) else ""
                poc_path = item.data(Qt.UserRole)
                selected.append({'id': poc_id, 'name': poc_name, 'path': poc_path, 'row': i})
        
        if not selected:
            QMessageBox.information(self, tr("msg.hint"), tr("poc.no_poc_selected"))
            return
        
        # 创建弹窗
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("poc.selected_pocs_title", count=len(selected)))
        dialog.resize(scaled(600), scaled(400))
        
        layout = QVBoxLayout(dialog)
        
        # 提示
        lbl_hint = QLabel("💡 Uncheck to remove POC from scan list")
        lbl_hint.setStyleSheet("color: #3498db; font-weight: bold;")
        layout.addWidget(lbl_hint)
        
        # POC 列表
        poc_list = QTableWidget()
        poc_list.setColumnCount(3)
        poc_list.setHorizontalHeaderLabels(["✓", "ID", tr("poc.col_name")])
        poc_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        poc_list.setColumnWidth(0, scaled(30))
        poc_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        poc_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        poc_list.setRowCount(len(selected))
        poc_list.verticalHeader().setVisible(False)
        
        for row, poc in enumerate(selected):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked)
            chk_item.setData(Qt.UserRole, poc['row'])  # 存储原始行号
            
            poc_list.setItem(row, 0, chk_item)
            poc_list.setItem(row, 1, QTableWidgetItem(poc['id']))
            poc_list.setItem(row, 2, QTableWidgetItem(poc['name']))
        
        layout.addWidget(poc_list)
        
        # 按钮行
        btn_row = QHBoxLayout()
        
        btn_uncheck_all = QPushButton(tr("common.uncheck_all"))
        btn_uncheck_all.clicked.connect(lambda: self._set_all_check_state(poc_list, Qt.Unchecked))
        btn_row.addWidget(btn_uncheck_all)
        
        btn_row.addStretch()
        
        btn_apply = QPushButton(tr("common.apply"))
        btn_apply.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        btn_apply.clicked.connect(lambda: self._apply_selected_changes(poc_list, dialog))
        btn_row.addWidget(btn_apply)
        
        btn_cancel = QPushButton(tr("common.cancel"))
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_cancel)
        
        layout.addLayout(btn_row)
        
        dialog.exec_()
    
    def _set_all_check_state(self, table, state):
        """设置表格所有复选框状态"""
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            if item:
                item.setCheckState(state)
    
    def _apply_selected_changes(self, poc_list, dialog):
        """应用Selected POC 的更改"""
        # 遍历弹窗列表，同步到主列表
        for i in range(poc_list.rowCount()):
            item = poc_list.item(i, 0)
            if item:
                original_row = item.data(Qt.UserRole)
                new_state = item.checkState()
                # 更新主列表对应行的选中状态
                main_item = self.list_scan_pocs.item(original_row, 0)
                if main_item:
                    main_item.setCheckState(new_state)
        
        # 更新按钮文本
        count = len(self.get_selected_pocs())
        self.btn_selected_pocs.setText(f"📋 Selected ({count})")
        
        dialog.accept()

    def start_scan(self, targets: list = None, templates: list = None):
        """开始扫描任务
        Args:
            targets: Optional, 目标列表
            templates: Optional, POC 路径列表
        """
        # 修复: 按钮点击信号会传递 boolean 值，导致 targets 变成 True/False
        # 如果是 bool 类型，视为 None (即从 UI 获取目标)
        if isinstance(targets, bool):
            targets = None
            
        # 1. 获取目标
        if targets is None:
            raw_targets = self.txt_targets.toPlainText().strip()
            if not raw_targets:
                QMessageBox.warning(self, tr("msg.hint"), tr("scan.enter_targets_first"))
                return
            targets = parse_targets_text(raw_targets)
        else:
            targets = dedupe_targets(targets)

        if not targets:
            QMessageBox.warning(self, tr("msg.hint"), tr("scan.enter_targets_first"))
            return
        
        # 2. 获取 POC
        if templates is None:
            templates = self.get_selected_pocs()
            
        if not templates:
            QMessageBox.warning(self, tr("msg.hint"), tr("scan.select_poc_first"))
            return
        
        # 3. 从设置管理器获取扫描参数
        settings = get_settings()
        scan_config = settings.get_scan_config()
        
        # 构建自定义参数
        custom_args = []
        
        # 超时
        custom_args.extend(["-timeout", str(scan_config.get("timeout", 5))])
        # 重试
        custom_args.extend(["-retries", str(scan_config.get("retries", 0))])
        # 跟随重定向
        if scan_config.get("follow_redirects", False):
            custom_args.append("-fr")
        # 发现即停
        if scan_config.get("stop_at_first_match", False):
            custom_args.append("-stop-at-first-match")
        # 代理
        proxy = scan_config.get("proxy", "")
        if proxy:
            custom_args.extend(["-proxy", proxy])
        # 详细模式
        if scan_config.get("verbose", False):
            custom_args.append("-v")
        # 跳过 httpx 探测
        if scan_config.get("no_httpx", False):
            custom_args.append("-nh")
            
        use_native = scan_config.get("use_native_scanner", False)
            
        # 4. 锁定 UI
        self.btn_start.setEnabled(False)
        self.btn_start.setText(tr("scan.scanning"))
        self.btn_stop.setEnabled(True)
        self.btn_pause.setEnabled(True)  # 启用暂停按钮
        self.btn_pause.setText(tr("task.pause"))
        self.progress_bar.setRange(0, 100)  # 设置确定模式
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        engine_name = tr("scan.engine_native") if use_native else tr("scan.engine_nuclei")
        self.lbl_progress.setText(tr("scan.starting_engine", engine=engine_name, count=len(targets)))
        self.result_table.setRowCount(0)
        self.log_output.clear()
        self.full_log = []  # 清空完整日志
        self.scan_results_data = []  # 清空结果数据
        
        # 更新统计面板
        self._update_scan_stats(targets=len(targets), pocs=len(templates), vulns=[])
        
        # 记录开始时间和扫描配置（用于保存历史）
        import time
        self.scan_start_time = time.time()
        self.current_scan_targets = targets
        self.current_scan_templates = templates
        self.current_scan_config = scan_config
        
        # 5. 注册任务到任务队列（以便在任务管理页面显示）
        from core.task_queue_manager import get_task_queue_manager, TaskStatus
        import uuid
        self.current_task_id = str(uuid.uuid4())[:8]
        queue = get_task_queue_manager()
        queue.register_external_task(
            task_id=self.current_task_id,
            name=tr("task.scan_task_name", targets=len(targets), pocs=len(templates)),
            targets=targets,
            templates=templates,
            status=TaskStatus.RUNNING
        )
        
        # 6. 启动线程
        limit = scan_config.get("rate_limit", 150)
        bulk = scan_config.get("bulk_size", 25)
        
        self.scan_thread = NucleiScanThread(targets, templates, limit, bulk, custom_args, use_native_scanner=use_native, oast_config=scan_config)
        self.scan_thread.log_signal.connect(self.append_log)
        self.scan_thread.result_signal.connect(self.add_scan_result)
        self.scan_thread.finished_signal.connect(self.scan_finished)
        self.scan_thread.progress_signal.connect(self.update_progress)
        self.scan_thread.start()

    def update_progress(self, current, total, description):
        """更新进度条"""
        if total > 0:
            # 防止进度回跳：只有当新进度大于等于当前进度时才更新
            current_value = self.progress_bar.value()
            new_value = int(current * 100 / total) if total != 100 else current

            # 允许进度前进，或者从0开始
            if new_value >= current_value or current_value == 0:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(new_value)

            result_count = self.result_table.rowCount()
            self.lbl_progress.setText(tr("scan.progress_detail", result_count=result_count))

            # 同步更新任务队列中的进度
            if hasattr(self, 'current_task_id'):
                from core.task_queue_manager import get_task_queue_manager
                queue = get_task_queue_manager()
                queue.update_task_progress(self.current_task_id, self.progress_bar.value(), result_count)

    def append_log(self, text):
        self.log_output.append(text)
        self.full_log.append(text)  # 存储完整日志

    def add_scan_result(self, result):
        """添加扫描结果到表格 - FORTRESS 风格"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        timestamp = result.get('timestamp', '')
        template_id = result.get('template-id', '')
        matched_at = result.get('matched-at', '')
        info = result.get('info', {})
        severity = info.get('severity', 'unknown')
        vuln_name = info.get('name', template_id)
        
        # 列 0: 状态圆点（使用特殊字符模拟）
        status_item = QTableWidgetItem("●")
        status_item.setTextAlignment(Qt.AlignCenter)
        # 根据严重程度设置颜色
        status_colors = {
            'critical': FORTRESS_COLORS['status_critical'],
            'high': FORTRESS_COLORS['status_medium'],  # 橙色
            'medium': FORTRESS_COLORS['status_medium'],
            'low': FORTRESS_COLORS['status_high'],  # 蓝色
            'info': FORTRESS_COLORS['status_low'],  # 绿色
        }
        status_item.setForeground(QColor(status_colors.get(severity, '#6b7280')))
        status_item.setFont(QFont("Arial", scaled(16)))
        self.result_table.setItem(row, 0, status_item)
        
        # 列 1: 漏洞名称
        name_item = QTableWidgetItem(vuln_name)
        name_item.setToolTip(f"ID: {template_id}\n{info.get('description', '')}")
        self.result_table.setItem(row, 1, name_item)
        
        # 列 2: 严重程度
        severity_item = QTableWidgetItem(display_severity(severity))
        severity_item.setTextAlignment(Qt.AlignCenter)
        self.result_table.setItem(row, 2, severity_item)
        
        # 列 3: 目标
        target_item = QTableWidgetItem(matched_at)
        target_item.setToolTip(matched_at)
        self.result_table.setItem(row, 3, target_item)
        
        # 列 4: 发现时间（简化格式）
        time_display = timestamp[11:19] if len(timestamp) > 19 else timestamp  # 只显示时间部分
        self.result_table.setItem(row, 4, QTableWidgetItem(time_display))
        
        # 列 5: 操作按钮 - 使用容器居中对齐
        from core.fortress_style import get_table_button_style
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        action_button_width = scaled(62)
        action_button_height = scaled(26)
        btn_container.setMinimumWidth(scaled(146))

        btn_layout.setContentsMargins(scaled(3), scaled(6), scaled(3), scaled(6))
        btn_layout.setSpacing(scaled(8))
        btn_layout.setAlignment(Qt.AlignCenter)

        btn_view = QPushButton(tr("common.view"))
        btn_view.setStyleSheet(get_table_button_style('info', FORTRESS_COLORS, 62))
        btn_view.setMinimumWidth(action_button_width)
        btn_view.setFixedHeight(action_button_height)
        btn_view.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn_view.setCursor(Qt.PointingHandCursor)
        btn_view.clicked.connect(lambda checked, idx=row: self._show_result_detail_by_row(idx))
        btn_layout.addWidget(btn_view)

        btn_report = QPushButton(tr("common.report"))
        btn_report.setStyleSheet(get_table_button_style('primary', FORTRESS_COLORS, 62))
        btn_report.setMinimumWidth(action_button_width)
        btn_report.setFixedHeight(action_button_height)
        btn_report.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        btn_report.setCursor(Qt.PointingHandCursor)
        btn_report.clicked.connect(lambda checked, idx=row: self._generate_vuln_report_by_row(idx))
        btn_layout.addWidget(btn_report)

        self.result_table.setCellWidget(row, 5, btn_container)
        self.result_table.setRowHeight(row, scaled(50))

        # 存储完整结果数据用于详情查看
        self.scan_results_data.append(result)

        # 实时更新统计卡片
        self._update_scan_stats(vulns=self.scan_results_data)

        # 实时更新仪表盘Vulns量卡片
        self._update_dashboard_vuln_count_realtime()

        # 更新进度标签和状态指示器
        self.lbl_progress.setText(tr("scan.found_vulns", count=row + 1))
        self.status_indicator.setText(tr("status.scanning_count", count=row + 1))
        self.status_indicator.setStyleSheet(scaled_style(f"""
            color: {FORTRESS_COLORS['btn_warning']};
            font-size: 13px;
            padding: 5px 12px;
            background-color: #fff7ed;
            border-radius: 12px;
        """))
    
    def _show_result_detail_by_row(self, row):
        """通过行号显示结果详情"""
        if row >= 0 and row < len(self.scan_results_data):
            result = self.scan_results_data[row]
            self._show_scan_result_detail(result)

    def _generate_vuln_report_by_row(self, row):
        """通过行号生成单条漏洞的 AI 报告"""
        from dialogs.ai_vuln_report_dialog import AIVulnReportDialog

        if row < 0 or row >= len(self.scan_results_data):
            return

        result = self.scan_results_data[row]
        template_id = result.get("template-id", result.get("templateID", "Unknown"))
        matched_at = result.get("matched-at", result.get("matched", "Unknown"))
        severity = result.get("info", {}).get("severity", "unknown")
        name = result.get("info", {}).get("name", template_id)
        description = result.get("info", {}).get("description", "")

        # 构建漏洞信息
        vuln_info = f"""Vulnerability: {name}
Vuln ID: {template_id}
Severity: {severity}
Target: {matched_at}
Description: {description}"""

        # 打开 AI 报告生成对话框
        dialog = AIVulnReportDialog(self, vuln_info, result, FORTRESS_COLORS)
        dialog.exec_()

    def _on_task_status_changed(self, task_id, status_value):
        """处理任务状态变更"""
        from core.task_queue_manager import TaskStatus

        self.append_log(f"[DEBUG] _on_task_status_changed: task={task_id}, status={status_value}")

        # 刷新任务列表
        self._refresh_task_list()

        # 如果是当前运行的任务
        if hasattr(self, 'current_task_id') and self.current_task_id == task_id:
            # 如果任务完成、取消或失败，同步 UI 状态
            if status_value in [TaskStatus.CANCELLED.value, TaskStatus.FAILED.value, TaskStatus.COMPLETED.value]:
                self.append_log(f"[DEBUG] Task status changed to: {status_value}, calling scan_finished")
                finish_status = "stopped" if status_value == TaskStatus.CANCELLED.value else status_value
                self.scan_finished(status=finish_status)

            # 对于 Cancelled 状态，还需要确保 worker 停止（双重保障）
            if status_value == TaskStatus.CANCELLED.value:
                if hasattr(self, 'scan_thread') and self.scan_thread and self.scan_thread.isRunning():
                    self.scan_thread.stop()
            return

        if status_value == TaskStatus.COMPLETED.value:
            task = self.task_queue.get_task(task_id)
            if not task:
                return
                
            # 计算耗时
            duration = 0
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
            
            # 保存到扫描历史
            self._save_scan_history("completed", duration, task.result_count, task_results=task.results)
            
            self.statusBar().showMessage(tr("task.completed_msg", name=task.name, count=task.vuln_count), 5000)

    def _save_scan_history(self, status, duration, result_count, task_results=None):
        """保存扫描历史记录到仪表盘数据库"""
        # 修复：使用 ScanHistory 类（与仪表盘一致），而非 HistoryManager
        from core.scan_history import get_scan_history
        
        # 如果没有提供 explicit results，尝试使用当前扫描结果
        results_to_save = task_results
        if results_to_save is None and hasattr(self, 'scan_results_data'):
             results_to_save = self.scan_results_data
        if results_to_save is None:
            results_to_save = []
            
        # 获取目标和 POC 信息
        targets = []
        templates = []
        config = {}
        
        # 情况1: 尝试从直接扫描的属性获取
        if hasattr(self, 'current_scan_targets') and self.current_scan_targets:
            targets = self.current_scan_targets
        if hasattr(self, 'current_scan_templates') and self.current_scan_templates:
            templates = self.current_scan_templates
        if hasattr(self, 'current_scan_config') and self.current_scan_config:
            config = self.current_scan_config
        
        # 情况2: 如果上面没有数据，尝试从任务队列获取（任务列表启动的扫描）
        if (not targets or not templates) and hasattr(self, 'current_task_id') and self.current_task_id:
            from core.task_queue_manager import get_task_queue_manager
            queue = get_task_queue_manager()
            task = queue.get_task(self.current_task_id)
            if task:
                if not targets and task.targets:
                    targets = task.targets
                if not templates and task.templates:
                    templates = task.templates

        target_count = len(targets) if targets else 0
        poc_count = len(templates) if templates else 0
        
        try:
            history_mgr = get_scan_history()
            
            # 添加扫描记录
            scan_id = history_mgr.add_scan_record(
                target_count=target_count,
                poc_count=poc_count,
                vuln_count=result_count,
                duration=duration,
                targets=targets,
                pocs=templates,
                config=config,
                status=status
            )
            
            # 保存每个漏洞结果详情
            for result in results_to_save:
                history_mgr.add_vuln_result(scan_id, result)
                
            print(f"[ScanHistory] Saved scan record (ID: {scan_id}, status: {status}, vulns: {result_count})")
            
        except Exception as e:
            print(f"Save scan history failed: {e}")
            
        # 刷新仪表盘
        if hasattr(self, 'refresh_dashboard'):
            self.refresh_dashboard()
    
    def _show_scan_result_detail(self, result):
        """显示扫描结果详情 - FORTRESS 风格"""
        import json
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("report.vuln_detail", id=result.get('template-id', 'Unknown')))
        dialog.resize(scaled(800), scaled(600))
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {FORTRESS_COLORS['content_bg']};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(scaled(15))
        layout.setContentsMargins(scaled(20), scaled(20), scaled(20), scaled(20))

        # 标题
        info = result.get('info', {})
        severity = info.get('severity', 'unknown')
        title = QLabel(f"{info.get('name', result.get('template-id', 'Unknown'))}")
        title.setStyleSheet(scaled_style(f"""
            font-size: 18px;
            font-weight: bold;
            color: {FORTRESS_COLORS['text_primary']};
        """))
        layout.addWidget(title)

        # 严重程度标签
        sev_label = QLabel(display_severity(severity))
        sev_colors = {
            'critical': ('#ef4444', '#fef2f2'),
            'high': ('#f97316', '#fff7ed'),
            'medium': ('#eab308', '#fefce8'),
            'low': ('#3b82f6', '#eff6ff'),
            'info': ('#22c55e', '#f0fdf4'),
        }
        fg, bg = sev_colors.get(severity, ('#6b7280', '#f9fafb'))
        sev_label.setStyleSheet(scaled_style(f"""
            background-color: {bg};
            color: {fg};
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
        """))
        sev_label.setMaximumWidth(scaled(100))
        layout.addWidget(sev_label)

        # 基本信息
        info_container = QWidget()
        # 根据主题自动调整背景色
        info_bg = FORTRESS_COLORS.get('nav_border', '#2c3e50')  # 深色背景
        info_container.setStyleSheet(scaled_style(f"background-color: {info_bg}; border-radius: 8px;"))
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(scaled(15), scaled(15), scaled(15), scaled(15))
        
        fields = [
            (tr("scan.detail_target"), result.get('matched-at', 'N/A')),
            (tr("scan.detail_template_id"), result.get('template-id', 'N/A')),
            (tr("scan.detail_found_time"), result.get('timestamp', 'N/A')),
            (tr("scan.detail_description"), info.get('description', 'N/A')),
        ]
        
        for label, value in fields:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(scaled_style(f"font-weight: bold; color: {FORTRESS_COLORS['text_secondary']}; min-width: 80px;"))
            row.addWidget(lbl)
            val = QLabel(str(value))
            val.setWordWrap(True)
            # 使用 text_primary 确保在深色背景上可见
            val.setStyleSheet(f"color: {FORTRESS_COLORS['text_primary']};")
            row.addWidget(val, 1)
            info_layout.addLayout(row)

        layout.addWidget(info_container)

        # JSON 详情
        json_label = QLabel(tr("scan.full_json_data"))
        json_label.setStyleSheet(f"font-weight: bold; color: {FORTRESS_COLORS['text_secondary']};")
        layout.addWidget(json_label)

        json_text = QTextEdit()
        json_text.setReadOnly(True)
        json_text.setStyleSheet(scaled_style(f"""
            QTextEdit {{
                background-color: #1e293b;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 12px;
                padding: 10px;
            }}
        """))
        json_text.setPlainText(json.dumps(result, indent=2, ensure_ascii=False))
        layout.addWidget(json_text)
        
        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_copy = self._create_fortress_button(tr("scan.copy_json"), "info")
        btn_copy.clicked.connect(lambda: (
            QApplication.clipboard().setText(json.dumps(result, indent=2, ensure_ascii=False)),
            QMessageBox.information(dialog, tr("msg.success"), tr("common.copied_to_clipboard"))
        ))
        btn_row.addWidget(btn_copy)
        
        btn_close = self._create_fortress_button(tr("common.close"), "primary")
        btn_close.clicked.connect(dialog.close)
        btn_row.addWidget(btn_close)
        
        layout.addLayout(btn_row)
        
        dialog.exec_()
    

    def stop_scan(self):
        """停止扫描 - 支持直接扫描和任务列表扫描"""
        # 情况1: 直接扫描（通过 self.scan_thread）
        if hasattr(self, 'scan_thread') and self.scan_thread and self.scan_thread.isRunning():
            # 1. 发送停止信号
            self.scan_thread.stop()
            self.append_log("[!] User stopped scan")
            
            # 2. 断开所有信号连接，防止后台继续更新 UI
            try:
                self.scan_thread.log_signal.disconnect(self.append_log)
            except:
                pass
            try:
                self.scan_thread.result_signal.disconnect(self.add_scan_result)
            except:
                pass
            try:
                self.scan_thread.progress_signal.disconnect(self.update_progress)
            except:
                pass
            try:
                self.scan_thread.finished_signal.disconnect(self.scan_finished)
            except:
                pass
            
            # 3. 立即更新 UI 状态（不等待线程结束）
            self._reset_scan_ui_after_stop()
            return
        
        # 情况2: 任务列表扫描（通过 TaskQueueManager）
        if hasattr(self, 'current_task_id') and self.current_task_id:
            from core.task_queue_manager import get_task_queue_manager, TaskStatus
            queue = get_task_queue_manager()
            
            # 取消任务
            if queue.cancel_task(self.current_task_id):
                self.append_log("[!] User stopped scan (task queue)")
                self._reset_scan_ui_after_stop()
                return
        
        # 没有找到正在运行的扫描
        self.append_log("[!] No running scan task")
    
    def _reset_scan_ui_after_stop(self):
        """停止扫描后重置 UI 状态"""
        self.btn_start.setEnabled(True)
        self.btn_start.setText(tr("scan.start_scan"))
        self.btn_stop.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText(tr("task.pause"))
        self.progress_bar.hide()
        
        # 计算耗时
        import time
        duration = time.time() - getattr(self, 'scan_start_time', time.time())
        duration_str = tr("time.ms", m=int(duration // 60), s=int(duration % 60)) if duration >= 60 else tr("time.seconds", s=int(duration))
        result_count = self.result_table.rowCount()
        
        # 保存扫描历史（标记为用户停止）
        self._save_scan_history("stopped", duration, result_count)
        
        # 更新任务队列中的状态为已取消
        if hasattr(self, 'current_task_id') and self.current_task_id:
            from core.task_queue_manager import get_task_queue_manager, TaskStatus
            queue = get_task_queue_manager()
            queue.update_task_status(self.current_task_id, TaskStatus.CANCELLED)
        
        self.lbl_progress.setText(tr("scan.stopped_summary", duration=duration_str, count=result_count))

        # 更新状态指示器
        self.status_indicator.setText(tr("status.stopped"))
        self.status_indicator.setStyleSheet(scaled_style(f"""
            color: {FORTRESS_COLORS['btn_warning']};
            font-size: 13px;
            padding: 5px 12px;
            background-color: #fff7ed;
            border-radius: 12px;
        """))


    def pause_scan(self):
        """暂停/继续扫描 - 支持直接扫描和任务列表扫描"""
        # 情况1: 直接扫描（通过 self.scan_thread）
        if hasattr(self, 'scan_thread') and self.scan_thread and self.scan_thread.isRunning():
            if self.scan_thread.is_paused():
                # 当前是暂停状态，点击继续
                if self.scan_thread.resume():
                    self._update_pause_ui_to_running()
                    return True
            else:
                # 当前是运行状态，点击暂停
                if self.scan_thread.pause():
                    self._update_pause_ui_to_paused()
                    return True
            return False
        
        # 情况2: 任务列表扫描（通过 TaskQueueManager）
        if hasattr(self, 'current_task_id') and self.current_task_id:
            from core.task_queue_manager import get_task_queue_manager, TaskStatus
            queue = get_task_queue_manager()
            task = queue.get_task(self.current_task_id)
            
            if not task:
                return False
            
            if task.status == TaskStatus.PAUSED:
                # 当前是暂停状态，点击继续
                if queue.resume_task(self.current_task_id):
                    self._update_pause_ui_to_running()
                    return True
            elif task.status == TaskStatus.RUNNING:
                # 当前是运行状态，点击暂停
                if queue.pause_task(self.current_task_id):
                    self._update_pause_ui_to_paused()
                    return True
        return False
    
    def _update_pause_ui_to_running(self):
        """更新 UI 为运行状态"""
        self.btn_pause.setText(tr("task.pause"))
        self.btn_pause.setToolTip(tr("scan.pause_tooltip"))
        self.lbl_progress.setText(tr("scan.resuming"))
        self.status_indicator.setText(tr("status.scanning"))
        self.status_indicator.setStyleSheet(scaled_style(f"""
            color: {FORTRESS_COLORS['btn_warning']};
            font-size: 13px;
            padding: 5px 12px;
            background-color: #fff7ed;
            border-radius: 12px;
        """))

        # 同步更新任务队列状态
        if hasattr(self, 'current_task_id') and self.current_task_id:
            from core.task_queue_manager import get_task_queue_manager, TaskStatus
            queue = get_task_queue_manager()
            queue.update_task_status(self.current_task_id, TaskStatus.RUNNING)

    def _update_pause_ui_to_paused(self):
        """更新 UI 为暂停状态"""
        self.btn_pause.setText(tr("task.continue"))
        self.btn_pause.setToolTip(tr("scan.resume_tooltip"))
        self.lbl_progress.setText(tr("scan.paused_hint"))
        self.status_indicator.setText(tr("status.paused"))
        self.status_indicator.setStyleSheet(scaled_style(f"""
            color: {FORTRESS_COLORS['btn_info']};
            font-size: 13px;
            padding: 5px 12px;
            background-color: #eff6ff;
            border-radius: 12px;
        """))
        
        # 同步更新任务队列状态
        if hasattr(self, 'current_task_id') and self.current_task_id:
            from core.task_queue_manager import get_task_queue_manager, TaskStatus
            queue = get_task_queue_manager()
            queue.update_task_status(self.current_task_id, TaskStatus.PAUSED)


    def show_log_dialog(self):
        """显示实时日志弹窗（非模态，实时更新）"""
        # 如果已有日志窗口，则激活它
        if hasattr(self, 'log_dialog') and self.log_dialog.isVisible():
            self.log_dialog.raise_()
            self.log_dialog.activateWindow()
            return
            
        self.log_dialog = QDialog(self)
        self.log_dialog.setWindowTitle(tr("log.realtime_log"))
        self.log_dialog.resize(scaled(900), scaled(600))
        
        # 应用全局样式
        from core.fortress_style import apply_fortress_style, get_button_style, get_secondary_button_style
        apply_fortress_style(self.log_dialog, FORTRESS_COLORS)
        
        layout = QVBoxLayout(self.log_dialog)
        
        # 提示标签
        lbl_hint = QLabel(tr("log.realtime_hint"))
        lbl_hint.setStyleSheet(f"color: {FORTRESS_COLORS['btn_success']}; font-weight: bold;")
        layout.addWidget(lbl_hint)
        
        self.live_log_text = QTextEdit()
        self.live_log_text.setReadOnly(True)
        self.live_log_text.setStyleSheet(scaled_style("font-family: Consolas; font-size: 10pt; background-color: #1e1e1e; color: #dcdcdc; border-radius: 6px;"))
        self.live_log_text.setText("\n".join(self.full_log))
        layout.addWidget(self.live_log_text)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_clear = QPushButton(tr("log.clear_log"))
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setStyleSheet(get_button_style("warning"))
        btn_clear.clicked.connect(lambda: (self.full_log.clear(), self.live_log_text.clear(), self.log_output.clear()))
        btn_row.addWidget(btn_clear)
        
        btn_close = QPushButton(tr("common.close"))
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(get_secondary_button_style())
        btn_close.clicked.connect(self.log_dialog.close)
        btn_row.addWidget(btn_close)
        
        layout.addLayout(btn_row)
        
        # 使用 QTimer 定时刷新日志
        from PyQt5.QtCore import QTimer
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_live_log)
        self.log_timer.start(500)  # 每 500ms 刷新一次
        
        # 窗口关闭时停止计时器
        self.log_dialog.finished.connect(lambda: self.log_timer.stop() if hasattr(self, 'log_timer') else None)
        
        self.log_dialog.show()  # 非模态显示
    
    def update_live_log(self):
        """更新实时日志"""
        if hasattr(self, 'live_log_text') and self.live_log_text:
            current_text = "\n".join(self.full_log)
            if self.live_log_text.toPlainText() != current_text:
                # 保存滚动位置
                scrollbar = self.live_log_text.verticalScrollBar()
                at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
                
                self.live_log_text.setText(current_text)
                
                # 如果之前在底部，保持滚动到底部
                if at_bottom:
                    scrollbar.setValue(scrollbar.maximum())

    def show_result_detail(self, index):
        """双击显示漏洞详情"""
        row = index.row()
        if row < 0 or row >= len(self.scan_results_data):
            return
        
        result = self.scan_results_data[row]
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("report.vuln_detail", id=result.get('template-id', 'Unknown')))
        dialog.resize(scaled(700), scaled(500))
        
        layout = QVBoxLayout(dialog)
        
        # 基本信息
        info_text = f"""
<h2>🔍 {result.get('template-id', 'Unknown')}</h2>
<p><b>Target:</b> {result.get('matched-at', 'N/A')}</p>
<p><b>Time:</b> {result.get('timestamp', 'N/A')}</p>
<p><b>Severity:</b> {result.get('info', {}).get('severity', 'unknown')}</p>
<p><b>Name:</b> {result.get('info', {}).get('name', 'N/A')}</p>
<p><b>Description:</b> {result.get('info', {}).get('description', 'N/A')}</p>
<hr>
<h3>📋 Full JSON Data:</h3>
"""
        
        detail_text = QTextEdit()
        detail_text.setReadOnly(True)
        detail_text.setHtml(info_text)
        
        import json
        json_text = QTextEdit()
        json_text.setReadOnly(True)
        json_text.setStyleSheet(scaled_style("font-family: Consolas; font-size: 10pt; background-color: #1e1e1e; color: #dcdcdc;"))
        json_text.setPlainText(json.dumps(result, indent=2, ensure_ascii=False))
        
        layout.addWidget(detail_text)
        layout.addWidget(json_text)
        
        btn_copy = QPushButton("📋 Copy JSON")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(json.dumps(result, indent=2, ensure_ascii=False)))
        layout.addWidget(btn_copy)
        
        btn_close = QPushButton(tr("common.close"))
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.exec_()

# 全局异常捕获
def install_exception_hook():
    """安装全局异常捕获器"""
    import sys
    import traceback
    from PyQt5.QtWidgets import QMessageBox, QApplication
    
    def _check_nuclei_status(self):
        """检测 Nuclei 状态"""
        try:
            from core.nuclei_runner import get_nuclei_path
            import os
            
            nuclei_path = get_nuclei_path()
            
            if os.path.exists(nuclei_path):
                self.nuclei_status_label.setText(tr("nuclei.status_installed"))
                self.nuclei_status_label.setStyleSheet(f"color: {FORTRESS_COLORS['btn_success']}; font-weight: bold;")
                self.download_nuclei_btn.setText(tr("nuclei.update_latest"))
            else:
                self.nuclei_status_label.setText(tr("nuclei.status_not_installed"))
                self.nuclei_status_label.setStyleSheet(f"color: {FORTRESS_COLORS['status_critical']}; font-weight: bold;")
                self.download_nuclei_btn.setText(tr("nuclei.download_latest"))

        except Exception as e:
            self.nuclei_status_label.setText(tr("nuclei.detect_failed", error=str(e)))
            self.nuclei_status_label.setStyleSheet(f"color: {FORTRESS_COLORS['status_critical']}; font-weight: bold;")
    
    def _download_nuclei(self):
        """下载 Nuclei"""
        try:
            import subprocess
            import sys
            import os
            from PyQt5.QtCore import QThread, pyqtSignal
            
            # 创建下载线程
            class NucleiDownloadThread(QThread):
                progress_signal = pyqtSignal(str)
                finished_signal = pyqtSignal(bool, str)
                
                def run(self):
                    try:
                        self.progress_signal.emit(tr("nuclei.downloading"))
                        from download_nuclei_with_progress import download_with_callback

                        def on_progress(message, percent=None):
                            self.progress_signal.emit(str(message))

                        if download_with_callback(on_progress):
                            self.finished_signal.emit(True, tr("nuclei.download_complete"))
                        else:
                            self.finished_signal.emit(False, tr("nuclei.download_failed"))
                            
                    except Exception as e:
                        self.finished_signal.emit(False, tr("nuclei.download_error", error=str(e)))
            
            # 禁用按钮并启动下载
            self.download_nuclei_btn.setEnabled(False)
            self.nuclei_progress_label.setText(tr("nuclei.preparing_download"))
            
            self.nuclei_download_thread = NucleiDownloadThread()
            self.nuclei_download_thread.progress_signal.connect(self.nuclei_progress_label.setText)
            self.nuclei_download_thread.finished_signal.connect(self._on_nuclei_download_finished)
            self.nuclei_download_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, tr("msg.error"), tr("nuclei.start_download_failed", error=str(e)))
            self.download_nuclei_btn.setEnabled(True)
    
    def _on_nuclei_download_finished(self, success, message):
        """Nuclei 下载完成回调"""
        self.download_nuclei_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, tr("msg.success"), message)
            self.nuclei_progress_label.setText(tr("nuclei.download_done"))
            self._check_nuclei_status()  # 重新检测状态
        else:
            QMessageBox.critical(self, tr("msg.failure"), message)
            self.nuclei_progress_label.setText(tr("nuclei.download_failed_status"))
    
    def exception_hook(exctype, value, tb):
        error_msg = "".join(traceback.format_exception(exctype, value, tb))
        print(error_msg)  # 输出到控制台
        
        # 确保 QApplication 实例存在
        if QApplication.instance():
            QMessageBox.critical(None, "Program Error", f"Uncaught exception: \n{str(value)}\n\n{error_msg}")
        
        # 调用原始的钩子
        sys.__excepthook__(exctype, value, tb)
        
    sys.excepthook = exception_hook

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QDesktopWidget
    from PyQt5.QtGui import QFont
    from PyQt5.QtCore import Qt
    
    install_exception_hook()
    ensure_external_layout()
    
    # 启用高 DPI 缩放支持
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except Exception as e:
        print(f"Error setting DPI attributes: {e}")
        pass
    
    # Windows 任务栏图标修复：设置 AppUserModelID
    # 这样 Windows 才会把程序识别为独立应用，而不是 Python 的子进程
    try:
        import ctypes
        app_id = 'NucleiGUI.Scanner.App.1.0'  # 自定义应用程序 ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:
        print(f"Error setting AppUserModelID: {e}")
        pass
    
    app = QApplication(sys.argv)

    # 获取屏幕信息和系统 DPI 缩放
    from PyQt5.QtWidgets import QDesktopWidget
    from core.settings_manager import get_settings
    primary_screen = app.primaryScreen()
    screen = primary_screen.availableGeometry() if primary_screen else QDesktopWidget().screenGeometry()
    settings = get_settings()

    # 初始化多语言
    from i18n import init_language
    init_language(settings.get_language())

    # 获取系统 DPI 缩放比例，仅用于诊断输出；Qt 已使用逻辑像素处理控件尺寸。
    logical_dpi = primary_screen.logicalDotsPerInch() if primary_screen else 96.0
    system_scale = logical_dpi / 96.0  # 系统缩放比例

    # 读取用户配置的 UI 缩放，0 表示自动
    user_scale = settings.get_ui_scale()

    if user_scale > 0:
        # 用户手动设置了缩放比例
        set_ui_scale(user_scale)
        font_size = 10
        print(f"[DPI Info] Using user-defined UI_SCALE: {user_scale}")
    else:
        # 自动计算缩放比例：Qt High DPI 下 screen 已是逻辑像素，避免再按 DPI 二次修正。
        auto_scale, font_size = calculate_auto_ui_scale(screen.width(), screen.height())
        set_ui_scale(auto_scale)

        print(f"[DPI Info] Screen: {screen.width()}x{screen.height()}, DPI: {logical_dpi}, System Scale: {system_scale:.0%}, UI_SCALE: {get_ui_scale()}")

    font = QFont("Microsoft YaHei", font_size)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
