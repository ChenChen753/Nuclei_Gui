"""
漏洞报告预览/编辑对话框
用于生成和编辑补天SRC格式的漏洞报告
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox, QFileDialog, QMessageBox,
    QGroupBox, QSplitter, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import os
from datetime import datetime

# 导入报告生成器
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.vuln_report_generator import get_report_generator


class VulnReportDialog(QDialog):
    """漏洞报告预览/编辑对话框"""
    
    def __init__(self, vuln_data: dict, poc_path: str = None, parent=None):
        super().__init__(parent)
        # 获取颜色配置（如果有）
        self.colors = {}
        if parent:
             # 尝试从父窗口获取颜色配置，或者使用全局配置
             from main import FORTRESS_COLORS
             self.colors = FORTRESS_COLORS
        
        self.vuln_data = vuln_data
        self.poc_path = poc_path
        self.generator = get_report_generator()
        
        self.init_ui()
        self.generate_report()
    
    def init_ui(self):
        """初始化界面"""
        from core.fortress_style import apply_fortress_style, get_button_style
        
        self.setWindowTitle("漏洞报告生成器 - 补天SRC格式")
        self.setMinimumSize(800, 700)
        self.resize(900, 800)
        
        # 应用全局主题样式
        apply_fortress_style(self, self.colors)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 顶部信息区
        info_group = QGroupBox("漏洞信息")
        # 显式设置 GroupBox 样式以匹配主题
        info_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.colors.get('nav_border', '#e5e7eb')};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                color: {self.colors.get('text_primary', '#1f2937')};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        info_layout = QHBoxLayout(info_group)
        
        # 漏洞类型
        info_layout.addWidget(QLabel("漏洞类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "SQL注入", "XSS跨站脚本", "远程命令执行", "任意文件上传",
            "SSRF服务端请求伪造", "文件包含/路径遍历", "越权访问/认证绕过",
            "信息泄露", "弱口令/默认密码", "XXE外部实体注入",
            "未授权访问", "反序列化漏洞", "CSRF跨站请求伪造", "其他漏洞"
        ])
        self.type_combo.setMinimumWidth(180)
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        info_layout.addWidget(self.type_combo)
        
        info_layout.addSpacing(20)
        
        # 危害等级
        info_layout.addWidget(QLabel("危害等级:"))
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["严重", "高危", "中危", "低危", "信息"])
        self.severity_combo.setMinimumWidth(100)
        info_layout.addWidget(self.severity_combo)
        
        info_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新模板")
        refresh_btn.setStyleSheet(get_button_style("info", self.colors))
        refresh_btn.clicked.connect(self.refresh_template)
        info_layout.addWidget(refresh_btn)
        
        layout.addWidget(info_group)
        
        # 报告编辑区
        edit_group = QGroupBox("报告内容 (支持Markdown)")
        # 显式设置 GroupBox 样式
        edit_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.colors.get('nav_border', '#e5e7eb')};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                color: {self.colors.get('text_primary', '#1f2937')};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        edit_layout = QVBoxLayout(edit_group)
        
        self.report_edit = QTextEdit()
        self.report_edit.setFont(QFont("Consolas", 10))
        self.report_edit.setPlaceholderText("报告内容将在这里生成...")
        edit_layout.addWidget(self.report_edit)
        
        layout.addWidget(edit_group, 1)
        
        # 底部按钮区
        btn_layout = QHBoxLayout()
        
        # 复制按钮
        copy_btn = QPushButton("复制到剪贴板")
        copy_btn.setStyleSheet(get_button_style("success", self.colors))
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)
        
        # 导出按钮
        export_btn = QPushButton("导出报告")
        export_btn.setStyleSheet(get_button_style("primary", self.colors))
        export_btn.clicked.connect(self.export_report)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(get_button_style("warning", self.colors))
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def generate_report(self):
        """生成漏洞报告"""
        try:
            # 生成报告
            report = self.generator.generate_report(self.vuln_data, self.poc_path)
            self.report_edit.setText(report)
            
            # 识别并设置漏洞类型
            vuln_type = self.generator.identify_vuln_type(self.vuln_data)
            index = self.type_combo.findText(vuln_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            
            # 设置危害等级
            severity = self.vuln_data.get('severity', 'unknown')
            if isinstance(severity, str):
                severity_map = {
                    'critical': '严重',
                    'high': '高危',
                    'medium': '中危',
                    'low': '低危',
                    'info': '信息'
                }
                severity_cn = severity_map.get(severity.lower(), '中危')
                index = self.severity_combo.findText(severity_cn)
                if index >= 0:
                    self.severity_combo.setCurrentIndex(index)
                    
        except Exception as e:
            self.report_edit.setText(f"生成报告失败: {str(e)}")
    
    def on_type_changed(self, vuln_type: str):
        """漏洞类型变更时的处理"""
        # 可选：更新危害描述和修复建议
        pass
    
    def refresh_template(self):
        """刷新模板（根据选择的漏洞类型更新危害和修复建议）"""
        vuln_type = self.type_combo.currentText()
        
        # 获取当前报告内容
        report = self.report_edit.toPlainText()
        
        # 1. 替换表格中的漏洞分类
        # 寻找 "| **漏洞分类** | " 所在的行
        lines = report.split('\n')
        for i, line in enumerate(lines):
            if "| **漏洞分类** |" in line:
                # 替换该行内容
                lines[i] = f"| **漏洞分类** | {vuln_type} |"
                break
        report = '\n'.join(lines)
        
        # 2. 替换危害描述
        # 寻找 "### 描述漏洞过程" 和 "### Payload" 之间的内容
        harm_start = report.find("### 描述漏洞过程")
        payload_start = report.find("### Payload")
        
        if harm_start != -1 and payload_start != -1:
            # 加上标题长度
            harm_content_start = harm_start + len("### 描述漏洞过程") + 1
            new_harm = f"\n{self.generator.get_harm_description(vuln_type)}\n\n"
            report = report[:harm_content_start] + new_harm + report[payload_start:]

        # 3. 替换修复建议
        # 寻找 "## 三、 修复建议" 之后的内容
        fix_start = report.find("## 三、 修复建议")
        if fix_start != -1:
            fix_content_start = fix_start + len("## 三、 修复建议") + 1
            new_fix = f"\n```text\n{self.generator.get_fix_suggestion(vuln_type)}\n```\n"
            report = report[:fix_content_start] + new_fix
        
        self.report_edit.setText(report)
        QMessageBox.information(self, "提示", f"已更新为 {vuln_type} 类型的模板")
    
    def copy_to_clipboard(self):
        """复制报告到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.report_edit.toPlainText())
        QMessageBox.information(self, "成功", "报告已复制到剪贴板！\n可直接粘贴到补天平台。")
    
    def export_report(self):
        """导出报告为文件"""
        # 获取默认文件名
        template_id = self.vuln_data.get('template_id', self.vuln_data.get('template-id', 'vuln_report'))
        default_name = f"{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出漏洞报告",
            default_name,
            "Markdown文件 (*.md);;文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.report_edit.toPlainText())
                QMessageBox.information(self, "成功", f"报告已导出到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
