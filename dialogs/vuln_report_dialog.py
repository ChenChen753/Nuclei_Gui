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
from core.ui_scale import scaled, scaled_style
from i18n import tr


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
        
        self.setWindowTitle(tr("report.generator_title"))
        self.setMinimumSize(scaled(800), scaled(700))
        self.resize(scaled(900), scaled(800))
        
        # 应用全局主题样式
        apply_fortress_style(self, self.colors)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(scaled(10))
        
        # 顶部信息区
        info_group = QGroupBox(tr("report.vuln_info"))
        # 显式设置 GroupBox 样式以匹配主题
        info_group.setStyleSheet(scaled_style(f"""
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
        """))
        info_layout = QHBoxLayout(info_group)
        
        # 漏洞类型
        info_layout.addWidget(QLabel(tr("report.vuln_type_label")))
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            tr("report.vuln_type_sqli"), tr("report.vuln_type_xss"), tr("report.vuln_type_rce"),
            tr("report.vuln_type_upload"), tr("report.vuln_type_ssrf"), tr("report.vuln_type_lfi"),
            tr("report.vuln_type_auth_bypass"), tr("report.vuln_type_info_leak"),
            tr("report.vuln_type_weak_password"), tr("report.vuln_type_xxe"),
            tr("report.vuln_type_unauth"), tr("report.vuln_type_deserialization"),
            tr("report.vuln_type_csrf"), tr("report.vuln_type_other")
        ])
        self.type_combo.setMinimumWidth(scaled(180))
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        info_layout.addWidget(self.type_combo)
        
        info_layout.addSpacing(20)
        
        # 危害等级
        info_layout.addWidget(QLabel(tr("report.severity_label")))
        self.severity_combo = QComboBox()
        self.severity_combo.addItems([tr("severity.critical"), tr("severity.high"), tr("severity.medium"), tr("severity.low"), tr("severity.info")])
        self.severity_combo.setMinimumWidth(scaled(100))
        info_layout.addWidget(self.severity_combo)
        
        info_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton(tr("report.refresh_template"))
        refresh_btn.setStyleSheet(get_button_style("info", self.colors))
        refresh_btn.clicked.connect(self.refresh_template)
        info_layout.addWidget(refresh_btn)
        
        layout.addWidget(info_group)
        
        # 报告编辑区
        edit_group = QGroupBox(tr("report.content_markdown"))
        # 显式设置 GroupBox 样式
        edit_group.setStyleSheet(scaled_style(f"""
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
        """))
        edit_layout = QVBoxLayout(edit_group)
        
        self.report_edit = QTextEdit()
        self.report_edit.setFont(QFont("Consolas", scaled(10)))
        self.report_edit.setPlaceholderText(tr("report.content_placeholder"))
        edit_layout.addWidget(self.report_edit)
        
        layout.addWidget(edit_group, 1)
        
        # 底部按钮区
        btn_layout = QHBoxLayout()
        
        # 复制按钮
        copy_btn = QPushButton(tr("report.copy_to_clipboard"))
        copy_btn.setStyleSheet(get_button_style("success", self.colors))
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(copy_btn)
        
        # 导出按钮
        export_btn = QPushButton(tr("report.export_report"))
        export_btn.setStyleSheet(get_button_style("primary", self.colors))
        export_btn.clicked.connect(self.export_report)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton(tr("common.close"))
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
                    'critical': tr("severity.critical"),
                    'high': tr("severity.high"),
                    'medium': tr("severity.medium"),
                    'low': tr("severity.low"),
                    'info': tr("severity.info")
                }
                severity_cn = severity_map.get(severity.lower(), tr("severity.medium"))
                index = self.severity_combo.findText(severity_cn)
                if index >= 0:
                    self.severity_combo.setCurrentIndex(index)
                    
        except Exception as e:
            self.report_edit.setText(tr("report.generate_report_failed", error=str(e)))
    
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
        QMessageBox.information(self, tr("msg.hint"), tr("report.template_updated", vuln_type=vuln_type))
    
    def copy_to_clipboard(self):
        """复制报告到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.report_edit.toPlainText())
        QMessageBox.information(self, tr("msg.success"), tr("report.copied_for_butian"))
    
    def export_report(self):
        """导出报告为文件"""
        # 获取默认文件名
        template_id = self.vuln_data.get('template_id', self.vuln_data.get('template-id', 'vuln_report'))
        default_name = f"{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("report.export_vuln_report"),
            default_name,
            tr("report.file_filter_md")
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.report_edit.toPlainText())
                QMessageBox.information(self, tr("msg.success"), tr("report.exported_to", filepath=file_path))
            except Exception as e:
                QMessageBox.critical(self, tr("msg.error"), tr("report.export_failed", error=str(e)))
