"""
FOFA 搜索弹窗 - 独立窗口执行 FOFA 搜索并导入目标
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QCheckBox, QGroupBox, QProgressBar, QComboBox,
    QMenu, QAction, QSplitter, QListWidget, QListWidgetItem, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.settings_manager import get_settings
from core.fofa_client import FofaSearchThread
from core.history_manager import get_history_manager


class FofaDialog(QDialog):
    """
    FOFA 搜索弹窗
    支持搜索、预览结果、勾选导入目标、历史记录
    """
    
    
    def __init__(self, parent=None, query=None):
        super().__init__(parent)
        self.settings = get_settings()
        self.history_manager = get_history_manager()
        self.search_thread = None
        self.selected_targets = []  # 存储选中的目标
        self.initial_query = query
        self.current_results = []  # 当前搜索结果
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("🔍 FOFA 搜索")
        self.resize(950, 650)
        self.setMinimumSize(700, 450)
        
        layout = QVBoxLayout(self)
        
        # 使用分割器：左侧历史记录，右侧搜索区域
        splitter = QSplitter(Qt.Horizontal)
        
        # ========== 左侧：历史记录 ==========
        history_widget = QGroupBox("📜 搜索历史")
        history_layout = QVBoxLayout(history_widget)
        
        self.history_list = QListWidget()
        self.history_list.setMaximumWidth(250)
        self.history_list.itemDoubleClicked.connect(self.load_history_item)
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_history_context_menu)
        history_layout.addWidget(self.history_list)
        
        # 历史记录操作按钮
        history_btn_row = QHBoxLayout()
        btn_load = QPushButton("📥 加载")
        btn_load.clicked.connect(self.load_selected_history)
        history_btn_row.addWidget(btn_load)
        
        btn_clear_history = QPushButton("🗑️ 清空")
        btn_clear_history.clicked.connect(self.clear_history)
        history_btn_row.addWidget(btn_clear_history)
        
        history_layout.addLayout(history_btn_row)
        
        splitter.addWidget(history_widget)
        
        # ========== 右侧：搜索和结果 ==========
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 搜索区域
        search_group = QGroupBox("搜索")
        search_layout = QVBoxLayout()
        
        # 输入行
        input_row = QHBoxLayout()
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText('输入 FOFA 查询语句，例如: app="Apache" && country="CN"')
        if self.initial_query:
            self.query_input.setText(self.initial_query)
        self.query_input.returnPressed.connect(self.do_search)
        input_row.addWidget(self.query_input)
        
        # 数量选择
        input_row.addWidget(QLabel("数量:"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(["100", "500", "1000", "5000", "10000"])
        self.size_combo.setEditable(True)  # 允许手动输入
        self.size_combo.setFixedWidth(80)
        input_row.addWidget(self.size_combo)
        
        self.btn_search = QPushButton("🔍 搜索")
        self.btn_search.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 5px 15px;")
        self.btn_search.clicked.connect(self.do_search)
        input_row.addWidget(self.btn_search)
        
        search_layout.addLayout(input_row)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        search_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("请输入 FOFA 语句并点击搜索")
        self.status_label.setStyleSheet("color: #7f8c8d;")
        search_layout.addWidget(self.status_label)
        
        search_group.setLayout(search_layout)
        right_layout.addWidget(search_group)
        
        # 结果表格
        result_group = QGroupBox("搜索结果")
        result_layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        btn_select_all = QPushButton("全选")
        btn_select_all.clicked.connect(self.select_all)
        toolbar.addWidget(btn_select_all)
        
        btn_deselect_all = QPushButton("取消全选")
        btn_deselect_all.clicked.connect(self.deselect_all)
        toolbar.addWidget(btn_deselect_all)
        
        toolbar.addStretch()
        
        self.count_label = QLabel("共 0 条结果")
        toolbar.addWidget(self.count_label)
        
        result_layout.addLayout(toolbar)
        
        # 表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["✓", "URL/Host", "IP", "端口", "标题"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.result_table.setColumnWidth(0, 30)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.result_table.setColumnWidth(3, 60)
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        
        result_layout.addWidget(self.result_table)
        
        result_group.setLayout(result_layout)
        right_layout.addWidget(result_group)
        
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([200, 700])
        
        layout.addWidget(splitter)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_import = QPushButton("📥 导入选中目标 (替换)")
        btn_import.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px 20px;")
        btn_import.clicked.connect(self.import_selected)
        btn_layout.addWidget(btn_import)
        
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
        # 加载历史记录
        self.refresh_history_list()
    
    def refresh_history_list(self):
        """刷新历史记录列表"""
        self.history_list.clear()
        histories = self.history_manager.get_fofa_history(limit=30)
        
        for h in histories:
            query = h.get('query', '')
            count = h.get('result_count', 0)
            time_str = h.get('search_time', '')[:16]  # 截取日期时间
            
            item = QListWidgetItem(f"[{count}] {query}")
            item.setToolTip(f"时间: {time_str}\n结果数: {count}\n语句: {query}")
            item.setData(Qt.UserRole, h)  # 存储完整记录
            self.history_list.addItem(item)
    
    def load_history_item(self, item):
        """双击加载历史记录"""
        history = item.data(Qt.UserRole)
        if history:
            self.query_input.setText(history.get('query', ''))
            
            # 加载历史结果到表格
            history_id = history.get('id')
            if history_id:
                results = self.history_manager.get_fofa_results(history_id)
                if results:
                    self.display_results(results)
                    self.status_label.setText(f"已加载历史记录，共 {len(results)} 条结果")
    
    def load_selected_history(self):
        """加载选中的历史记录"""
        item = self.history_list.currentItem()
        if item:
            self.load_history_item(item)
        else:
            QMessageBox.information(self, "提示", "请先选择一条历史记录")
    
    def show_history_context_menu(self, pos):
        """历史记录右键菜单"""
        item = self.history_list.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        load_action = menu.addAction("📥 加载")
        load_action.triggered.connect(lambda: self.load_history_item(item))
        
        delete_action = menu.addAction("🗑️ 删除")
        delete_action.triggered.connect(lambda: self.delete_history_item(item))
        
        menu.exec_(self.history_list.mapToGlobal(pos))
    
    def delete_history_item(self, item):
        """删除历史记录"""
        history = item.data(Qt.UserRole)
        if history:
            self.history_manager.delete_fofa_history(history.get('id'))
            self.refresh_history_list()
    
    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有搜索历史吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.history_manager.clear_fofa_history()
            self.refresh_history_list()
    
    def do_search(self):
        """执行搜索"""
        query = self.query_input.text().strip()
        if not query:
            QMessageBox.warning(self, "提示", "请输入搜索语句")
            return
        
        # 获取 FOFA 配置
        fofa_config = self.settings.get_fofa_config()
        if not fofa_config.get("api_key"):
            QMessageBox.warning(self, "提示", "请先在设置中配置 FOFA API")
            return
            
        # 获取数量
        try:
            size = int(self.size_combo.currentText())
        except ValueError:
            size = 100
        
        # 禁用搜索按钮
        self.btn_search.setEnabled(False)
        self.btn_search.setText("搜索中...")
        self.progress_bar.show()
        self.status_label.setText(f"正在搜索 (size={size})...")
        
        # 启动搜索线程
        self.search_thread = FofaSearchThread(
            fofa_config.get("api_url", ""),
            fofa_config.get("email", ""),
            fofa_config.get("api_key", ""),
            query,
            size # 使用选择的数量
        )
        self.search_thread.result_signal.connect(self.on_search_result)
        self.search_thread.error_signal.connect(self.on_search_error)
        self.search_thread.progress_signal.connect(self.on_search_progress)
        self.search_thread.start()
    
    def on_search_result(self, results):
        """搜索完成"""
        self.btn_search.setEnabled(True)
        self.btn_search.setText("🔍 搜索")
        self.progress_bar.hide()
        
        # 保存到历史记录
        query = self.query_input.text().strip()
        self.history_manager.add_fofa_history(query, len(results), results)
        self.refresh_history_list()
        
        # 保存当前结果
        self.current_results = results
        
        # 显示结果
        self.display_results(results)
        
        count = len(results)
        self.status_label.setText(f"搜索完成，共 {count} 条结果")
        self.count_label.setText(f"共 {count} 条结果")
    
    def display_results(self, results):
        """显示搜索结果"""
        # 暂停界面更新，提升大量数据插入性能
        self.result_table.setUpdatesEnabled(False)
        self.result_table.setRowCount(0)
        
        # 预分配行数
        self.result_table.setRowCount(len(results))
        
        for row, item in enumerate(results):
            # 复选框
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked)  # 默认选中
            
            host = item.get("host", "")
            chk_item.setData(Qt.UserRole, host)  # 存储目标 URL
            
            self.result_table.setItem(row, 0, chk_item)
            self.result_table.setItem(row, 1, QTableWidgetItem(host))
            self.result_table.setItem(row, 2, QTableWidgetItem(item.get("ip", "")))
            self.result_table.setItem(row, 3, QTableWidgetItem(str(item.get("port", ""))))
            self.result_table.setItem(row, 4, QTableWidgetItem(item.get("title", "")))
        
        # 恢复界面更新
        self.result_table.setUpdatesEnabled(True)
        self.count_label.setText(f"共 {len(results)} 条结果")
    
    def on_search_error(self, error):
        """搜索出错"""
        self.btn_search.setEnabled(True)
        self.btn_search.setText("🔍 搜索")
        self.progress_bar.hide()
        self.status_label.setText(f"搜索失败: {error}")
        QMessageBox.critical(self, "错误", error)
    
    def on_search_progress(self, msg):
        """更新进度"""
        self.status_label.setText(msg)
    
    def select_all(self):
        """全选"""
        for i in range(self.result_table.rowCount()):
            item = self.result_table.item(i, 0)
            if item:
                item.setCheckState(Qt.Checked)
    
    def deselect_all(self):
        """取消全选"""
        for i in range(self.result_table.rowCount()):
            item = self.result_table.item(i, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
    
    def import_selected(self):
        """导入选中的目标"""
        self.selected_targets = []
        for i in range(self.result_table.rowCount()):
            item = self.result_table.item(i, 0)
            if item and item.checkState() == Qt.Checked:
                target = item.data(Qt.UserRole)
                if target:
                    self.selected_targets.append(target)
        
        if not self.selected_targets:
            QMessageBox.warning(self, "提示", "请至少选择一个目标")
            return
        
        self.accept()
    
    def get_selected_targets(self) -> list:
        """获取选中的目标列表"""
        return self.selected_targets
