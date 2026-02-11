"""
POC 生成器对话框 - 支持多步骤请求
根据请求包、FOFA 语句和漏洞名称自动生成 Nuclei POC
"""
import os
import re
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPlainTextEdit, QPushButton, 
                             QComboBox, QGroupBox, QMessageBox, QFileDialog,
                             QFormLayout, QSplitter, QFrame, QApplication,
                             QScrollArea, QWidget, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from core.fortress_style import FORTRESS_COLORS, get_dialog_stylesheet, get_button_style, get_secondary_button_style


class StepWidget(QFrame):
    """单个请求步骤的可折叠组件"""
    
    delete_requested = pyqtSignal(object)  # 删除信号
    
    def __init__(self, step_number: int, parent=None, colors=None):
        super().__init__(parent)
        self.step_number = step_number
        self.colors = colors if colors else {}
        self.is_expanded = True  # 默认展开
        self.init_ui()
    
    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        
        nav_border = self.colors.get('nav_border', '#e5e7eb')
        content_bg = self.colors.get('content_bg', '#ffffff')
        
        # 如果是深色模式，StepWidget 背景要稍微亮一点或不同于主背景
        bg_color = content_bg
        if self.colors.get('is_dark', False):
             # 步骤卡片背景与主背景一致（深色）
             bg_color = self.colors.get('content_bg', '#1e293b')
        else:
             bg_color = 'white'

        self.setStyleSheet(f"""
            StepWidget {{
                background-color: {bg_color};
                background-color: {bg_color};
                border: 1px solid {nav_border};
                border-radius: 8px;
                margin: 2px;
            }}
            StepWidget:hover {{
                border-color: {self.colors.get('btn_primary', '#2563eb')};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # 头部：步骤标题 + 折叠/删除按钮
        header = QHBoxLayout()
        
        self.step_label = QLabel(f"步骤 {self.step_number}")
        self.step_label.setStyleSheet(f"""
            font-weight: bold; 
            font-size: 14px;
            color: {self.colors.get('text_primary', '#1f2937')};
        """)
        header.addWidget(self.step_label)
        
        header.addStretch()
        
        # 折叠按钮
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(28, 28)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        
        nav_hover = self.colors.get('nav_hover', '#f3f4f6')
        nav_border = self.colors.get('nav_border', '#e5e7eb')
        text_secondary = self.colors.get('text_secondary', '#6b7280')
        
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {nav_hover};
                border: 1px solid {nav_border};
                border-radius: 4px;
                font-size: 12px;
                color: {text_secondary};
            }}
            QPushButton:hover {{
                background-color: {nav_border};
            }}
        """)
        self.toggle_btn.clicked.connect(self.toggle_expand)
        header.addWidget(self.toggle_btn)
        
        # 删除按钮
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        
        btn_danger = self.colors.get('btn_danger', '#ef4444')
        bg_color = 'white' 
        if self.colors.get('is_dark', False):
             bg_color = 'transparent'
             
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg_color};
                border: 1px solid {btn_danger};
                border-radius: 4px;
                font-size: 12px;
                color: {btn_danger};
            }}
            QPushButton:hover {{
                background-color: {btn_danger};
                color: white;
            }}
        """)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        header.addWidget(self.delete_btn)
        
        layout.addLayout(header)
        
        # 内容区（可折叠）
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 5, 0, 0)
        content_layout.setSpacing(8)
        
        # 请求包输入
        req_label = QLabel("请求包:")
        text_secondary = self.colors.get('text_secondary', '#6b7280')
        req_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
        content_layout.addWidget(req_label)
        
        self.request_input = QPlainTextEdit()
        self.request_input.setPlaceholderText("""GET /api/endpoint HTTP/1.1
Host: example.com
User-Agent: Mozilla/5.0
Cookie: session=xxx

{"param": "value"}""")
        self.request_input.setFont(QFont("Consolas", 10))
        self.request_input.setMaximumHeight(100)
        content_layout.addWidget(self.request_input)
        
        # 响应包输入
        resp_label = QLabel("响应包（用于分析匹配规则）:")
        resp_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
        content_layout.addWidget(resp_label)
        
        self.response_input = QPlainTextEdit()
        self.response_input.setPlaceholderText("""HTTP/1.1 200 OK
Content-Type: application/json

