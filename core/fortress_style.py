"""
FORTRESS 风格共享样式和组件
用于统一所有对话框和界面的样式
支持动态主题切换
"""

def get_table_stylesheet(colors=None):
    """获取表格通用样式"""
    if colors is None:
        colors = {}
    # 判断是否是深色主题
    is_dark = colors.get('is_dark', False)
    if not is_dark and 'content_bg' in colors:
        is_dark = colors.get('content_bg', '').lower() in ['#1e293b', '#1a2332', '#111827']
    
    bg_color = colors.get('content_bg', '#1e293b') if is_dark else 'white'

    
    return f"""
        QTableWidget {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            gridline-color: {colors.get('nav_border', '#e5e7eb')};
            background-color: {bg_color};
            alternate-background-color: {colors.get('table_row_alt', '#f9fafb')};
            color: {colors.get('text_primary', '#1f2937')};
            selection-background-color: {colors.get('nav_active', '#3b82f6')};
            selection-color: white;
            outline: none;
        }}
        QTableWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {colors.get('nav_border', '#e5e7eb')};
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QTableWidget::item:selected {{
            background-color: {colors.get('nav_active', '#3b82f6')};
            color: white;
            border: none;
        }}
        
        QHeaderView {{
            background-color: transparent;
            border: none;
        }}
        
        QHeaderView::section {{
            background-color: {colors.get('table_header', '#f1f5f9')};
            padding: 8px;
            border: none;
            border-bottom: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-right: 1px solid {colors.get('nav_border', '#e5e7eb')};
            font-weight: bold;
            color: {colors.get('text_primary', '#1f2937')};
        }}
        
        /* 垂直表头（序号列）特殊处理 */
        QHeaderView::section:vertical {{
            background-color: {colors.get('table_header', '#f1f5f9')};
            border-right: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-bottom: 1px solid {colors.get('nav_border', '#e5e7eb')};
            color: {colors.get('text_secondary', '#6b7280')};
            padding-left: 5px;
        }}
        
        QTableCornerButton::section {{
            background-color: {colors.get('table_header', '#f1f5f9')};
            border: none;
            border-bottom: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-right: 1px solid {colors.get('nav_border', '#e5e7eb')};
        }}
    """

def get_list_stylesheet(colors=None):
    """获取列表通用样式"""
    if colors is None:
        colors = {}
    is_dark = colors.get('is_dark', False)
    if not is_dark and 'content_bg' in colors:
         is_dark = colors.get('content_bg', '').lower() in ['#1e293b', '#1a2332', '#111827']
         
    bg_color = colors.get('content_bg', '#1e293b') if is_dark else 'white'

    
    return f"""
        QListWidget {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            background-color: {bg_color};
            color: {colors.get('text_primary', '#1f2937')};
            outline: none;
        }}
        QListWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {colors.get('nav_border', '#e5e7eb')};
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QListWidget::item:hover {{
            background-color: {colors.get('nav_hover', '#f3f4f6')};
        }}
        QListWidget::item:selected {{
            background-color: {colors.get('nav_active', '#3b82f6')};
            color: white;
            border: none;
        }}
        QListWidget::item:selected:hover {{
            background-color: {colors.get('btn_primary', '#2563eb')};
        }}
    """

def get_menu_stylesheet(colors=None):
    """获取菜单通用样式"""
    if colors is None:
        colors = {}
    is_dark = colors.get('is_dark', False)
    if not is_dark and 'content_bg' in colors:
         is_dark = colors.get('content_bg', '').lower() in ['#1e293b', '#1a2332', '#111827']
         
    bg_color = colors.get('content_bg', '#1e293b') if is_dark else 'white'
    
    return f"""
        QMenu {{
            background-color: {bg_color};
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            padding: 5px 0px;
        }}
        QMenu::item {{
            padding: 8px 30px 8px 20px;
            background-color: transparent;
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QMenu::item:selected {{
            background-color: {colors.get('nav_hover', '#f3f4f6')};
            color: {colors.get('btn_primary', '#2563eb')};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {colors.get('nav_border', '#e5e7eb')};
            margin: 5px 0px;
        }}
        QMenu::icon {{
            padding-left: 10px;
            width: 16px;
            height: 16px;
        }}
    """

def get_dialog_stylesheet(colors=None):
    """获取对话框基础样式"""
    if colors is None:
        colors = {}
    is_dark = colors.get('is_dark', False)
    if not is_dark and 'content_bg' in colors:
         is_dark = colors.get('content_bg', '').lower() in ['#1e293b', '#1a2332', '#111827']
         
    input_bg = colors.get('table_header', '#334155') if is_dark else 'white'
    
    return f"""
        QDialog, QMessageBox {{
            background-color: {colors.get('content_bg', '#f8fafc')};
        }}
        QLabel {{
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 10px;
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }}
        QLineEdit, QTextEdit, QPlainTextEdit {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            padding: 8px 12px;
            background-color: {input_bg};
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors.get('btn_primary', '#2563eb')};
        }}
        QComboBox {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            padding: 6px 10px;
            background-color: {input_bg};
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QSpinBox {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            padding: 6px 10px;
            background-color: {input_bg};
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QProgressBar {{
            border: none;
            border-radius: 5px;
            background-color: {colors.get('nav_border', '#ecf0f1')};
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {colors.get('btn_primary', '#2563eb')};
            border-radius: 5px;
        }}
        QCheckBox {{
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QRadioButton {{
            color: {colors.get('text_primary', '#1f2937')};
        }}
        {get_table_stylesheet(colors)}
    """


