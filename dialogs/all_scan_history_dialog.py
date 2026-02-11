"""
全部扫描历史记录弹窗 - 支持分页查看所有历史
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QPushButton, QLabel,
                             QComboBox, QMessageBox, QApplication, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont


class AllScanHistoryDialog(QDialog):
    """全部扫描历史记录弹窗"""
    
    def __init__(self, parent=None, colors=None):
        super().__init__(parent)
        self.parent_window = parent
        self.colors = colors if colors else {}
        self.setWindowTitle("全部扫描历史")
        self.resize(1000, 650)
        
        # 分页参数
        self.current_page = 1
        self.page_size = 50
        self.total_records = 0
        self.total_pages = 1
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """初始化界面"""
        # 应用 FORTRESS 样式
        from core.fortress_style import get_dialog_stylesheet, get_button_style, get_secondary_button_style, get_table_button_style
        
        # 使用传入的颜色配置，如果未传入则默认空字典（将使用默认样式）
        self.setStyleSheet(get_dialog_stylesheet(self.colors))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部信息
        top_row = QHBoxLayout()
        self.info_label = QLabel("正在加载...")
        c = self.colors
        text_primary = c.get('text_primary', '#1f2937')
        self.info_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {text_primary};")
        top_row.addWidget(self.info_label)
        top_row.addStretch()
        
        # 每页条数选择
        top_row.addWidget(QLabel("每页显示:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["20", "50", "100", "200"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        top_row.addWidget(self.page_size_combo)
        
        layout.addLayout(top_row)
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(["时间", "目标数", "POC数", "漏洞数", "状态", "详情", "导出"])
        self.history_table.verticalHeader().setVisible(False)
        
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 时间列拉伸
        for i in range(1, 5):  # 目标数、POC数、漏洞数、状态列自适应
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        # 详情和导出列设置固定宽度，防止被挤压
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.history_table.setColumnWidth(5, 85)  # 详情列 - 与仪表盘保持一致
        self.history_table.setColumnWidth(6, 85)  # 导出列 - 与仪表盘保持一致
        
        # 设置行高，确保按钮完全显示（与仪表盘一致）
        self.history_table.verticalHeader().setDefaultSectionSize(45)
        self.history_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)
        
        # 分页控制
        page_row = QHBoxLayout()
        
        self.btn_first = QPushButton("首页")
        self.btn_first.setStyleSheet(get_secondary_button_style(self.colors))
        self.btn_first.clicked.connect(lambda: self.goto_page(1))
        page_row.addWidget(self.btn_first)
        
        self.btn_prev = QPushButton("上一页")
        self.btn_prev.setStyleSheet(get_secondary_button_style(self.colors))
        self.btn_prev.clicked.connect(lambda: self.goto_page(self.current_page - 1))
        page_row.addWidget(self.btn_prev)
        
        self.page_label = QLabel("第 1 页 / 共 1 页")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label = QLabel("第 1 页 / 共 1 页")
        self.page_label.setAlignment(Qt.AlignCenter)
        text_secondary = self.colors.get('text_secondary', '#6b7280')
        self.page_label.setStyleSheet(f"color: {text_secondary}; padding: 0 15px;")
        page_row.addWidget(self.page_label)
        
        self.btn_next = QPushButton("下一页")
        self.btn_next.setStyleSheet(get_secondary_button_style(self.colors))
        self.btn_next.clicked.connect(lambda: self.goto_page(self.current_page + 1))
        page_row.addWidget(self.btn_next)
        
        self.btn_last = QPushButton("末页")
        self.btn_last.setStyleSheet(get_secondary_button_style(self.colors))
        self.btn_last.clicked.connect(lambda: self.goto_page(self.total_pages))
        page_row.addWidget(self.btn_last)
        
        page_row.addStretch()
        
        # 刷新按钮
        btn_refresh = QPushButton("刷新")
        btn_refresh.setStyleSheet(get_button_style('info', self.colors))
        btn_refresh.clicked.connect(self.load_data)
        page_row.addWidget(btn_refresh)
        
        layout.addLayout(page_row)
        
        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet(get_secondary_button_style(self.colors))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        
        layout.addLayout(btn_row)
    
    def load_data(self):
        """加载数据"""
        from core.scan_history import get_scan_history
        
        history_mgr = get_scan_history()
        
        # 获取分页数据
        result = history_mgr.get_all_scans(self.current_page, self.page_size)
        records = result.get('records', [])
        self.total_records = result.get('total', 0)
        self.total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        
        # 更新信息
        self.info_label.setText(f"📊 共 {self.total_records} 条扫描记录")
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {self.total_pages} 页")
        
        # 更新按钮状态
        self.btn_first.setEnabled(self.current_page > 1)
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < self.total_pages)
        self.btn_last.setEnabled(self.current_page < self.total_pages)
        
        # 填充表格
        self.history_table.setUpdatesEnabled(False)
        self.history_table.setRowCount(0)
        self.history_table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            # 时间
            scan_time = record.get('scan_time', '')[:19]
            self.history_table.setItem(row, 0, QTableWidgetItem(scan_time))
            
            # 目标数
            self.history_table.setItem(row, 1, QTableWidgetItem(str(record.get('target_count', 0))))
            
            # POC 数
            self.history_table.setItem(row, 2, QTableWidgetItem(str(record.get('poc_count', 0))))
            
            # 漏洞数
            vuln_count = record.get('vuln_count', 0)
            vuln_item = QTableWidgetItem(str(vuln_count))
            if vuln_count > 0:
                vuln_item.setForeground(QColor('#e74c3c'))
                vuln_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.history_table.setItem(row, 3, vuln_item)
            
            # 状态
            status = record.get('status', '扫描完成')
            status_item = QTableWidgetItem(status)
            if status == '用户停止':
                status_item.setForeground(QColor('#e67e22'))
            else:
                status_item.setForeground(QColor('#27ae60'))
            self.history_table.setItem(row, 4, status_item)
            
            # 查看详情按钮 - 使用统一样式和容器居中（与仪表盘一致）
            from core.fortress_style import get_table_button_style
            btn_detail = QPushButton("详情")
            btn_detail.setStyleSheet(get_table_button_style('info', self.colors, 60))
            btn_detail.setCursor(Qt.PointingHandCursor)
            btn_detail.clicked.connect(lambda checked, sid=record.get('id'): self.show_scan_detail(sid))
            # 创建容器使按钮居中（调整边距让按钮靠左）
            detail_widget = QWidget()
            detail_widget.setObjectName("cell_container")
            detail_widget.setStyleSheet("#cell_container { background: transparent; }")
            detail_layout = QHBoxLayout(detail_widget)
            detail_layout.setContentsMargins(0, 2, 10, 2)
            detail_layout.addWidget(btn_detail)
            self.history_table.setCellWidget(row, 5, detail_widget)
            
            # 导出按钮 - 使用统一样式和容器居中（与仪表盘一致）
            btn_export = QPushButton("导出")
            btn_export.setStyleSheet(get_table_button_style('success', self.colors, 60))
            btn_export.setCursor(Qt.PointingHandCursor)
            btn_export.clicked.connect(lambda checked, sid=record.get('id'): self.export_scan_record(sid))
            # 创建容器使按钮居中（调整边距让按钮靠左）
            export_widget = QWidget()
            export_widget.setObjectName("cell_container")
            export_widget.setStyleSheet("#cell_container { background: transparent; }")
            export_layout = QHBoxLayout(export_widget)
            export_layout.setContentsMargins(0, 2, 10, 2)
            export_layout.addWidget(btn_export)
            self.history_table.setCellWidget(row, 6, export_widget)
        
        self.history_table.setUpdatesEnabled(True)
    
    def goto_page(self, page):
        """跳转到指定页"""
        if 1 <= page <= self.total_pages:
            self.current_page = page
            self.load_data()
    
    def on_page_size_changed(self, text):
        """每页条数改变"""
        self.page_size = int(text)
        self.current_page = 1  # 重置到第一页
        self.load_data()
    
    def show_scan_detail(self, scan_id):
        """显示扫描详情 - 调用父窗口方法"""
        if self.parent_window and hasattr(self.parent_window, 'show_scan_detail'):
            self.parent_window.show_scan_detail(scan_id)
        else:
            QMessageBox.warning(self, "错误", "无法显示扫描详情")
    
    def export_scan_record(self, scan_id):
        """导出扫描记录 - 调用父窗口方法"""
        if self.parent_window and hasattr(self.parent_window, 'export_scan_record'):
            self.parent_window.export_scan_record(scan_id)
        else:
            QMessageBox.warning(self, "错误", "无法导出扫描记录")
