"""
POC 编辑器弹窗 - YAML 语法高亮编辑
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QMessageBox, QFileDialog, QPlainTextEdit,
    QWidget, QSplitter
)
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui_scale import scaled, scaled_style
from i18n import tr


class YAMLHighlighter(QSyntaxHighlighter):
    """YAML 语法高亮器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        
        # 关键字（Nuclei 特定）
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#c678dd"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = ['id', 'info', 'name', 'author', 'severity', 'description', 
                    'tags', 'reference', 'http', 'requests', 'matchers', 
                    'extractors', 'raw', 'path', 'method', 'body', 'headers',
                    'matchers-condition', 'type', 'words', 'regex', 'status',
                    'part', 'condition', 'stop-at-first-match']
        for word in keywords:
            pattern = QRegExp(f"^\\s*{word}:")
            self.highlighting_rules.append((pattern, keyword_format))
        
        # 字符串
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#98c379"))
        self.highlighting_rules.append((QRegExp('"[^"]*"'), string_format))
        self.highlighting_rules.append((QRegExp("'[^']*'"), string_format))
        
        # 数字
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#d19a66"))
        self.highlighting_rules.append((QRegExp("\\b\\d+\\b"), number_format))
        
        # 布尔值
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#56b6c2"))
        self.highlighting_rules.append((QRegExp("\\b(true|false)\\b"), bool_format))
        
        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#5c6370"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((QRegExp("#.*"), comment_format))
        
        # 严重程度
        severity_format = QTextCharFormat()
        severity_format.setForeground(QColor("#e06c75"))
        severity_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegExp("\\b(critical|high|medium|low|info)\\b"), severity_format))
        
        # 列表项
        list_format = QTextCharFormat()
        list_format.setForeground(QColor("#61afef"))
        self.highlighting_rules.append((QRegExp("^\\s*-\\s"), list_format))
    
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)