def get_button_style(btn_type='primary', colors=None):
    """获取按钮样式"""
    if colors is None:
        colors = {}
    
    color_map = {
        'primary': (colors.get('btn_primary', '#2563eb'), colors.get('btn_primary_hover', '#1d4ed8')),
        'warning': (colors.get('btn_warning', '#f97316'), colors.get('btn_warning_hover', '#ea580c')),
        'info': (colors.get('btn_info', '#3b82f6'), colors.get('btn_info_hover', '#2563eb')),
        'success': (colors.get('btn_success', '#22c55e'), colors.get('btn_success_hover', '#16a34a')),
        'danger': (colors.get('btn_danger', '#ef4444'), colors.get('btn_danger_hover', '#dc2626')),
    }
    
    bg, hover = color_map.get(btn_type, color_map['primary'])
    
    return f"""
        QPushButton {{
            background-color: {bg};
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: bold;
            padding: 8px 16px;
            min-height: 32px;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:disabled {{
            background-color: #9ca3af;
        }}
    """


def get_secondary_button_style(colors=None):
    """获取次要按钮样式（灰色边框）"""
    if colors is None:
        colors = {}
    
    is_dark = colors.get('is_dark', False)
    if not is_dark and 'content_bg' in colors:
         is_dark = colors.get('content_bg', '').lower() in ['#1e293b', '#1a2332', '#111827']
         
    bg_color = colors.get('table_header', '#334155') if is_dark else 'white'
    
    return f"""
        QPushButton {{
            background-color: {bg_color};
            color: {colors.get('text_primary', '#1f2937')};
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            font-size: 13px;
            padding: 8px 16px;
            min-height: 32px;
        }}
        QPushButton:hover {{
            background-color: {colors.get('nav_hover', '#f3f4f6')};
        }}
    """


def get_table_button_style(btn_type='info', colors=None, min_width=70):
    """
    获取表格内操作按钮样式
    - 固定最小宽度防止被挤压
    - 统一的视觉风格
    """
    if colors is None:
        colors = {}

    color_map = {
        'primary': (colors.get('btn_primary', '#2563eb'), colors.get('btn_primary_hover', '#1d4ed8')),
        'warning': (colors.get('btn_warning', '#f97316'), colors.get('btn_warning_hover', '#ea580c')),
        'info': (colors.get('btn_info', '#3b82f6'), colors.get('btn_info_hover', '#2563eb')),
        'success': (colors.get('btn_success', '#22c55e'), colors.get('btn_success_hover', '#16a34a')),
        'danger': (colors.get('btn_danger', '#ef4444'), colors.get('btn_danger_hover', '#dc2626')),
    }

    bg, hover = color_map.get(btn_type, color_map['info'])

    return f"""
        QPushButton {{
            background-color: {bg};
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 12px;
            padding: 4px 10px;
            min-width: {min_width}px;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:disabled {{
            background-color: #9ca3af;
        }}
    """


def apply_fortress_style(dialog, colors=None):
    """应用 FORTRESS 样式到对话框"""
    if colors is None:
        colors = {}
    dialog.setStyleSheet(get_dialog_stylesheet(colors))