{"success":true,"data":{...}}""")
        self.response_input.setFont(QFont("Consolas", 10))
        self.response_input.setMaximumHeight(80)
        content_layout.addWidget(self.response_input)
        
        # 响应判断规则 - 分开的输入框
        rule_layout = QVBoxLayout()
        rule_layout.setSpacing(5)
        
        # 关键词匹配
        keywords_row = QHBoxLayout()
        keywords_label = QLabel("关键词:")
        keywords_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
        keywords_label.setFixedWidth(60)
        keywords_row.addWidget(keywords_label)
        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("匹配关键词，多个用逗号分隔，如: success, token")
        keywords_row.addWidget(self.keywords_input)
        rule_layout.addLayout(keywords_row)
        
        # 状态码 + 正则（同一行）
        status_regex_row = QHBoxLayout()
        
        status_label = QLabel("状态码:")
        status_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
        status_label.setFixedWidth(60)
        status_regex_row.addWidget(status_label)
        self.status_input = QLineEdit()
        self.status_input.setPlaceholderText("如: 200")
        self.status_input.setMaximumWidth(100)
        status_regex_row.addWidget(self.status_input)
        
        status_regex_row.addSpacing(20)
        
        regex_label = QLabel("正则:")
        regex_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
        regex_label.setFixedWidth(40)
        status_regex_row.addWidget(regex_label)
        self.regex_input = QLineEdit()
        self.regex_input.setPlaceholderText("正则表达式，如: root:.*:0:0（留空表示不使用）")
        status_regex_row.addWidget(self.regex_input)
        
        rule_layout.addLayout(status_regex_row)
        content_layout.addLayout(rule_layout)
        
        layout.addWidget(self.content_widget)
    
    def toggle_expand(self):
        """切换折叠/展开"""
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        self.toggle_btn.setText("▼" if self.is_expanded else "▶")
    
    def collapse(self):
        """折叠"""
        self.is_expanded = False
        self.content_widget.setVisible(False)
        self.toggle_btn.setText("▶")
    
    def expand(self):
        """展开"""
        self.is_expanded = True
        self.content_widget.setVisible(True)
        self.toggle_btn.setText("▼")
    
    def update_step_number(self, number: int):
        """更新步骤序号"""
        self.step_number = number
        self.step_label.setText(f"步骤 {number}")
    
    def get_request_text(self) -> str:
        return self.request_input.toPlainText().strip()
    
    def get_response_text(self) -> str:
        return self.response_input.toPlainText().strip()
    
    def get_match_rule(self) -> str:
        """获取此步骤的响应判断规则（兼容旧格式）"""
        parts = []
        if self.keywords_input.text().strip():
            parts.append(self.keywords_input.text().strip())
        if self.status_input.text().strip():
            parts.append(f"status:{self.status_input.text().strip()}")
        if self.regex_input.text().strip():
            parts.append(f"regex:{self.regex_input.text().strip()}")
        return ", ".join(parts)
    
    def get_keywords(self) -> str:
        """获取关键词"""
        return self.keywords_input.text().strip()
    
    def get_status_code(self) -> str:
        """获取状态码"""
        return self.status_input.text().strip()
    
    def get_regex(self) -> str:
        """获取正则表达式"""
        return self.regex_input.text().strip()
    
    def set_keywords(self, value: str):
        """设置关键词"""
        self.keywords_input.setText(value)
    
    def set_status_code(self, value: str):
        """设置状态码"""
        self.status_input.setText(value)
    
    def set_regex(self, value: str):
        """设置正则表达式"""
        self.regex_input.setText(value)


class POCGeneratorDialog(QDialog):
    """POC 生成器对话框 - 支持多步骤请求"""
    
    MAX_STEPS = 10  # 最大步骤数
    
    def __init__(self, parent=None, colors=None):
        super().__init__(parent)
        self.setWindowTitle("POC 生成器")
        self.resize(1000, 750)
        self.colors = colors if colors else {}
        self.step_widgets = []  # 存储所有步骤组件
        # 重新定义输入框背景色 (Standard Gray)
        input_bg = self.colors.get('input_bg', '#ffffff')
        if self.colors.get('is_dark', False):
            input_bg = self.colors.get('table_header', '#334155') # Standard Gray
            
        self.setStyleSheet(get_dialog_stylesheet(self.colors) + f"""
            QGroupBox {{
                border: 1px solid {self.colors.get('nav_border', '#e5e7eb')};
            }}
            QGroupBox::title {{
                color: {self.colors.get('text_secondary', '#6b7280')};
            }}
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
                background-color: {input_bg};
                border: 1px solid {self.colors.get('nav_border', '#334155')};
            }}
        """)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("POC 生成器（支持多步骤）")
        btn_primary = self.colors.get('btn_primary', '#2563eb')
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {btn_primary};")
        layout.addWidget(title)
        
        subtitle = QLabel("根据请求包自动生成 Nuclei POC 模板，支持多步骤漏洞利用")
        text_secondary = self.colors.get('text_secondary', '#6b7280')
        subtitle.setStyleSheet(f"color: {text_secondary}; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # 主内容区
        splitter = QSplitter(Qt.Horizontal)
        
        # ===== 左侧：输入区域 =====
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)
        
        # 基本信息表单（紧凑布局）
        form_group = QGroupBox("基本信息")
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)
        
        # 第一行：漏洞名称
        row1 = QHBoxLayout()
        lbl1 = QLabel("漏洞名称:")
        lbl1.setFixedWidth(70)
        row1.addWidget(lbl1)
        self.vuln_name_input = QLineEdit()
        self.vuln_name_input.setPlaceholderText("例如：某某系统-接口名-SQL注入漏洞")
        row1.addWidget(self.vuln_name_input)
        form_layout.addLayout(row1)
        
        # 第二行：严重程度 + FOFA语句
        row2 = QHBoxLayout()
        lbl2 = QLabel("严重程度:")
        lbl2.setFixedWidth(70)
        row2.addWidget(lbl2)
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["high", "critical", "medium", "low", "info"])
        self.severity_combo.setFixedWidth(100)
        row2.addWidget(self.severity_combo)
        row2.addSpacing(10)
        row2.addWidget(QLabel("FOFA语句:"))
        self.fofa_input = QLineEdit()
        self.fofa_input.setPlaceholderText("例如：body=\"xxx\" || title=\"xxx\"")
        row2.addWidget(self.fofa_input)
        form_layout.addLayout(row2)
        
        # 第三行：漏洞描述
        row3 = QHBoxLayout()
        lbl3 = QLabel("漏洞描述:")
        lbl3.setFixedWidth(70)
        row3.addWidget(lbl3)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("漏洞危害描述（可选）")
        row3.addWidget(self.desc_input)
        form_layout.addLayout(row3)
        
        form_group.setLayout(form_layout)
        left_layout.addWidget(form_group)
        
        # ===== 步骤编辑区 =====
        steps_group = QGroupBox("请求步骤")
        steps_layout = QVBoxLayout()
        steps_layout.setSpacing(8)
        
        # 步骤标题行
        steps_header = QHBoxLayout()
        hint_label = QLabel("支持添加多个请求步骤以构建多步骤漏洞POC")
        hint_label.setStyleSheet(f"color: {text_secondary}; font-size: 11px;")
        steps_header.addWidget(hint_label)
        steps_header.addStretch()
        
        self.add_step_btn = QPushButton("添加步骤")
        self.add_step_btn.setCursor(Qt.PointingHandCursor)
        self.add_step_btn.setStyleSheet(get_button_style("info", self.colors))
        self.add_step_btn.clicked.connect(self.add_step)
        steps_header.addWidget(self.add_step_btn)
        steps_layout.addLayout(steps_header)
        
        # 步骤滚动区域
        self.steps_scroll = QScrollArea()
        self.steps_scroll.setWidgetResizable(True)
        nav_border = self.colors.get('nav_border', '#e5e7eb')
        content_bg = self.colors.get('content_bg', '#f8fafc')
        
        self.steps_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {nav_border};
                border-radius: 6px;
                background: {content_bg};
            }}
        """)
        
        self.steps_container = QWidget()
        self.steps_container.setStyleSheet(f"background: {content_bg};")
        self.steps_container_layout = QVBoxLayout(self.steps_container)
        self.steps_container_layout.setContentsMargins(5, 5, 5, 5)
        self.steps_container_layout.setSpacing(8)
        self.steps_container_layout.addStretch()
        
        self.steps_scroll.setWidget(self.steps_container)
        steps_layout.addWidget(self.steps_scroll, 1)
        
        # AI提示行（全局）
        ai_hint_row = QHBoxLayout()
        ai_hint_label = QLabel("AI提示:")
        ai_hint_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
        ai_hint_label.setFixedWidth(50)
        ai_hint_row.addWidget(ai_hint_label)
        
        self.global_ai_hint = QLineEdit()
        self.global_ai_hint.setPlaceholderText("可选：补充漏洞信息给AI，如漏洞类型、CVE编号、产品名等")
        ai_hint_row.addWidget(self.global_ai_hint)
        steps_layout.addLayout(ai_hint_row)
        
        # 分析按钮行
        analyze_row = QHBoxLayout()
        
        btn_auto_analyze = QPushButton("自动分析")
        btn_auto_analyze.setCursor(Qt.PointingHandCursor)
        btn_auto_analyze.setStyleSheet(get_button_style("success", self.colors))
        btn_auto_analyze.setToolTip("使用规则自动提取所有步骤响应中的特征关键词")
        btn_auto_analyze.clicked.connect(self.auto_analyze_response)
        analyze_row.addWidget(btn_auto_analyze)
        
        btn_ai_analyze = QPushButton("AI 分析")
        btn_ai_analyze.setCursor(Qt.PointingHandCursor)
        btn_ai_analyze.setStyleSheet(get_button_style("warning", self.colors))
        btn_ai_analyze.setToolTip("使用 AI 智能分析所有步骤的响应并生成匹配规则建议")
        btn_ai_analyze.clicked.connect(self.ai_analyze_response)
        analyze_row.addWidget(btn_ai_analyze)
        
        analyze_row.addStretch()
        steps_layout.addLayout(analyze_row)
        
        steps_group.setLayout(steps_layout)
        left_layout.addWidget(steps_group, 1)
        
        splitter.addWidget(left_panel)
        
        # ===== 右侧：预览区域 =====
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        preview_group = QGroupBox("POC 预览")
        preview_layout = QVBoxLayout()
        
        self.preview_output = QPlainTextEdit()
        self.preview_output.setReadOnly(True)
        self.preview_output.setFont(QFont("Consolas", 10))
        
        # 预览区域样式 - 确保深浅色模式都有良好的对比度
        if self.colors.get('is_dark', False):
            # 深色模式：灰色背景 + 浅色文字
            preview_bg = self.colors.get('table_header', '#334155')
            preview_text = '#e2e8f0'
        else:
            # 浅色模式：深色背景（代码编辑器风格） + 浅色文字
            preview_bg = '#1e1e2e'
            preview_text = '#cdd6f4'
        
        self.preview_output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {preview_bg};
                color: {preview_text};
                border: 1px solid {nav_border};
                border-radius: 4px;
            }}
        """)
        preview_layout.addWidget(self.preview_output)
        
        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([550, 450])
        
        layout.addWidget(splitter, 1)
        
        # ===== 按钮区域 =====
        btn_row = QHBoxLayout()
        
        btn_preview = QPushButton("生成预览")
        btn_preview.setCursor(Qt.PointingHandCursor)
        btn_preview.setStyleSheet(get_button_style("info", self.colors))
        btn_preview.clicked.connect(self.generate_preview)
        btn_row.addWidget(btn_preview)
        
        btn_row.addStretch()
        
        btn_save = QPushButton("保存 POC")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(get_button_style("success", self.colors))
        btn_save.clicked.connect(self.save_poc)
        btn_row.addWidget(btn_save)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(get_secondary_button_style(self.colors))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        
        layout.addLayout(btn_row)
        
        # 默认添加一个步骤
        self.add_step()
    
    def add_step(self):
        """添加新步骤"""
        if len(self.step_widgets) >= self.MAX_STEPS:
            QMessageBox.warning(self, "提示", f"最多支持 {self.MAX_STEPS} 个步骤")
            return
        
        step_num = len(self.step_widgets) + 1
        step_widget = StepWidget(step_num, colors=self.colors)
        step_widget.delete_requested.connect(self.delete_step)
        
        # 第一个步骤不显示删除按钮
        if step_num == 1 and len(self.step_widgets) == 0:
            step_widget.delete_btn.hide()
        
        # 插入到容器末尾（stretch之前）
        self.steps_container_layout.insertWidget(
            self.steps_container_layout.count() - 1,
            step_widget
        )
        self.step_widgets.append(step_widget)
        
        # 更新删除按钮可见性
        self.update_delete_buttons()
    
    def delete_step(self, step_widget: StepWidget):
        """删除步骤"""
        if len(self.step_widgets) <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留一个步骤")
            return
        
        self.step_widgets.remove(step_widget)
        self.steps_container_layout.removeWidget(step_widget)
        step_widget.deleteLater()
        
        # 重新编号
        for i, sw in enumerate(self.step_widgets, 1):
            sw.update_step_number(i)
        
        self.update_delete_buttons()
    
    def update_delete_buttons(self):
        """更新删除按钮的可见性"""
        for sw in self.step_widgets:
            if len(self.step_widgets) <= 1:
                sw.delete_btn.hide()
            else:
                sw.delete_btn.show()
    
    def parse_request(self, raw_request: str) -> dict:
        """解析原始请求包"""
        lines = raw_request.strip().split('\n')
        if not lines:
            return None
        
        first_line = lines[0].strip()
        parts = first_line.split(' ')
        if len(parts) < 2:
            return None
        
        method = parts[0]
        path = parts[1]
        
        headers = []
        body = ""
        body_start = False
        
        for i, line in enumerate(lines[1:], 1):
            line = line.rstrip('\r')
            if line == '' and not body_start:
                body_start = True
                continue
            if body_start:
                body += line + '\n'
            else:
                headers.append(line)
        
        body = body.rstrip('\n')
        
        return {
            'method': method,
            'path': path,
            'headers': headers,
            'body': body
        }
    
    def generate_poc_content(self) -> str:
        """生成多步骤 POC 内容"""
        vuln_name = self.vuln_name_input.text().strip()
        if not vuln_name:
            return "# 错误：请输入漏洞名称"
        
        # 收集所有步骤的请求
        raw_requests = []
        last_valid_step_widget = None
        
        for sw in self.step_widgets:
            req_text = sw.get_request_text()
            if req_text:
                raw_requests.append(req_text)
                last_valid_step_widget = sw
        
        if not raw_requests:
            return "# 错误：请至少在一个步骤中输入请求包"
        
        # 生成 POC ID - 必须只包含英文、数字、短横线、下划线
        # nuclei 要求 id 匹配: ^([a-zA-Z0-9]+[-_])*[a-zA-Z0-9]+$
        import hashlib
        # 先尝试提取英文部分
        poc_id = re.sub(r'[^a-zA-Z0-9_-]', '-', vuln_name)
        poc_id = re.sub(r'-+', '-', poc_id).strip('-')
        
        # 如果 ID 为空（全是中文），使用名称的 hash 生成唯一 ID
        if not poc_id or len(poc_id) < 3:
            hash_suffix = hashlib.md5(vuln_name.encode('utf-8')).hexdigest()[:8]
            poc_id = f"user-poc-{hash_suffix}"

        
        severity = self.severity_combo.currentText()
        fofa = self.fofa_input.text().strip()
        desc = self.desc_input.text().strip() or "该漏洞可能导致敏感信息泄露或系统被攻击。"
        
        # 从最后一个步骤的组件直接获取匹配条件
        match_words = ""
        match_status = "200"
        match_regex = ""
        
        if last_valid_step_widget:
            match_words = last_valid_step_widget.get_keywords()
            match_status = last_valid_step_widget.get_status_code() or "200"
            match_regex = last_valid_step_widget.get_regex()
        
        # 生成匹配器 - 符合Nuclei标准YAML格式
        matchers = []
        
        # 辅助函数：安全转义YAML字符串中的引号
        def escape_yaml_string(s):
            """转义YAML字符串中的特殊字符"""
            # 如果字符串包含双引号，使用单引号包裹并转义内部单引号
            if '"' in s:
                return "'" + s.replace("'", "''") + "'"
            else:
                return '"' + s + '"'
        
        if match_words:
            words = [w.strip().strip('"\'') for w in match_words.split(',') if w.strip()]
            if words:
                # 每个关键词独占一行，10空格缩进，正确处理引号
                words_yaml = '\n          - '.join([escape_yaml_string(w) for w in words])
                matchers.append(f'''- type: word
        part: body
        words:
          - {words_yaml}
        condition: and''')
        
        if match_status:
            matchers.append(f'''- type: status
        status:
          - {match_status}''')
        
        if match_regex:
            matchers.append(f'''- type: regex
        part: body
        regex:
          - '{match_regex}' ''')
        
        if len(matchers) > 1:
            matcher = "matchers-condition: and\n    matchers:\n      " + "\n      ".join(matchers)
        elif len(matchers) == 1:
            matcher = "matchers:\n      " + matchers[0]
        else:
            matcher = """matchers:
      - type: status
        status:
          - 200"""
        
        # 根据步骤数量生成不同格式
        if len(raw_requests) == 1:
            # 单步骤：使用传统 path 格式
            parsed = self.parse_request(raw_requests[0])
            if not parsed:
                return "# 错误：请求包格式不正确"
            
            headers_yaml = ""
            for header in parsed['headers']:
                if not header.lower().startswith('host:'):
                    if ':' in header:
                        key, value = header.split(':', 1)
                        headers_yaml += f'      {key.strip()}: "{value.strip()}"\n'
            
            method = parsed['method'].upper()
            path = parsed['path']
            body = parsed['body']
            
            if body:
                # 使用YAML块标量语法处理复杂的body内容，避免引号转义问题
                # 对body进行缩进处理，使其符合YAML块标量格式
                body_lines = body.split('\n')
                if len(body_lines) > 1 or "'" in body or '"' in body or '\\' in body:
                    # 多行body或包含特殊字符时，使用块标量语法
                    indented_body = '\n'.join(['      ' + line for line in body_lines])
                    body_yaml = f'|\n{indented_body}'
                else:
                    # 简单body直接使用双引号
                    body_yaml = f'"{body}"'
                
                poc_content = f'''id: {poc_id}

info:
  name: {vuln_name}
  author: UserGenerated
  severity: {severity}
  description: |-
    fofa: {fofa or "待填写"}
    {desc}
  tags: user-generated

http:
  - method: {method}
    path:
      - "{{{{BaseURL}}}}{path}"
    headers:
{headers_yaml.rstrip()}
    body: {body_yaml}

    {matcher}
'''
            else:
                poc_content = f'''id: {poc_id}

info:
  name: {vuln_name}
  author: UserGenerated
  severity: {severity}
  description: |-
    fofa: {fofa or "待填写"}
    {desc}
  tags: user-generated

http:
  - method: {method}
    path:
      - "{{{{BaseURL}}}}{path}"
    headers:
{headers_yaml.rstrip()}

    {matcher}
'''
        else:
            # 多步骤：所有请求放在同一个 raw 数组中（Nuclei标准格式）
            # 正确格式：
            # http:
            #   - raw:
            #       - |
            #         请求1
            #       - |
            #         请求2
            #     matchers:
            #       ...
            raw_items = []
            for idx, req in enumerate(raw_requests):
                lines = req.split('\n')
                modified_lines = []
                for line in lines:
                    line = line.rstrip('\r')
                    if line.lower().startswith('host:'):
                        modified_lines.append('Host: {{Hostname}}')
                    else:
                        modified_lines.append(line)
                modified_req = '\n'.join(modified_lines)
                # 每个请求按照YAML块标量格式缩进（8个空格）
                indented_req = modified_req.replace('\n', '\n        ')
                raw_items.append(f'''      - |
        {indented_req}''')
            
            # 将所有raw请求项合并
            raw_items_str = '\n'.join(raw_items)
            
            poc_content = f'''id: {poc_id}

info:
  name: {vuln_name}
  author: UserGenerated
  severity: {severity}
  description: |-
    fofa: {fofa or "待填写"}
    {desc}
    本POC包含 {len(raw_requests)} 个请求步骤
  tags: user-generated,multi-step

http:
  - raw:
{raw_items_str}

    cookie-reuse: true
    {matcher}
'''
        
        return poc_content
    
    def generate_preview(self):
        """生成预览"""
        content = self.generate_poc_content()
        self.preview_output.setPlainText(content)
    
    def save_poc(self):
        """保存 POC 文件"""
        vuln_name = self.vuln_name_input.text().strip()
        if not vuln_name:
            QMessageBox.warning(self, "错误", "请输入漏洞名称")
            return
        
        has_request = any(sw.get_request_text() for sw in self.step_widgets)
        if not has_request:
            QMessageBox.warning(self, "错误", "请至少在一个步骤中输入请求包")
            return
        
        content = self.generate_poc_content()
        if content.startswith("# 错误"):
            QMessageBox.warning(self, "错误", content.replace("# 错误：", ""))
            return
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_poc_dir = os.path.join(base_dir, "poc_library", "user_generated")
        
        if not os.path.exists(user_poc_dir):
            os.makedirs(user_poc_dir)
        
        safe_name = re.sub(r'[<>:"/\\|?*]', '-', vuln_name)
        safe_name = re.sub(r'-+', '-', safe_name).strip('-')
        filename = f"nuclei-{safe_name}.yaml"
        file_path = os.path.join(user_poc_dir, filename)
        
        if os.path.exists(file_path):
            reply = QMessageBox.question(
                self, "文件已存在",
                f"文件 {filename} 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            QMessageBox.information(
                self, "保存成功",
                f"POC 已保存到：\n{file_path}\n\n请刷新 POC 库以加载新 POC。"
            )
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存文件时出错：\n{str(e)}")
    
    def auto_analyze_response(self):
        """自动分析所有步骤的响应包"""
        all_responses = []
        for sw in self.step_widgets:
            resp = sw.get_response_text()
            if resp:
                all_responses.append(resp)
        
        if not all_responses:
            QMessageBox.warning(self, "提示", "请先在任意步骤中粘贴响应包内容")
            return
        
        response_text = all_responses[-1]
        
        status_code = ""
        status_match = re.search(r'HTTP/\d\.?\d?\s+(\d{3})', response_text)
        if status_match:
            status_code = status_match.group(1)
        
        parts = re.split(r'\r?\n\r?\n', response_text, 1)
        body = parts[1] if len(parts) > 1 else response_text
        
        keywords = []
        
        success_patterns = [
            (r'"success"\s*:\s*true', '"success":true'),
            (r'"code"\s*:\s*0[,}\s]', '"code":0'),
            (r'"status"\s*:\s*"?ok"?', 'status'),
            (r'"result"\s*:\s*"?success"?', 'result'),
            (r'"msg"\s*:\s*"成功"', '"msg":"成功"'),
        ]
        
        for pattern, keyword in success_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                keywords.append(keyword)
        
        sensitive_fields = ['token', 'password', 'admin', 'userName', 'userId', 'secret', 'key', 'session']
        for field in sensitive_fields:
            if re.search(rf'"{field}"\s*:', body, re.IGNORECASE):
                keywords.append(field)
        
        keywords = list(set(keywords))[:5]
        keywords_str = ", ".join(keywords)
        
        if not status_code and not keywords:
            QMessageBox.information(self, "分析结果", "未能自动提取有效特征，请手动填写匹配规则。")
            return
        
        msg = f"分析了 {len(all_responses)} 个响应包，结果如下：\n\n"
        if status_code:
            msg += f"• 状态码: {status_code}\n"
        if keywords:
            msg += f"• 关键词: {keywords_str}\n"
        msg += "\n是否采纳？"
        
        reply = QMessageBox.question(
            self, "确认采纳分析结果",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # 将结果填入最后一个步骤的判断规则
            if self.step_widgets:
                last_widget = self.step_widgets[-1]
                if keywords:
                    last_widget.set_keywords(keywords_str)
                if status_code:
                    last_widget.set_status_code(status_code)
                last_widget.set_regex("")
    
    def ai_analyze_response(self):
        """使用 AI 分析所有步骤的响应包"""
        steps_info = []
        for i, sw in enumerate(self.step_widgets, 1):
            req = sw.get_request_text()
            resp = sw.get_response_text()
            match_rule = sw.get_match_rule()  # 获取每个步骤的判断规则
            if req or resp:
                steps_info.append({
                    'step': i,
                    'request': req[:1000] if req else "",
                    'response': resp[:1500] if resp else "",
                    'match_rule': match_rule  # 用户指定的判断规则
                })
        
        if not steps_info:
            QMessageBox.warning(self, "提示", "请先在任意步骤中填写请求包或响应包")
            return
        
        vuln_name = self.vuln_name_input.text().strip() or "未命名漏洞"
        global_hint = self.global_ai_hint.text().strip()  # 全局AI提示
        
        steps_text = ""
        for info in steps_info:
            steps_text += f"\n=== 步骤 {info['step']} ===\n"
            if info['request']:
                steps_text += f"【请求】\n{info['request']}\n"
            if info['response']:
                steps_text += f"【响应】\n{info['response']}\n"
            if info['match_rule']:
                steps_text += f"【用户指定匹配规则】{info['match_rule']}\n"
        
        # 添加全局提示
        hint_text = ""
        if global_hint:
            hint_text = f"\n用户补充信息：{global_hint}\n请参考此信息来生成更准确的匹配规则。\n"
        
        # 保存步骤信息供AI结果处理使用
        self._ai_steps_info = steps_info
        
        prompt = f"""你是资深安全研究专家，擅长分析漏洞和编写 Nuclei POC。

