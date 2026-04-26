"""
全部扫描历史记录弹窗 - 支持分页查看所有历史
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QPushButton, QLabel,
                             QComboBox, QMessageBox, QApplication, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from core.ui_scale import scaled, scaled_style
from i18n import tr


class AllScanHistoryDialog(QDialog):
    """全部扫描历史记录弹窗"""
    
    def __init__(self, parent=None, colors=None):
        super().__init__(parent)
        self.parent_window = parent
        self.colors = colors if colors else {}
        self.setWindowTitle(tr("history.all_scan_history"))
        self.resize(scaled(1000), scaled(650))
        
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
        layout.setSpacing(scaled(15))
        layout.setContentsMargins(scaled(20), scaled(20), scaled(20), scaled(20))
        
        # 顶部信息
        top_row = QHBoxLayout()
        self.info_label = QLabel(tr("history.loading"))
        c = self.colors
        text_primary = c.get('text_primary', '#1f2937')
        self.info_label.setStyleSheet(scaled_style(f"font-weight: bold; font-size: 14px; color: {text_primary};"))
        top_row.addWidget(self.info_label)
        top_row.addStretch()
        
        # 每页条数选择
        top_row.addWidget(QLabel(tr("history.per_page")))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["20", "50", "100", "200"])
        self.page_size_combo.setCurrentText("50")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        top_row.addWidget(self.page_size_combo)
        
        layout.addLayout(top_row)
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([tr("history.col_time"), tr("history.col_targets"), tr("history.col_pocs"), tr("history.col_vulns"), tr("history.col_status"), tr("history.col_detail"), tr("history.col_export")])
        self.history_table.verticalHeader().setVisible(False)
        
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 时间列拉伸
        for i in range(1, 5):  # 目标数、POC数、漏洞数、状态列自适应
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        # 详情和导出列设置固定宽度，防止被挤压
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.history_table.setColumnWidth(5, scaled(100))  # 详情列 - 与仪表盘保持一致
        self.history_table.setColumnWidth(6, scaled(100))  # 导出列 - 与仪表盘保持一致

        # 设置行高，确保按钮完全显示（与仪表盘一致）
        self.history_table.verticalHeader().setDefaultSectionSize(scaled(45))
        self.history_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)
        
        # 分页控制
        page_row = QHBoxLayout()
        
        self.btn_first = QPushButton(tr("history.first_page"))
        self.btn_first.setStyleSheet(get_secondary_button_style(self.colors))
        self.btn_first.clicked.connect(lambda: self.goto_page(1))
        page_row.addWidget(self.btn_first)
        
        self.btn_prev = QPushButton(tr("history.prev_page"))
        self.btn_prev.setStyleSheet(get_secondary_button_style(self.colors))
        self.btn_prev.clicked.connect(lambda: self.goto_page(self.current_page - 1))
        page_row.addWidget(self.btn_prev)
        
        self.page_label = QLabel(tr("history.page_info", current=1, total=1))
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label = QLabel(tr("history.page_info", current=1, total=1))
        self.page_label.setAlignment(Qt.AlignCenter)
        text_secondary = self.colors.get('text_secondary', '#6b7280')
        self.page_label.setStyleSheet(scaled_style(f"color: {text_secondary}; padding: 0 15px;"))
        page_row.addWidget(self.page_label)
        
        self.btn_next = QPushButton(tr("history.next_page"))
        self.btn_next.setStyleSheet(get_secondary_button_style(self.colors))
        self.btn_next.clicked.connect(lambda: self.goto_page(self.current_page + 1))
        page_row.addWidget(self.btn_next)
        
        self.btn_last = QPushButton(tr("history.last_page"))
        self.btn_last.setStyleSheet(get_secondary_button_style(self.colors))
        self.btn_last.clicked.connect(lambda: self.goto_page(self.total_pages))
        page_row.addWidget(self.btn_last)
        
        page_row.addStretch()
        
        # 刷新按钮
        btn_refresh = QPushButton(tr("common.refresh"))
        btn_refresh.setStyleSheet(get_button_style('info', self.colors))
        btn_refresh.clicked.connect(self.load_data)
        page_row.addWidget(btn_refresh)
        
        layout.addLayout(page_row)
        
        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_close = QPushButton(tr("common.close"))
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
        self.info_label.setText(tr("history.total_records", count=self.total_records))
        self.page_label.setText(tr("history.page_info", current=self.current_page, total=self.total_pages))
        
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
                vuln_item.setFont(QFont("Arial", scaled(10), QFont.Bold))
            self.history_table.setItem(row, 3, vuln_item)
            
            # 状态
            status = record.get('status', 'completed')
            # 将英文内部键映射为显示文本
            _scan_status_display = {
                'completed': tr('scan_status.completed'),
                'failed': tr('scan_status.failed'),
                'stopped': tr('scan_status.stopped'),
            }
            display_status = _scan_status_display.get(status, status)
            status_item = QTableWidgetItem(display_status)
            if status == 'stopped':
                status_item.setForeground(QColor('#e67e22'))
            else:
                status_item.setForeground(QColor('#27ae60'))
            self.history_table.setItem(row, 4, status_item)
            
            # 查看详情按钮 - 使用统一样式和容器居中（与仪表盘一致）
            from core.fortress_style import get_table_button_style
            btn_detail = QPushButton(tr("history.col_detail"))
            btn_detail.setStyleSheet(get_table_button_style('info', self.colors, 60))
            btn_detail.setCursor(Qt.PointingHandCursor)
            btn_detail.clicked.connect(lambda checked, sid=record.get('id'): self.show_scan_detail(sid))
            # 创建容器使按钮居中（调整边距让按钮靠左）
            detail_widget = QWidget()
            detail_widget.setObjectName("cell_container")
            detail_widget.setStyleSheet(scaled_style("#cell_container { background: transparent; }"))
            detail_layout = QHBoxLayout(detail_widget)
            detail_layout.setContentsMargins(scaled(0), scaled(2), scaled(10), scaled(2))
            detail_layout.addWidget(btn_detail)
            self.history_table.setCellWidget(row, 5, detail_widget)
            
            # 导出按钮 - 使用统一样式和容器居中（与仪表盘一致）
            btn_export = QPushButton(tr("history.col_export"))
            btn_export.setStyleSheet(get_table_button_style('success', self.colors, 60))
            btn_export.setCursor(Qt.PointingHandCursor)
            btn_export.clicked.connect(lambda checked, sid=record.get('id'): self.export_scan_record(sid))
            # 创建容器使按钮居中（调整边距让按钮靠左）
            export_widget = QWidget()
            export_widget.setObjectName("cell_container")
            export_widget.setStyleSheet(scaled_style("#cell_container { background: transparent; }"))
            export_layout = QHBoxLayout(export_widget)
            export_layout.setContentsMargins(scaled(0), scaled(2), scaled(10), scaled(2))
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
            QMessageBox.warning(self, tr("msg.error"), tr("history.cannot_show_detail"))
    
    def export_scan_record(self, scan_id):
        """导出扫描记录 - 调用父窗口方法"""
        if self.parent_window and hasattr(self.parent_window, 'export_scan_record'):
            self.parent_window.export_scan_record(scan_id)
        else:
            QMessageBox.warning(self, tr("msg.error"), tr("history.cannot_export"))