def get_global_stylesheet(colors=None):
    """获取全局通用样式（滚动条、下拉框等）"""
    if colors is None:
        colors = {}
    
    is_dark = colors.get('is_dark', False)
    if not is_dark and 'content_bg' in colors:
         is_dark = colors.get('content_bg', '').lower() in ['#1e293b', '#1a2332', '#111827']
         
    input_bg = colors.get('table_header', '#334155') if is_dark else 'white'
    scroll_bg = colors.get('nav_border', '#334155')
    scroll_handle = '#64748b' if is_dark else '#cbd5e1'
    
    return f"""
        /* 滚动条样式 */
        QScrollBar:vertical {{
            border: none;
            background: {scroll_bg};
            width: 12px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {scroll_handle};
            min-height: 30px;
            border-radius: 6px;
            border: 2px solid {scroll_bg};
        }}
        QScrollBar::handle:vertical:hover {{
            background: #94a3b8;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        
        QScrollBar:horizontal {{
            border: none;
            background: {scroll_bg};
            height: 12px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {scroll_handle};
            min-width: 30px;
            border-radius: 6px;
            border: 2px solid {scroll_bg};
        }}
        QScrollBar::handle:horizontal:hover {{
            background: #94a3b8;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
        
        /* 下拉框样式 */
        QComboBox {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            padding: 6px 10px;
            background-color: {input_bg};
            color: {colors.get('text_primary', '#1f2937')};
            min-height: 20px;
        }}
        QComboBox:hover {{
            border-color: {colors.get('btn_primary', '#2563eb')};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 25px;
            border-left-width: 1px;
            border-left-color: {colors.get('nav_border', '#e5e7eb')};
            border-left-style: solid;
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
            background-color: {colors.get('table_header', '#f8fafc')};
        }}
        QComboBox::drop-down:hover {{
            background-color: {colors.get('nav_hover', '#f1f5f9')};
        }}
        /* 使用自定义绘制的箭头（通过边框实现倒三角） */
        QComboBox::down-arrow {{
            width: 0; 
            height: 0; 
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {colors.get('text_secondary', '#6b7280')};
            margin-right: 2px;
        }}
        QComboBox::down-arrow:on {{
            top: 1px;
            left: 1px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {input_bg};
            color: {colors.get('text_primary', '#1f2937')};
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            selection-background-color: {colors.get('nav_active', '#3b82f6')};
            selection-color: white;
        }}
        
        /* 输入框样式 */
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            padding: 8px 12px;
            background-color: {input_bg};
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {colors.get('btn_primary', '#2563eb')};
        }}
        
        /* 文本框样式 */
        QTextEdit, QPlainTextEdit {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 6px;
            padding: 8px;
            background-color: {input_bg};
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors.get('btn_primary', '#2563eb')};
        }}
        
        /* 表格样式 */
        {get_table_stylesheet(colors)}
        
        /* 列表样式 */
        {get_list_stylesheet(colors)}
        
        /* 标签页样式 */
        QTabWidget::pane {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            background-color: {colors.get('content_bg', '#f8fafc')};
            border-radius: 8px;
        }}
        QTabBar::tab {{
            background-color: {colors.get('table_header', '#f1f5f9')};
            color: {colors.get('text_primary', '#1f2937')};
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background-color: {colors.get('content_bg', '#ffffff')};
            font-weight: bold;
        }}
        
        /* 分组框样式 */
        QGroupBox {{
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 10px;
            color: {colors.get('text_primary', '#1f2937')};
            background-color: {colors.get('content_bg', '#f8fafc')};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: {colors.get('text_primary', '#1f2937')};
        }}
        
        /* 基础组件样式 */
        QLabel {{
            color: {colors.get('text_primary', '#1f2937')};
        }}
        QCheckBox {{
            color: {colors.get('text_primary', '#1f2937')};
            spacing: 5px;
        }}
        QRadioButton {{
            color: {colors.get('text_primary', '#1f2937')};
            spacing: 5px;
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            background-color: {input_bg};
            border: 1px solid {colors.get('nav_border', '#e5e7eb')};
            border-radius: 3px;
        }}
        QRadioButton::indicator {{
            border-radius: 8px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors.get('btn_primary', '#2563eb')};
            border-color: {colors.get('btn_primary', '#2563eb')};
            image: url(resources/check.png); /* 如果没有图片，用纯色也可以，或者暂时这样 */
        }}
        QRadioButton::indicator:checked {{
            background-color: {colors.get('btn_primary', '#2563eb')};
            border-color: {colors.get('btn_primary', '#2563eb')};
        }}
        QCheckBox::indicator:checked:disabled, QRadioButton::indicator:checked:disabled {{
            background-color: {colors.get('nav_border', '#e5e7eb')};
            border-color: {colors.get('nav_border', '#e5e7eb')};
        }}
        
        /* 弹窗样式 */
        QMessageBox {{
            background-color: {colors.get('content_bg', '#f8fafc')};
        }}
        QMessageBox QLabel {{
            color: {colors.get('text_primary', '#1f2937')};
        }}
    """


# 兼容旧接口 - 使用默认颜色
FORTRESS_COLORS = {
    'nav_bg': '#ffffff',
    'nav_border': '#e5e7eb',
    'nav_active': '#3b82f6',
    'nav_hover': '#f3f4f6',
    'btn_primary': '#2563eb',
    'btn_primary_hover': '#1d4ed8',
    'btn_warning': '#f97316',
    'btn_warning_hover': '#ea580c',
    'btn_info': '#3b82f6',
    'btn_info_hover': '#2563eb',
    'btn_success': '#22c55e',
    'btn_success_hover': '#16a34a',
    'btn_danger': '#ef4444',
    'btn_danger_hover': '#dc2626',
    'content_bg': '#f8fafc',
    'text_primary': '#1f2937',
    'text_secondary': '#6b7280',
    'table_header': '#f1f5f9',
    'status_high': '#3b82f6',
    'status_medium': '#f97316',
    'status_low': '#22c55e',
}