class POCEditorDialog(QDialog):
    """
    POC 编辑器弹窗
    支持 YAML 语法高亮和保存功能
    """
    
    def __init__(self, poc_path: str = None, parent=None, colors=None):
        super().__init__(parent)
        self.poc_path = poc_path
        self.is_modified = False
        
        # 使用传入的颜色或默认颜色
        from core.fortress_style import FORTRESS_COLORS
        self.colors = colors if colors else FORTRESS_COLORS
        
        self.init_ui()
        
        if poc_path:
            self.load_file(poc_path)
    
    def init_ui(self):
        self.setWindowTitle(tr("poc.editor_title"))
        self.resize(scaled(900), scaled(650))
        self.setMinimumSize(scaled(600), scaled(400))
        
        # 应用 FORTRESS 样式
        from core.fortress_style import get_dialog_stylesheet, get_button_style, get_secondary_button_style
        self.setStyleSheet(get_dialog_stylesheet(self.colors))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(scaled(15))
        layout.setContentsMargins(scaled(20), scaled(20), scaled(20), scaled(20))
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.path_label = QLabel(tr("poc.new_poc"))
        self.path_label.setStyleSheet(scaled_style(f"color: {self.colors['text_secondary']}; font-size: 13px;"))
        toolbar.addWidget(self.path_label)
        
        toolbar.addStretch()
        
        btn_new = QPushButton(tr("poc.new"))
        btn_new.setStyleSheet(get_secondary_button_style(self.colors))
        btn_new.clicked.connect(self.new_file)
        toolbar.addWidget(btn_new)

        btn_open = QPushButton(tr("poc.open"))
        btn_open.setStyleSheet(get_secondary_button_style(self.colors))
        btn_open.clicked.connect(self.open_file)
        toolbar.addWidget(btn_open)

        btn_save = QPushButton(tr("common.save"))
        btn_save.setStyleSheet(get_button_style('success', self.colors))
        btn_save.clicked.connect(self.save_file)
        toolbar.addWidget(btn_save)

        btn_save_as = QPushButton(tr("poc.save_as"))
        btn_save_as.setStyleSheet(get_secondary_button_style(self.colors))
        btn_save_as.clicked.connect(self.save_file_as)
        toolbar.addWidget(btn_save_as)
        
        layout.addLayout(toolbar)
        
        # 编辑区
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", scaled(11)))
        
        # 编辑器统一使用深色代码编辑器风格，确保良好的可读性
        # 深色背景 + 浅色文字，类似 VS Code 风格
        bg_color = "#1e1e2e"
        text_color = "#cdd6f4"
        border_color = self.colors['nav_border']
        
        self.editor.setStyleSheet(scaled_style(f"""
            QPlainTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 15px;
            }}
        """))
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.textChanged.connect(self.on_text_changed)
        
        # 应用语法高亮
        self.highlighter = YAMLHighlighter(self.editor.document())
        
        layout.addWidget(self.editor)
        
        # 模板提示
        template_tip = QLabel(tr("poc.save_tip"))
        template_tip.setStyleSheet(scaled_style(f"color: {self.colors['text_secondary']}; font-size: 12px;"))
        layout.addWidget(template_tip)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_template = QPushButton(tr("poc.insert_template"))
        btn_template.setStyleSheet(get_button_style('info', self.colors))
        btn_template.clicked.connect(self.insert_template)
        btn_layout.addWidget(btn_template)

        btn_close = QPushButton(tr("common.close"))
        btn_close.setStyleSheet(get_secondary_button_style(self.colors))
        btn_close.clicked.connect(self.close_editor)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def on_text_changed(self):
        """文本修改标记"""
        self.is_modified = True
        title = self.windowTitle()
        if not title.endswith("*"):
            self.setWindowTitle(title + " *")
    
    def load_file(self, path: str):
        """加载文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.editor.setPlainText(content)
            self.poc_path = path
            self.path_label.setText(os.path.basename(path))
            self.setWindowTitle(f"{tr('poc.editor_title')} - {os.path.basename(path)}")
            self.is_modified = False
        except Exception as e:
            QMessageBox.critical(self, tr("msg.error"), tr("poc.read_file_failed", error=str(e)))

    def new_file(self):
        """新建文件"""
        if self.is_modified:
            reply = QMessageBox.question(self, tr("msg.confirm"), tr("poc.unsaved_discard"),
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.editor.clear()
        self.poc_path = None
        self.path_label.setText(tr("poc.new_poc"))
        self.setWindowTitle(tr("poc.editor_title"))
        self.is_modified = False
    
    def open_file(self):
        """打开文件"""
        if self.is_modified:
            reply = QMessageBox.question(self, tr("msg.confirm"), tr("poc.unsaved_discard"),
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        file_path, _ = QFileDialog.getOpenFileName(self, tr("poc.open_file"), "", "YAML Files (*.yaml *.yml)")
        if file_path:
            self.load_file(file_path)
    
    def save_file(self):
        """保存文件"""
        if not self.poc_path:
            self.save_file_as()
            return
        
        try:
            with open(self.poc_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.is_modified = False
            self.setWindowTitle(f"{tr('poc.editor_title')} - {os.path.basename(self.poc_path)}")
            QMessageBox.information(self, tr("msg.success"), tr("poc.file_saved"))
        except Exception as e:
            QMessageBox.critical(self, tr("msg.error"), tr("poc.save_failed", error=str(e)))
    
    def save_file_as(self):
        """另存为"""
        file_path, _ = QFileDialog.getSaveFileName(self, tr("poc.save_as"), "new_poc.yaml", "YAML Files (*.yaml *.yml)")
        if file_path:
            self.poc_path = file_path
            self.path_label.setText(os.path.basename(file_path))
            self.save_file()
    
    def insert_template(self):
        """插入 POC 模板"""
        template = '''id: my-custom-poc

info:
  name: My Custom POC
  author: your-name
  severity: medium
  description: Description of the vulnerability
  tags: custom,web

http:
  - method: GET
    path:
      - "{{BaseURL}}/vulnerable-path"

    matchers-condition: and
    matchers:
      - type: word
        words:
          - "vulnerable_keyword"

      - type: status
        status:
          - 200
'''
        self.editor.setPlainText(template)
    
    def close_editor(self):
        """关闭编辑器"""
        if self.is_modified:
            reply = QMessageBox.question(self, tr("msg.confirm"), tr("poc.unsaved_discard"),
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
        self.accept()