**任务：分析多步骤漏洞利用场景，为每个步骤生成独立的判断规则**

漏洞名称：{vuln_name}
步骤数量：{len(steps_info)}
{hint_text}
{steps_text}

**请严格按以下格式返回（为每个有响应的步骤都生成判断规则）：**

步骤1: 关键词1, 关键词2, status:状态码
步骤2: 关键词, status:状态码
...

**格式说明：**
- 每行一个步骤的判断规则
- 关键词直接写，多个用逗号分隔
- 状态码格式：status:200
- 正则格式：regex:表达式（如无需正则则不写）

**分析原则：**
1. 为每个步骤分析其响应中的关键特征
2. 选择能证明该步骤执行成功的字段
3. 关注步骤间的关联（如第一步返回token，第二步使用token）
4. 避免选择通用字段如 Content-Type

**示例输出：**
步骤1: "code":0, status:200
步骤2: "success":true, token, status:200"""
        
        try:
            from core.settings_manager import get_settings
            from core.ai_client import AIClient
            
            settings = get_settings()
            presets = settings.get_ai_presets()
            current_index = settings.get_current_ai_preset_index()
            
            if not presets or current_index < 0 or current_index >= len(presets):
                QMessageBox.warning(self, "错误", "请先在设置中配置 AI 模型")
                return
            
            preset = presets[current_index]
            api_url = preset.get("api_url", "")
            api_key = preset.get("api_key", "")
            model = preset.get("model", "")
            
            if not api_key:
                QMessageBox.warning(self, "错误", "请先在设置中配置 AI API 密钥")
                return
            
            self.preview_output.setPlainText(f"正在调用 AI 分析 {len(steps_info)} 个步骤，请稍候...\n\n（正在后台处理）")
            
            from PyQt5.QtCore import QThread
            
            class AIAnalyzeThread(QThread):
                from PyQt5.QtCore import pyqtSignal
                result_signal = pyqtSignal(str)
                error_signal = pyqtSignal(str)
                
                def __init__(self, api_url, api_key, model, prompt):
                    super().__init__()
                    self.api_url = api_url
                    self.api_key = api_key
                    self.model = model
                    self.prompt = prompt
                
                def run(self):
                    try:
                        from core.ai_client import AIClient
                        ai = AIClient(self.api_url, self.api_key, self.model)
                        result = ai._call_api(self.prompt)
                        self.result_signal.emit(result)
                    except Exception as e:
                        self.error_signal.emit(str(e))
            
            self.ai_thread = AIAnalyzeThread(api_url, api_key, model, prompt)
            self.ai_thread.result_signal.connect(self._on_ai_result)
            self.ai_thread.error_signal.connect(self._on_ai_error)
            self.ai_thread.start()
            
        except Exception as e:
            QMessageBox.warning(self, "AI 分析失败", f"准备调用 AI 时出错：\n{str(e)}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self._is_closing = True
        
        if hasattr(self, 'ai_thread') and self.ai_thread.isRunning():
            try:
                self.ai_thread.result_signal.disconnect(self._on_ai_result)
                self.ai_thread.error_signal.disconnect(self._on_ai_error)
            except:
                pass
        
        super().closeEvent(event)
    
    def _on_ai_result(self, result):
        """处理 AI 返回结果 - 支持多步骤判断规则"""
        if not self.isVisible() or getattr(self, '_is_closing', False):
            return
        
        if not result:
            QMessageBox.warning(self, "AI 分析失败", "未能获取 AI 响应，请检查 AI 配置。")
            return
        
        self.preview_output.setPlainText(f"AI 分析结果：\n\n{result}")
        
        # 解析每个步骤的判断规则
        step_rules = {}
        for line in result.split('\n'):
            line = line.strip()
            # 匹配格式: 步骤1: xxx 或 步骤 1: xxx 或 Step 1: xxx
            match = re.match(r'步骤\s*(\d+)\s*[:：]\s*(.+)', line, re.IGNORECASE)
            if not match:
                match = re.match(r'Step\s*(\d+)\s*[:：]\s*(.+)', line, re.IGNORECASE)
            if match:
                step_num = int(match.group(1))
                rule_text = match.group(2).strip()
                # 过滤无效内容
                if rule_text and rule_text.lower() not in ['无', '留空', 'none', '']:
                    step_rules[step_num] = rule_text
        
        if not step_rules:
            QMessageBox.information(self, "AI 分析完成", 
                "AI 返回的结果格式不符合预期，已显示在预览区域，请手动填写判断规则。")
            return
        
        # 构建确认消息，标注每个步骤
        msg = "AI 分析结果如下，是否采纳？\n\n"
        for step_num, rule in sorted(step_rules.items()):
            msg += f"【步骤 {step_num}】{rule}\n"
        
        reply = QMessageBox.question(
            self, "确认采纳 AI 分析结果",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # 将结果填入对应步骤的判断规则输入框
            for step_num, rule in step_rules.items():
                # 步骤索引从0开始，step_num从1开始
                idx = step_num - 1
                if 0 <= idx < len(self.step_widgets):
                    sw = self.step_widgets[idx]
                    
                    # 解析 AI 返回的规则字符串
                    match_status = ""
                    match_regex = ""
                    match_words = ""
                    
                    # 提取 status:xxx
                    status_match = re.search(r'status[:\s]*(\d+)', rule, re.IGNORECASE)
                    if status_match:
                        match_status = status_match.group(1)
                        rule = re.sub(r'status[:\s]*\d+', '', rule, flags=re.IGNORECASE)
                    
                    # 提取 regex:xxx
                    regex_match = re.search(r'regex[:\s]*([^\s,]+)', rule, re.IGNORECASE)
                    if regex_match:
                        match_regex = regex_match.group(1)
                        rule = re.sub(r'regex[:\s]*[^\s,]+', '', rule, flags=re.IGNORECASE)
                    
                    # 剩余的作为关键词
                    match_words = rule.strip().strip(',').strip()
                    
                    sw.set_keywords(match_words)
                    sw.set_status_code(match_status)
                    sw.set_regex(match_regex)
    
    def _on_ai_error(self, error):
        """处理 AI 调用错误"""
        if not self.isVisible() or getattr(self, '_is_closing', False):
            return
        
        self.preview_output.setPlainText(f"AI 分析失败：{error}")
        QMessageBox.warning(self, "AI 分析失败", f"调用 AI 时出错：\n{error}")
