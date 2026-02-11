# -*- coding: utf-8 -*-
"""
新建扫描对话框 - FORTRESS 风格
整合目标设置和 POC 选择功能
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QPlainTextEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLineEdit,
                             QComboBox, QFileDialog, QGroupBox, QWidget,
                             QSplitter, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# FORTRESS 风格颜色
# 移除静态定义的 FORTRESS_COLORS，改用动态传入



class NewScanDialog(QDialog):
    """新建扫描配置对话框"""
    
    def __init__(self, parent=None, poc_library=None, initial_pocs=None, colors=None):
        super().__init__(parent)
        self.colors = colors if colors else {}
        self.poc_library = poc_library
        self.selected_pocs = []
        self.initial_pocs = initial_pocs or []  # 初始选中的 POC 路径列表
        self.setWindowTitle("新建扫描任务")
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)
        self._init_ui()
        self._load_pocs()
    
    def _init_ui(self):
        """初始化界面"""
        # 从 colors 获取颜色，提供默认备选
        c = self.colors
        bg_color = c.get('content_bg', '#ffffff')
        text_primary = c.get('text_primary', '#1f2937')
        text_secondary = c.get('text_secondary', '#6b7280')
        border_color = c.get('nav_border', '#e5e7eb')
        btn_primary = c.get('btn_primary', '#2563eb')
        table_header = c.get('table_header', '#f9fafb')
        input_bg = c.get('table_header') if c.get('is_dark') else 'white' # 深色模式下输入框背景使用稍浅的颜色

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }}
            QLineEdit, QPlainTextEdit, QComboBox {{
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 12px;
                background-color: {input_bg};
                color: {text_primary};
                font-size: 13px;
            }}
            QLineEdit:focus, QPlainTextEdit:focus {{
                border-color: {btn_primary};
            }}
            QTableWidget {{
                border: 1px solid {border_color};
                border-radius: 6px;
                gridline-color: {border_color};
                background-color: {bg_color};
                color: {text_primary};
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QHeaderView::section {{
                background-color: {table_header};
                padding: 10px;
                border: none;
                border-bottom: 1px solid {border_color};
                font-weight: bold;
                color: {text_primary};
            }}
            QCheckBox, QLabel {{
                color: {text_primary};
            }}
            /* 复选框样式适配 (QTableWidget::indicator) */
            QTableWidget::indicator {{
                width: 18px;
                height: 18px;
                background-color: {input_bg};
                border: 1px solid {border_color};
                border-radius: 3px;
            }}
            QTableWidget::indicator:checked {{
                background-color: {btn_primary};
                border-color: {btn_primary};
                image: url(resources/check.svg);
            }}
            QTableWidget::indicator:checked:disabled {{
                background-color: {border_color};
                border-color: {border_color};
            }}
            /* 鼠标悬停效果 */
            QTableWidget::indicator:hover {{
                border-color: {btn_primary};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("配置扫描任务")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {text_primary};
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # 主内容区（左右分栏）
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：目标设置
        left_panel = QGroupBox("目标设置")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # 目标输入框
        self.txt_targets = QPlainTextEdit()
        self.txt_targets.setPlaceholderText("请输入目标 URL，每行一个\n例如：\nhttp://example.com\nhttps://test.site:8080/path")
        self.txt_targets.setMinimumHeight(200)
        left_layout.addWidget(self.txt_targets)
        
        # 导入按钮
        btn_import = self._create_button("从文件导入目标", "secondary")
        btn_import.clicked.connect(self._import_targets)
        left_layout.addWidget(btn_import)
        
        # 目标统计
        self.lbl_target_count = QLabel("已输入 0 个目标")
        self.lbl_target_count.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
        left_layout.addWidget(self.lbl_target_count)
        
        self.txt_targets.textChanged.connect(self._update_target_count)
        
        left_layout.addStretch()
        splitter.addWidget(left_panel)
        
        # 右侧：POC 选择
        right_panel = QGroupBox("POC 选择")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        
        # 搜索和筛选行
        filter_row = QHBoxLayout()
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("搜索 POC 名称/ID...")
        self.txt_search.textChanged.connect(self._filter_pocs)
        filter_row.addWidget(self.txt_search, 1)
        
        filter_row.addWidget(QLabel("严重级别:"))
        self.cmb_severity = QComboBox()
        self.cmb_severity.addItems(["全部", "critical", "high", "medium", "low", "info"])
        self.cmb_severity.setFixedWidth(120)
        self.cmb_severity.currentTextChanged.connect(self._filter_pocs)
        filter_row.addWidget(self.cmb_severity)
        
        right_layout.addLayout(filter_row)
        
        # POC 列表
        self.poc_table = QTableWidget()
        self.poc_table.setColumnCount(4)
        self.poc_table.setHorizontalHeaderLabels(["选择", "ID", "名称", "级别"])
        self.poc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.poc_table.setColumnWidth(0, 60)
        
        # ID 列：改为交互式并设置固定初始宽度，防止过长导致水平滚动
        self.poc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.poc_table.setColumnWidth(1, 280)
        
        # 名称列：自动填充剩余空间
        self.poc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        # 级别列：适应内容
        self.poc_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.poc_table.verticalHeader().setVisible(False)
        self.poc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.poc_table.setAlternatingRowColors(True)
        self.poc_table.setAlternatingRowColors(True)
        self.poc_table.doubleClicked.connect(self._on_poc_double_click)  # 双击查看 POC
        
        # 应用 FORTRESS 表格样式
        from core.fortress_style import get_table_stylesheet
        self.poc_table.setStyleSheet(get_table_stylesheet(self.colors))
        
        right_layout.addWidget(self.poc_table)
        
        # POC 操作按钮
        poc_btn_row = QHBoxLayout()
        
        btn_select_all = self._create_button("全选", "secondary")
        btn_select_all.clicked.connect(self._select_all_pocs)
        poc_btn_row.addWidget(btn_select_all)
        
        btn_deselect_all = self._create_button("取消全选", "secondary")
        btn_deselect_all.clicked.connect(self._deselect_all_pocs)
        poc_btn_row.addWidget(btn_deselect_all)
        
        poc_btn_row.addStretch()
        
        # 已选 POC 按钮（点击可查看并取消选择）
        self.btn_selected_pocs = QPushButton("已选择 0 个 POC")
        self.btn_selected_pocs.setStyleSheet(f"""
            QPushButton {{
                color: {btn_primary};
                background-color: transparent;
                border: none;
                font-size: 13px;
                text-decoration: underline;
            }}
            QPushButton:hover {{
                color: {c.get('btn_primary_hover', btn_primary)};
            }}
        """)
        self.btn_selected_pocs.setCursor(Qt.PointingHandCursor)
        self.btn_selected_pocs.clicked.connect(self._show_selected_pocs)
        poc_btn_row.addWidget(self.btn_selected_pocs)
        
        right_layout.addLayout(poc_btn_row)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 500])
        
        layout.addWidget(splitter, 1)
        
        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_cancel = self._create_button("取消", "secondary")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        
        # 加入队列按钮
        btn_queue = self._create_button("加入队列", "secondary")
        btn_queue.setMinimumWidth(100)
        btn_queue.clicked.connect(self._add_to_queue)
        btn_queue.setToolTip("将任务添加到扫描队列，稍后手动启动")
        btn_row.addWidget(btn_queue)
        
        btn_save = self._create_button("立即扫描", "primary")
        btn_save.setMinimumWidth(120)
        btn_save.clicked.connect(self._save_config)
        btn_row.addWidget(btn_save)
        
        layout.addLayout(btn_row)
        
        # 返回模式标识: 'scan' 立即扫描, 'queue' 加入队列
        # 初始化为 None，防止意外触发 accept 时默认执行扫描
        self.action_mode = None
    
    def _create_button(self, text, btn_type='primary'):
        """创建按钮"""
        btn = QPushButton(text)
        btn.setMinimumHeight(38)
        btn.setCursor(Qt.PointingHandCursor)
        
        c = self.colors
        if btn_type == 'primary':
            btn_primary = c.get('btn_primary', '#2563eb')
            btn_primary_hover = c.get('btn_primary_hover', '#1d4ed8')
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_primary};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 20px;
                }}
                QPushButton:hover {{
                    background-color: {btn_primary_hover};
                }}
            """)
        else:
            c = self.colors
            text_primary = c.get('text_primary', '#1f2937')
            border_color = c.get('nav_border', '#e5e7eb')
            bg_light = c.get('table_header', '#f9fafb')
            btn_bg = 'transparent' if c.get('is_dark') else 'white'
             
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    color: {text_primary};
                    border: 1px solid {border_color};
                    border-radius: 6px;
                    font-size: 13px;
                    padding: 8px 20px;
                }}
                QPushButton:hover {{
                    background-color: {bg_light};
                }}
            """)
        
        return btn
    
    def _load_pocs(self):
        """加载 POC 列表"""
        if not self.poc_library:
            return
        
        pocs = self.poc_library.get_all_pocs()
        self._render_poc_table(pocs)
    
    def _render_poc_table(self, pocs):
        """渲染 POC 表格"""
        self.poc_table.setUpdatesEnabled(False)
        self.poc_table.setRowCount(0)
        self.poc_table.setRowCount(len(pocs))
        
        # 使用 QTableWidgetItem 的 checkState 代替 QCheckBox，极大提高性能
        for row, poc in enumerate(pocs):
            poc_path = poc.get('path', '')
            
            # 选择列 (使用 item check state)
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            
            # 如果在初始列表中，设置为选中状态
            if poc_path in self.initial_pocs:
                chk_item.setCheckState(Qt.Checked)
            else:
                chk_item.setCheckState(Qt.Unchecked)
            
            # 存储路径到 user role
            chk_item.setData(Qt.UserRole, poc_path)
            self.poc_table.setItem(row, 0, chk_item)
            
            # ID
            id_item = QTableWidgetItem(poc.get('id', ''))
            id_item.setData(Qt.UserRole, poc_path)  # 存储路径用于双击查看
            self.poc_table.setItem(row, 1, id_item)
            
            # 名称
            self.poc_table.setItem(row, 2, QTableWidgetItem(poc.get('name', poc.get('id', ''))))
            
            # 严重程度
            severity = poc.get('severity', 'info')
            sev_item = QTableWidgetItem(severity)
            
            # 根据严重程度设置颜色
            colors = {
                'critical': '#9b59b6',
                'high': '#e74c3c',
                'medium': '#f97316',
                'low': '#3b82f6',
                'info': '#22c55e',
            }
            
            # 适配深色模式文字颜色
            fg_color = Qt.black
            if self.colors.get('is_dark'):
                fg_color = Qt.white
            
            sev_item.setForeground(fg_color)
            if severity in colors:
                from PyQt5.QtGui import QColor
                sev_item.setForeground(QColor(colors[severity]))
            self.poc_table.setItem(row, 3, sev_item)
        
        # 连接 itemChanged 信号以更新计数 (先断开以防重复连接)
        try:
            self.poc_table.itemChanged.disconnect(self._on_item_changed)
        except:
            pass
        self.poc_table.itemChanged.connect(self._on_item_changed)
        
        self.poc_table.setUpdatesEnabled(True)
        self._update_poc_count()
        
    def _on_item_changed(self, item):
        """当表格项改变时触发"""
        if item.column() == 0:
            self._update_poc_count()

    def _filter_pocs(self):
        """筛选 POC"""
        search_text = self.txt_search.text().lower()
        severity = self.cmb_severity.currentText()
        
        self.poc_table.setUpdatesEnabled(False)
        for row in range(self.poc_table.rowCount()):
            show = True
            
            # 搜索匹配
            if search_text:
                id_item = self.poc_table.item(row, 1)
                name_item = self.poc_table.item(row, 2)
                id_text = id_item.text().lower() if id_item else ""
                name_text = name_item.text().lower() if name_item else ""
                if search_text not in id_text and search_text not in name_text:
                    show = False
            
            # 严重程度筛选
            if severity != "全部":
                sev_item = self.poc_table.item(row, 3)
                if sev_item and sev_item.text() != severity:
                    show = False
            
            self.poc_table.setRowHidden(row, not show)
        self.poc_table.setUpdatesEnabled(True)
    
    def _select_all_pocs(self):
        """全选 POC"""
        self.poc_table.blockSignals(True) # 阻止信号，避免频繁更新计数
        for row in range(self.poc_table.rowCount()):
            if not self.poc_table.isRowHidden(row):
                item = self.poc_table.item(row, 0)
                if item:
                    item.setCheckState(Qt.Checked)
        self.poc_table.blockSignals(False)
        self._update_poc_count()
    
    def _deselect_all_pocs(self):
        """取消全选"""
        self.poc_table.blockSignals(True)
        for row in range(self.poc_table.rowCount()):
            item = self.poc_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        self.poc_table.blockSignals(False)
        self._update_poc_count()
    
    def _update_poc_count(self):
        """更新已选 POC 数量"""
        count = 0
        for row in range(self.poc_table.rowCount()):
            item = self.poc_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                count += 1
        self.btn_selected_pocs.setText(f"已选择 {count} 个 POC（点击查看）")
    
    def _show_selected_pocs(self):
        """显示已选 POC 列表弹窗，可取消选择"""
        # 获取已选中的 POC
        selected = []
        for row in range(self.poc_table.rowCount()):
            item = self.poc_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                id_item = self.poc_table.item(row, 1)
                name_item = self.poc_table.item(row, 2)
                poc_id = id_item.text() if id_item else ""
                poc_name = name_item.text() if name_item else ""
                selected.append((row, poc_id, poc_name))
        
        if not selected:
            QMessageBox.information(self, "提示", "当前未选择任何 POC")
            return
        
        # 创建弹窗
        dialog = QDialog(self)
        dialog.setWindowTitle(f"已选择的 POC ({len(selected)} 个)")
        dialog.resize(500, 400)
        
        # 简单样式适配
        c = self.colors
        bg = c.get('content_bg', '#ffffff')
        fg = c.get('text_primary', '#000000')
        btn_bg = c.get('btn_primary', '#2563eb')
        
        dialog.setStyleSheet(f"QDialog {{ background-color: {bg}; color: {fg}; }} QLabel {{ color: {fg}; }}")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(15, 15, 15, 15)
        
        tip = QLabel("点击列表项可取消选择该 POC：")
        layout.addWidget(tip)
        
        # 列表
        from PyQt5.QtWidgets import QListWidget, QListWidgetItem
        list_widget = QListWidget()
        list_widget.setStyleSheet(f"background-color: {c.get('table_row_alt', '#f9fafb')}; border: 1px solid {c.get('nav_border', '#e5e7eb')}; color: {fg};")
        
        for row, poc_id, poc_name in selected:
            item = QListWidgetItem(f"{poc_id} - {poc_name}")
            item.setData(Qt.UserRole, row) # 存储原始行号
            list_widget.addItem(item)
        
        def on_item_clicked(item):
            original_row = item.data(Qt.UserRole)
            # 取消选中主表格对应行
            main_item = self.poc_table.item(original_row, 0)
            if main_item:
                main_item.setCheckState(Qt.Unchecked)
            
            list_widget.takeItem(list_widget.row(item))
            dialog.setWindowTitle(f"已选择的 POC ({list_widget.count()} 个)")
            
            # 实时更新外面主界面的计数
            self._update_poc_count()
            
            if list_widget.count() == 0:
                dialog.accept()
        
        list_widget.itemClicked.connect(on_item_clicked)
        layout.addWidget(list_widget)
        
        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(dialog.accept)
        btn_close.setStyleSheet(f"padding: 6px 15px; border-radius: 4px; background-color: #e5e7eb; color: #333;")
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
        
        dialog.exec_()
    
    def _on_poc_double_click(self, index):
        """双击查看 POC"""
        row = index.row()
        id_item = self.poc_table.item(row, 1)
        if id_item:
            poc_path = id_item.data(Qt.UserRole)
            if poc_path:
                from dialogs.poc_editor_dialog import POCEditorDialog
                dialog = POCEditorDialog(poc_path, self)
                dialog.exec_()
    
    def _update_target_count(self):
        """更新目标数量"""
        text = self.txt_targets.toPlainText().strip()
        count = len([t for t in text.split('\n') if t.strip()]) if text else 0
        self.lbl_target_count.setText(f"已输入 {count} 个目标")
    
    def _import_targets(self):
        """从文件导入目标"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择目标文件", "", "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    targets = f.read()
                current = self.txt_targets.toPlainText()
                if current.strip():
                    self.txt_targets.setPlainText(current + "\n" + targets)
                else:
                    self.txt_targets.setPlainText(targets)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"读取文件失败：{str(e)}")
    
    def _add_to_queue(self):
        """加入队列"""
        targets = self.get_targets()
        pocs = self.get_selected_pocs()
        
        if not targets:
            QMessageBox.warning(self, "提示", "请输入扫描目标")
            return
        
        if not pocs:
            QMessageBox.warning(self, "提示", "请选择至少一个 POC")
            return
        
        self.action_mode = 'queue'
        self.accept()
    
    
    
    def _save_config(self):
        """保存配置并立即扫描"""
        targets = self.get_targets()
        pocs = self.get_selected_pocs()
        
        if not targets:
            QMessageBox.warning(self, "提示", "请输入扫描目标")
            return
        
        if not pocs:
            QMessageBox.warning(self, "提示", "请选择至少一个 POC")
            return
        
        self.action_mode = 'scan'
        self.accept()
    
    def get_action_mode(self):
        """获取操作模式"""
        return getattr(self, 'action_mode', None)
    
    def get_targets(self):
        """获取目标列表"""
        text = self.txt_targets.toPlainText().strip()
        if not text:
            return []
        return [t.strip() for t in text.split('\n') if t.strip()]
    
    def get_selected_pocs(self):
        """获取选中的 POC 路径列表"""
        pocs = []
        for row in range(self.poc_table.rowCount()):
            item = self.poc_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                path = item.data(Qt.UserRole)
                if path:
                    pocs.append(path)
        return pocs
