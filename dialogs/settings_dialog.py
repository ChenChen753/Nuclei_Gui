"""
设置弹窗 - 统一管理 AI、FOFA、扫描参数配置
使用 Tab 页分类，保持界面整洁
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox,
    QCheckBox, QGroupBox, QGridLayout, QMessageBox, QListWidget,
    QListWidgetItem, QFormLayout, QTextEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.settings_manager import get_settings
from core.updater import (
    UpdateCheckThread, UpdateDownloadThread,
    get_current_version, PRESERVE_FILES, PRESERVE_DIRS
)


class NucleiDownloadThread(QThread):
    """Nuclei 下载线程"""
    progress_signal = pyqtSignal(str)
    progress_percent_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def run(self):
        try:
            import subprocess
            import sys
            import os
            
            self.progress_signal.emit("正在检查 Nuclei...")
            self.progress_percent_signal.emit(0)
            
            # 调用带进度的下载脚本
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "download_nuclei_with_progress.py")
            
            if os.path.exists(script_path):
                # 实时读取输出
                process = subprocess.Popen([sys.executable, script_path],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT,
                                         text=True,
                                         bufsize=1,
                                         encoding='utf-8',
                                         errors='ignore')
                
                success = False
                error_output = []
                
                for line in iter(process.stdout.readline, ''):
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith("PROGRESS:"):
                        # 解析进度: PROGRESS:percent:message
                        parts = line.split(":", 2)
                        if len(parts) >= 3:
                            try:
                                percent = int(parts[1])
                                message = parts[2]
                                self.progress_percent_signal.emit(percent)
                                self.progress_signal.emit(message)
                                
                                if percent == 100 and "安装完成" in message:
                                    success = True
                            except ValueError:
                                pass
                    elif line.startswith("STATUS:"):
                        # 解析状态: STATUS:message
                        message = line[7:]  # 去掉 "STATUS:" 前缀
                        self.progress_signal.emit(message)
                    else:
                        # 其他输出作为错误信息收集
                        error_output.append(line)
                
                process.wait()
                
                if success or process.returncode == 0:
                    self.finished_signal.emit(True, "Nuclei 安装完成！")
                else:
                    error_msg = "\n".join(error_output) if error_output else "安装失败"
                    # 检查是否是网络问题
                    if "ProxyError" in error_msg or "ConnectionError" in error_msg or "网络错误" in error_msg:
                        self.finished_signal.emit(False,
                            "网络连接失败，请检查网络设置或代理配置。\n"
                            "您也可以手动下载 Nuclei：\n"
                            "1. 访问 https://github.com/projectdiscovery/nuclei/releases\n"
                            "2. 下载 nuclei_*_windows_amd64.zip\n"
                            "3. 解压后将 nuclei.exe 放入 bin/ 目录")
                    elif "未找到 Nuclei" in error_msg or "下载失败" in error_msg:
                        self.finished_signal.emit(False,
                            "未找到 Nuclei，请手动安装：\n\n"
                            "方法1 - 手动下载：\n"
                            "1. 访问 https://github.com/projectdiscovery/nuclei/releases\n"
                            "2. 下载适合您系统的版本\n"
                            "3. 解压后将可执行文件放入 bin/ 目录\n"
                            "4. 重命名为 nuclei.exe\n\n"
                            "方法2 - 使用 Go 安装：\n"
                            "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest")
                    else:
                        self.finished_signal.emit(False, f"安装失败: {error_msg}")
            else:
                self.finished_signal.emit(False, "找不到下载脚本 download_nuclei_with_progress.py")
                
        except subprocess.TimeoutExpired:
            self.finished_signal.emit(False, "下载超时，请检查网络连接")
        except Exception as e:
            self.finished_signal.emit(False, f"下载过程中出错: {str(e)}")


class SettingsDialog(QDialog):
    """
    统一设置弹窗
    包含 AI 配置、FOFA 配置、扫描参数、Nuclei 管理四个 Tab 页
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = get_settings()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        self.setWindowTitle("⚙️ 设置")
        self.resize(600, 500)
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 创建 Tab 页
        self.tabs = QTabWidget()
        
        # Tab 1: AI 配置
        self.ai_tab = QWidget()
        self.setup_ai_tab()
        self.tabs.addTab(self.ai_tab, "🤖 AI 配置")
        
        # Tab 2: FOFA 配置
        self.fofa_tab = QWidget()
        self.setup_fofa_tab()
        self.tabs.addTab(self.fofa_tab, "🔍 FOFA 配置")
        
        # Tab 3: 扫描参数
        self.scan_tab = QWidget()
        self.setup_scan_tab()
        self.tabs.addTab(self.scan_tab, "📡 扫描参数")
        
        # Tab 4: Nuclei 管理
        self.nuclei_tab = QWidget()
        self.setup_nuclei_tab()
        self.tabs.addTab(self.nuclei_tab, "⚡ Nuclei 管理")

        # Tab 5: 更新设置
        self.update_tab = QWidget()
        self.setup_update_tab()
        self.tabs.addTab(self.update_tab, "🔄 更新设置")

        layout.addWidget(self.tabs)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_save = QPushButton("💾 保存")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px 20px;")
        btn_save.clicked.connect(self.save_and_close)
        btn_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
    
    def setup_ai_tab(self):
        """设置 AI 配置页面"""
        layout = QVBoxLayout(self.ai_tab)
        
        # 简化的 AI 配置
        config_group = QGroupBox("AI 配置")
        config_layout = QFormLayout()
        
        self.ai_url_input = QLineEdit()
        self.ai_url_input.setPlaceholderText("https://api.deepseek.com")
        config_layout.addRow("API 地址:", self.ai_url_input)
        
        self.ai_key_input = QLineEdit()
        self.ai_key_input.setEchoMode(QLineEdit.Password)
        self.ai_key_input.setPlaceholderText("API Key")
        config_layout.addRow("API Key:", self.ai_key_input)
        
        self.ai_model_input = QLineEdit()
        self.ai_model_input.setPlaceholderText("deepseek-chat")
        config_layout.addRow("模型:", self.ai_model_input)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        layout.addStretch()
    
    def setup_fofa_tab(self):
        """设置 FOFA 配置页面"""
        layout = QVBoxLayout(self.fofa_tab)
        
        config_group = QGroupBox("FOFA API 配置")
        config_layout = QFormLayout()
        
        self.fofa_url_input = QLineEdit()
        self.fofa_url_input.setPlaceholderText("https://fofa.info/api/v1/search/all")
        config_layout.addRow("API 地址:", self.fofa_url_input)
        
        self.fofa_email_input = QLineEdit()
        self.fofa_email_input.setPlaceholderText("your@email.com")
        config_layout.addRow("邮箱:", self.fofa_email_input)
        
        self.fofa_key_input = QLineEdit()
        self.fofa_key_input.setEchoMode(QLineEdit.Password)
        self.fofa_key_input.setPlaceholderText("FOFA API Key")
        config_layout.addRow("API Key:", self.fofa_key_input)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        layout.addStretch()
    
    def setup_scan_tab(self):
        """设置扫描参数页面"""
        layout = QVBoxLayout(self.scan_tab)
        
        # 基础参数
        basic_group = QGroupBox("基础参数")
        basic_layout = QGridLayout()
        
        basic_layout.addWidget(QLabel("并发数:"), 0, 0)
        self.scan_rate_spin = QSpinBox()
        self.scan_rate_spin.setRange(1, 1000)
        self.scan_rate_spin.setValue(150)
        basic_layout.addWidget(self.scan_rate_spin, 0, 1)
        
        basic_layout.addWidget(QLabel("批量数:"), 0, 2)
        self.scan_bulk_spin = QSpinBox()
        self.scan_bulk_spin.setRange(1, 100)
        self.scan_bulk_spin.setValue(25)
        basic_layout.addWidget(self.scan_bulk_spin, 0, 3)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        layout.addStretch()
    
    def setup_nuclei_tab(self):
        """设置 Nuclei 管理页面"""
        layout = QVBoxLayout(self.nuclei_tab)
        
        # 系统信息
        info_group = QGroupBox("系统信息")
        info_layout = QGridLayout()
        
        import platform
        system = platform.system()
        machine = platform.machine()
        info_layout.addWidget(QLabel("操作系统:"), 0, 0)
        info_layout.addWidget(QLabel(f"{system} {machine}"), 0, 1)
        
        info_layout.addWidget(QLabel("Nuclei 状态:"), 1, 0)
        self.nuclei_status_label = QLabel("检测中...")
        info_layout.addWidget(self.nuclei_status_label, 1, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Nuclei 下载管理
        download_group = QGroupBox("Nuclei 下载管理")
        download_layout = QVBoxLayout()
        
        desc_label = QLabel("""
        <b>Nuclei 扫描引擎管理</b><br>
        • 自动检测系统中已安装的 Nuclei<br>
        • 提供详细的安装指导<br>
        • 支持多种安装方式<br>
        • 跨平台兼容性检查
        """)
        desc_label.setStyleSheet("color: #34495e; font-size: 12px; padding: 10px;")
        download_layout.addWidget(desc_label)
        
        # 下载按钮
        btn_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("🔧 检查/安装 Nuclei")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.download_btn.clicked.connect(self.download_nuclei)
        btn_layout.addWidget(self.download_btn)
        
        self.check_btn = QPushButton("检测 Nuclei")
        self.check_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.check_btn.clicked.connect(self.check_nuclei_status)
        btn_layout.addWidget(self.check_btn)
        
        download_layout.addLayout(btn_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        download_layout.addWidget(self.progress_bar)
        
        # 进度显示
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 5px;")
        download_layout.addWidget(self.progress_label)
        
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        layout.addStretch()
        
        # 初始检测
        self.check_nuclei_status()
    
    def check_nuclei_status(self):
        """检测 Nuclei 状态"""
        try:
            from core.nuclei_runner import get_nuclei_path
            import os
            
            nuclei_path = get_nuclei_path()
            
            if os.path.exists(nuclei_path):
                self.nuclei_status_label.setText("[OK] 已安装")
                self.nuclei_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.download_btn.setText("重新检查")
            else:
                self.nuclei_status_label.setText("[FAIL] 未安装")
                self.nuclei_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.download_btn.setText("🔧 检查/安装 Nuclei")
                
        except Exception as e:
            self.nuclei_status_label.setText(f"[FAIL] 检测失败: {str(e)}")
            self.nuclei_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
    
    def download_nuclei(self):
        """下载 Nuclei"""
        self.download_btn.setEnabled(False)
        self.progress_label.setText("准备下载...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.download_thread = NucleiDownloadThread()
        self.download_thread.progress_signal.connect(self.progress_label.setText)
        self.download_thread.progress_percent_signal.connect(self.progress_bar.setValue)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.start()
    
    def on_download_finished(self, success, message):
        """下载完成回调"""
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.progress_label.setText("下载完成")
            self.check_nuclei_status()
        else:
            QMessageBox.critical(self, "失败", message)
            self.progress_label.setText("下载失败")
    
    def load_settings(self):
        """加载设置"""
        # 加载更新设置
        auto_update = self.settings.get_auto_check_update()
        self.auto_update_checkbox.setChecked(auto_update)

    def save_and_close(self):
        """保存设置并关闭"""
        # 保存更新设置
        self.settings.set_auto_check_update(self.auto_update_checkbox.isChecked())
        QMessageBox.information(self, "成功", "设置已保存")
        self.accept()

    def setup_update_tab(self):
        """设置更新配置页面"""
        layout = QVBoxLayout(self.update_tab)

        # 当前版本信息
        version_group = QGroupBox("版本信息")
        version_layout = QGridLayout()

        version_layout.addWidget(QLabel("当前版本:"), 0, 0)
        self.current_version_label = QLabel(f"v{get_current_version()}")
        self.current_version_label.setStyleSheet("font-weight: bold; color: #2980b9;")
        version_layout.addWidget(self.current_version_label, 0, 1)

        version_layout.addWidget(QLabel("最新版本:"), 1, 0)
        self.latest_version_label = QLabel("未检查")
        self.latest_version_label.setStyleSheet("color: #7f8c8d;")
        version_layout.addWidget(self.latest_version_label, 1, 1)

        version_group.setLayout(version_layout)
        layout.addWidget(version_group)

        # 更新设置
        settings_group = QGroupBox("更新设置")
        settings_layout = QVBoxLayout()

        self.auto_update_checkbox = QCheckBox("启动时自动检查更新")
        self.auto_update_checkbox.setChecked(True)
        self.auto_update_checkbox.setToolTip("关闭后需要手动点击检查更新按钮")
        settings_layout.addWidget(self.auto_update_checkbox)

        preserve_label = QLabel(
            "<b>更新时保留的数据:</b><br>"
            "• 扫描历史数据库 (scan_history.db, history.db)<br>"
            "• 自定义 POC (poc_library/custom, poc_library/user_generated)<br>"
            "• 配置文件和日志"
        )
        preserve_label.setStyleSheet("color: #34495e; font-size: 11px; padding: 10px; background: #ecf0f1; border-radius: 4px;")
        settings_layout.addWidget(preserve_label)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # 更新操作
        action_group = QGroupBox("更新操作")
        action_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()

        self.check_update_btn = QPushButton("🔍 检查更新")
        self.check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.check_update_btn.clicked.connect(self.check_for_updates)
        btn_layout.addWidget(self.check_update_btn)

        self.do_update_btn = QPushButton("⬇️ 下载更新")
        self.do_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.do_update_btn.clicked.connect(self.do_update)
        self.do_update_btn.setEnabled(False)
        btn_layout.addWidget(self.do_update_btn)

        action_layout.addLayout(btn_layout)

        # 更新进度条
        self.update_progress_bar = QProgressBar()
        self.update_progress_bar.setVisible(False)
        self.update_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
        """)
        action_layout.addWidget(self.update_progress_bar)

        # 状态标签
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 5px;")
        action_layout.addWidget(self.update_status_label)

        # 更新日志
        self.release_notes_text = QTextEdit()
        self.release_notes_text.setReadOnly(True)
        self.release_notes_text.setMaximumHeight(120)
        self.release_notes_text.setPlaceholderText("更新日志将在检查更新后显示...")
        self.release_notes_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 5px;
                font-size: 11px;
            }
        """)
        action_layout.addWidget(self.release_notes_text)

        action_group.setLayout(action_layout)
        layout.addWidget(action_group)

        layout.addStretch()

        # 存储下载信息
        self._update_download_url = None
        self._update_version = None

    def check_for_updates(self):
        """检查更新"""
        self.check_update_btn.setEnabled(False)
        self.update_status_label.setText("正在检查更新...")
        self.latest_version_label.setText("检查中...")
        self.latest_version_label.setStyleSheet("color: #f39c12;")

        self.update_check_thread = UpdateCheckThread()
        self.update_check_thread.check_finished.connect(self.on_check_finished)
        self.update_check_thread.error_signal.connect(self.on_check_error)
        self.update_check_thread.start()

    def on_check_finished(self, has_update, latest_version, download_url, release_notes):
        """检查更新完成"""
        self.check_update_btn.setEnabled(True)
        self.latest_version_label.setText(f"v{latest_version}")

        if has_update:
            self.latest_version_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.update_status_label.setText(f"发现新版本 v{latest_version}，可以更新！")
            self.do_update_btn.setEnabled(True)
            self._update_download_url = download_url
            self._update_version = latest_version
        else:
            self.latest_version_label.setStyleSheet("color: #7f8c8d;")
            self.update_status_label.setText("当前已是最新版本")
            self.do_update_btn.setEnabled(False)

        self.release_notes_text.setText(release_notes if release_notes else "无更新说明")

    def on_check_error(self, error_msg):
        """检查更新出错"""
        self.check_update_btn.setEnabled(True)
        self.latest_version_label.setText("检查失败")
        self.latest_version_label.setStyleSheet("color: #e74c3c;")
        self.update_status_label.setText(error_msg)

    def do_update(self):
        """执行更新"""
        if not self._update_download_url:
            QMessageBox.warning(self, "警告", "没有可用的更新下载地址")
            return

        reply = QMessageBox.question(
            self, "确认更新",
            f"确定要更新到 v{self._update_version} 吗？\n\n"
            "更新过程中会保留您的:\n"
            "• 扫描历史数据\n"
            "• 自定义 POC\n"
            "• 配置文件\n\n"
            "更新完成后需要重启程序。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.check_update_btn.setEnabled(False)
        self.do_update_btn.setEnabled(False)
        self.update_progress_bar.setVisible(True)
        self.update_progress_bar.setValue(0)

        self.update_download_thread = UpdateDownloadThread(
            self._update_download_url,
            self._update_version
        )
        self.update_download_thread.progress_signal.connect(self.on_update_progress)
        self.update_download_thread.finished_signal.connect(self.on_update_finished)
        self.update_download_thread.start()

    def on_update_progress(self, percent, message):
        """更新进度"""
        self.update_progress_bar.setValue(percent)
        self.update_status_label.setText(message)

    def on_update_finished(self, success, message):
        """更新完成"""
        self.check_update_btn.setEnabled(True)
        self.update_progress_bar.setVisible(False)

        if success:
            QMessageBox.information(self, "更新成功", message)
            self.update_status_label.setText("更新完成，请重启程序")
            # 询问是否立即重启
            reply = QMessageBox.question(
                self, "重启程序",
                "更新已完成，是否立即重启程序？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.restart_application()
        else:
            QMessageBox.critical(self, "更新失败", message)
            self.update_status_label.setText("更新失败")
            self.do_update_btn.setEnabled(True)

    def restart_application(self):
        """重启应用程序"""
        import sys
        import os
        python = sys.executable
        script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        os.execl(python, python, script)
