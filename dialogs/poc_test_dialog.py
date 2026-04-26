"""
POC 快速测试弹窗 - 单目标单POC快速验证
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QGroupBox, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

import subprocess
import json
import os
import tempfile
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui_scale import scaled, scaled_style
from core.nuclei_runner import get_nuclei_path
from i18n import tr


class QuickTestThread(QThread):
    """快速测试后台线程"""
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(bool)  # True=发现漏洞, False=未发现
    
    def __init__(self, target: str, poc_path: str):
        super().__init__()
        self.target = target
        self.poc_path = poc_path
        self._is_running = True
    
    def run(self):
        # 获取 nuclei 路径
        nuclei_cmd = get_nuclei_path()
        
        try:
            cmd = [
                nuclei_cmd,
                "-u", self.target,
                "-t", self.poc_path,
                "-jsonl",
                "-timeout", "10",
                "-no-color"
            ]
            
            self.log_signal.emit(f"[*] {tr('poc.test.exec_cmd')}: {' '.join(cmd)}")
            self.log_signal.emit(f"[*] {tr('poc.test.target')}: {self.target}")
            self.log_signal.emit(f"[*] POC: {os.path.basename(self.poc_path)}")
            self.log_signal.emit("")
            
            # 隐藏控制台窗口
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=startupinfo,
                encoding='utf-8',
                errors='ignore'
            )
            
            found_vuln = False
            
            for line in iter(process.stdout.readline, ''):
                if not self._is_running:
                    process.terminate()
                    break
                
                line = line.strip()
                if line:
                    try:
                        result = json.loads(line)
                        if 'template-id' in result and 'matched-at' in result:
                            self.result_signal.emit(result)
                            found_vuln = True
                            self.log_signal.emit(f"[+] {tr('poc.test.vuln_found')}")
                        else:
                            self.log_signal.emit(f"[*] {line}")
                    except:
                        # 清理 ANSI 颜色代码
                        import re
                        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
                        self.log_signal.emit(f"[*] {clean_line}")
            
            process.wait()
            
            if found_vuln:
                self.log_signal.emit(f"\n[✓] {tr('poc.test.complete_found')}")
            else:
                self.log_signal.emit(f"\n[✗] {tr('poc.test.complete_not_found')}")
            
            self.finished_signal.emit(found_vuln)
            
        except FileNotFoundError:
            self.log_signal.emit(f"[!] {tr('poc.test.nuclei_not_found')}")
            self.finished_signal.emit(False)
        except Exception as e:
            self.log_signal.emit(f"[!] {tr('poc.test.error_occurred', error=str(e))}")
            self.finished_signal.emit(False)
    
    def stop(self):
        self._is_running = False


class POCTestDialog(QDialog):
    """
    POC 快速测试弹窗
    单目标 + 单 POC 快速验证
    """
    
    def __init__(self, poc_path: str = None, poc_name: str = None, parent=None, colors=None):
        super().__init__(parent)
        self.poc_path = poc_path
        self.poc_name = poc_name or (os.path.basename(poc_path) if poc_path else "")
        self.test_thread = None
        
        # 使用传入的颜色或默认颜色
        from core.fortress_style import FORTRESS_COLORS
        self.colors = colors if colors else FORTRESS_COLORS
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(tr("poc.test.title"))
        self.resize(scaled(700), scaled(550))
        self.setMinimumSize(scaled(500), scaled(400))
        
        # 应用 FORTRESS 样式
        from core.fortress_style import get_dialog_stylesheet, get_button_style, get_secondary_button_style
        self.setStyleSheet(get_dialog_stylesheet(self.colors))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(scaled(15))
        layout.setContentsMargins(scaled(20), scaled(20), scaled(20), scaled(20))
        
        # POC 信息
        poc_group = QGroupBox(tr("poc.test.poc_group"))
        poc_group.setStyleSheet(scaled_style(f"QGroupBox {{ color: {self.colors['text_primary']}; font-weight: bold; border: 1px solid {self.colors['nav_border']}; border-radius: 6px; margin-top: 6px; padding-top: 10px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}"))
        poc_layout = QHBoxLayout()
        
        self.poc_label = QLabel(self.poc_name or tr("poc.test.no_poc_selected"))
        self.poc_label.setStyleSheet(scaled_style(f"font-weight: bold; color: {self.colors['text_primary']};"))
        poc_layout.addWidget(self.poc_label)
        
        poc_layout.addStretch()
        
        btn_select_poc = QPushButton(tr("poc.test.select_poc"))
        btn_select_poc.setStyleSheet(get_secondary_button_style(self.colors))
        btn_select_poc.clicked.connect(self.select_poc)
        poc_layout.addWidget(btn_select_poc)
        
        poc_group.setLayout(poc_layout)
        layout.addWidget(poc_group)
        
        # 目标输入
        target_group = QGroupBox(tr("poc.test.target_group"))
        target_group.setStyleSheet(scaled_style(f"QGroupBox {{ color: {self.colors['text_primary']}; font-weight: bold; border: 1px solid {self.colors['nav_border']}; border-radius: 6px; margin-top: 6px; padding-top: 10px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}"))
        target_layout = QHBoxLayout()
        
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText(tr("poc.test.target_placeholder"))
        input_bg = self.colors.get('input_bg', '#1e293b' if self.colors.get('is_dark', False) else '#ffffff')
        
        self.target_input.setStyleSheet(scaled_style(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['nav_border']};
                border-radius: 4px;
                padding: 6px;
            }}
        """))
        target_layout.addWidget(self.target_input)
        
        self.btn_test = QPushButton(tr("poc.test.start"))
        self.btn_test.setStyleSheet(get_button_style('success', self.colors))
        self.btn_test.clicked.connect(self.start_test)
        target_layout.addWidget(self.btn_test)
        
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # 结果显示
        result_group = QGroupBox(tr("poc.test.result_group"))
        result_group.setStyleSheet(scaled_style(f"QGroupBox {{ color: {self.colors['text_primary']}; font-weight: bold; border: 1px solid {self.colors['nav_border']}; border-radius: 6px; margin-top: 6px; padding-top: 10px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}"))
        result_layout = QVBoxLayout()
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", scaled(10)))
        
        bg_color = "#1e1e1e" if self.colors.get('is_dark', True) else "#f8f9fa"
        text_color = "#dcdcdc" if self.colors.get('is_dark', True) else "#333333"
        border_color = self.colors['nav_border']
        
        self.result_text.setStyleSheet(scaled_style(f"""
            QTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 10px;
            }}
        """))
        result_layout.addWidget(self.result_text)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_clear = QPushButton(tr("common.clear"))
        btn_clear.setStyleSheet(get_secondary_button_style(self.colors))
        btn_clear.clicked.connect(self.result_text.clear)
        btn_layout.addWidget(btn_clear)

        btn_close = QPushButton(tr("common.close"))
        btn_close.setStyleSheet(get_secondary_button_style(self.colors))
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def select_poc(self):
        """选择 POC 文件"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, tr("poc.test.select_poc_file"), "", "YAML Files (*.yaml *.yml)")
        if file_path:
            self.poc_path = file_path
            self.poc_name = os.path.basename(file_path)
            self.poc_label.setText(self.poc_name)
    
    def start_test(self):
        """开始测试"""
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, tr("msg.hint"), tr("poc.test.please_input_target"))
            return

        if not self.poc_path:
            QMessageBox.warning(self, tr("msg.hint"), tr("poc.test.please_select_poc"))
            return
        
        # 禁用按钮
        self.btn_test.setEnabled(False)
        self.btn_test.setText(tr("poc.test.testing"))
        self.progress_bar.show()
        self.result_text.clear()
        
        # 启动测试线程
        self.test_thread = QuickTestThread(target, self.poc_path)
        self.test_thread.log_signal.connect(self.append_log)
        self.test_thread.result_signal.connect(self.on_vuln_found)
        self.test_thread.finished_signal.connect(self.on_test_finished)
        self.test_thread.start()
    
    def append_log(self, text):
        """追加日志"""
        self.result_text.append(text)
    
    def on_vuln_found(self, result):
        """发现漏洞"""
        self.result_text.append("")
        self.result_text.append("=" * 50)
        self.result_text.append(tr("poc.test.vuln_detail"))
        self.result_text.append(f"  {tr('poc.test.template')}: {result.get('template-id', 'N/A')}")
        self.result_text.append(f"  {tr('poc.test.target')}: {result.get('matched-at', 'N/A')}")
        self.result_text.append(f"  {tr('poc.test.severity')}: {result.get('info', {}).get('severity', 'N/A')}")
        if 'extracted-results' in result:
            self.result_text.append(f"  {tr('poc.test.extracted')}: {result['extracted-results']}")
        self.result_text.append("=" * 50)
    
    def on_test_finished(self, found_vuln):
        """测试完成"""
        self.btn_test.setEnabled(True)
        self.btn_test.setText(tr("poc.test.start"))
        self.progress_bar.hide()
