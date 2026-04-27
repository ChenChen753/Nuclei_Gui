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
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QCoreApplication
from PyQt5.QtGui import QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from i18n import tr
from core.paths import is_frozen
from core.ui_scale import scaled, scaled_style
from core.settings_manager import get_settings
from core.updater import (
    UpdateCheckThread, UpdateDownloadThread,
    get_current_version, PRESERVE_FILES, PRESERVE_DIRS,
    PACKAGE_WINDOWS_EXE
)


class NucleiDownloadThread(QThread):
    """Nuclei 下载线程"""
    progress_signal = pyqtSignal(str)
    progress_percent_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def run(self):
        try:
            self.progress_signal.emit(tr("settings.nuclei.checking"))
            self.progress_percent_signal.emit(0)

            from download_nuclei_with_progress import download_with_callback

            def on_progress(message, percent=None):
                if percent is not None:
                    self.progress_percent_signal.emit(int(percent))
                self.progress_signal.emit(str(message))

            if download_with_callback(on_progress):
                self.finished_signal.emit(True, tr("settings.nuclei.install_success"))
            else:
                self.finished_signal.emit(False, tr("settings.nuclei.install_failed"))
                
        except Exception as e:
            self.finished_signal.emit(False, tr("settings.nuclei.download_error", error=str(e)))


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
        self.setWindowTitle(tr("settings.title"))
        self.resize(scaled(600), scaled(500))
        self.setMinimumSize(scaled(500), scaled(400))
        
        layout = QVBoxLayout(self)
        
        # 创建 Tab 页
        self.tabs = QTabWidget()

        # Tab 1: 通用设置（语言等）
        self.general_tab = QWidget()
        self.setup_general_tab()
        self.tabs.addTab(self.general_tab, tr("settings.tab.general"))

        # Tab 2: AI 配置
        self.ai_tab = QWidget()
        self.setup_ai_tab()
        self.tabs.addTab(self.ai_tab, tr("settings.tab.ai"))

        # Tab 3: FOFA 配置
        self.fofa_tab = QWidget()
        self.setup_fofa_tab()
        self.tabs.addTab(self.fofa_tab, tr("settings.tab.fofa"))

        # Tab 4: 扫描参数
        self.scan_tab = QWidget()
        self.setup_scan_tab()
        self.tabs.addTab(self.scan_tab, tr("settings.tab.scan"))

        # Tab 5: Nuclei 管理
        self.nuclei_tab = QWidget()
        self.setup_nuclei_tab()
        self.tabs.addTab(self.nuclei_tab, tr("settings.tab.nuclei"))

        # Tab 6: 更新设置
        self.update_tab = QWidget()
        self.setup_update_tab()
        self.tabs.addTab(self.update_tab, tr("settings.tab.update"))

        layout.addWidget(self.tabs)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_save = QPushButton(tr("common.save"))
        btn_save.setStyleSheet(scaled_style("background-color: #27ae60; color: white; font-weight: bold; padding: 8px 20px;"))
        btn_save.clicked.connect(self.save_and_close)
        btn_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton(tr("common.cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
    
    def setup_ai_tab(self):
        """设置 AI 配置页面"""
        layout = QVBoxLayout(self.ai_tab)
        
        # 简化的 AI 配置
        config_group = QGroupBox(tr("settings.ai.group_title"))
        config_layout = QFormLayout()

        self.ai_url_input = QLineEdit()
        self.ai_url_input.setPlaceholderText("https://api.deepseek.com")
        config_layout.addRow(tr("settings.ai.api_url"), self.ai_url_input)

        self.ai_key_input = QLineEdit()
        self.ai_key_input.setEchoMode(QLineEdit.Password)
        self.ai_key_input.setPlaceholderText("API Key")
        config_layout.addRow(tr("settings.ai.api_key"), self.ai_key_input)

        self.ai_model_input = QLineEdit()
        self.ai_model_input.setPlaceholderText("deepseek-chat")
        config_layout.addRow(tr("settings.ai.model"), self.ai_model_input)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        layout.addStretch()
    
    def setup_fofa_tab(self):
        """设置 FOFA 配置页面"""
        layout = QVBoxLayout(self.fofa_tab)
        
        config_group = QGroupBox(tr("settings.fofa.group_title"))
        config_layout = QFormLayout()

        self.fofa_url_input = QLineEdit()
        self.fofa_url_input.setPlaceholderText("https://fofa.info/api/v1/search/all")
        config_layout.addRow(tr("settings.fofa.api_url"), self.fofa_url_input)

        self.fofa_email_input = QLineEdit()
        self.fofa_email_input.setPlaceholderText("your@email.com")
        config_layout.addRow(tr("settings.fofa.email"), self.fofa_email_input)

        self.fofa_key_input = QLineEdit()
        self.fofa_key_input.setEchoMode(QLineEdit.Password)
        self.fofa_key_input.setPlaceholderText("FOFA API Key")
        config_layout.addRow(tr("settings.fofa.api_key"), self.fofa_key_input)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        layout.addStretch()
    
    def setup_scan_tab(self):
        """设置扫描参数页面"""
        layout = QVBoxLayout(self.scan_tab)
        
        # 基础参数
        basic_group = QGroupBox(tr("settings.scan.basic_params"))
        basic_layout = QGridLayout()

        basic_layout.addWidget(QLabel(tr("settings.scan.concurrency")), 0, 0)
        self.scan_rate_spin = QSpinBox()
        self.scan_rate_spin.setRange(1, 1000)
        self.scan_rate_spin.setValue(150)
        basic_layout.addWidget(self.scan_rate_spin, 0, 1)
        
        basic_layout.addWidget(QLabel(tr("settings.scan.bulk_size")), 0, 2)
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
        info_group = QGroupBox(tr("settings.nuclei.system_info"))
        info_layout = QGridLayout()

        import platform
        system = platform.system()
        machine = platform.machine()
        info_layout.addWidget(QLabel(tr("settings.nuclei.os")), 0, 0)
        info_layout.addWidget(QLabel(f"{system} {machine}"), 0, 1)
        
        info_layout.addWidget(QLabel(tr("settings.nuclei.status")), 1, 0)
        self.nuclei_status_label = QLabel(tr("settings.nuclei.detecting"))
        info_layout.addWidget(self.nuclei_status_label, 1, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Nuclei 下载管理
        download_group = QGroupBox(tr("settings.nuclei.download_mgmt"))
        download_layout = QVBoxLayout()
        
        desc_label = QLabel(tr("settings.nuclei.description_html"))
        desc_label.setStyleSheet(scaled_style("color: #34495e; font-size: 12px; padding: 10px;"))
        download_layout.addWidget(desc_label)
        
        # 下载按钮
        btn_layout = QHBoxLayout()
        
        self.download_btn = QPushButton(tr("settings.nuclei.check_install"))
        self.download_btn.setStyleSheet(scaled_style("""
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
        """))
        self.download_btn.clicked.connect(self.download_nuclei)
        btn_layout.addWidget(self.download_btn)
        
        self.check_btn = QPushButton(tr("settings.nuclei.detect"))
        self.check_btn.setStyleSheet(scaled_style("""
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
        """))
        self.check_btn.clicked.connect(self.check_nuclei_status)
        btn_layout.addWidget(self.check_btn)
        
        download_layout.addLayout(btn_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(scaled_style("""
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
        """))
        download_layout.addWidget(self.progress_bar)
        
        # 进度显示
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(scaled_style("color: #7f8c8d; font-size: 11px; padding: 5px;"))
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
                self.nuclei_status_label.setText(tr("settings.nuclei.installed"))
                self.nuclei_status_label.setStyleSheet(scaled_style("color: #27ae60; font-weight: bold;"))
                self.download_btn.setText(tr("settings.nuclei.recheck"))
            else:
                self.nuclei_status_label.setText(tr("settings.nuclei.not_installed"))
                self.nuclei_status_label.setStyleSheet(scaled_style("color: #e74c3c; font-weight: bold;"))
                self.download_btn.setText(tr("settings.nuclei.check_install"))

        except Exception as e:
            self.nuclei_status_label.setText(tr("settings.nuclei.detect_failed", error=str(e)))
            self.nuclei_status_label.setStyleSheet(scaled_style("color: #e74c3c; font-weight: bold;"))
    
    def download_nuclei(self):
        """下载 Nuclei"""
        self.download_btn.setEnabled(False)
        self.progress_label.setText(tr("settings.nuclei.preparing_download"))
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
            QMessageBox.information(self, tr("msg.success"), message)
            self.progress_label.setText(tr("settings.nuclei.download_complete"))
            self.check_nuclei_status()
        else:
            QMessageBox.critical(self, tr("msg.failed"), message)
            self.progress_label.setText(tr("settings.nuclei.download_failed"))
    
    def load_settings(self):
        """加载设置"""
        # 加载语言设置
        from i18n import SUPPORTED_LANGUAGES
        current_lang = self.settings.get_language()
        lang_codes = list(SUPPORTED_LANGUAGES.keys())
        if current_lang in lang_codes:
            self.lang_combo.setCurrentIndex(lang_codes.index(current_lang))

        # 加载更新设置
        auto_update = self.settings.get_auto_check_update()
        self.auto_update_checkbox.setChecked(auto_update)

    def save_and_close(self):
        """保存设置并关闭"""
        # 保存语言设置
        from i18n import SUPPORTED_LANGUAGES, get_current_language, init_language
        lang_codes = list(SUPPORTED_LANGUAGES.keys())
        new_lang = lang_codes[self.lang_combo.currentIndex()]
        old_lang = get_current_language()
        self.settings.set_language(new_lang)

        # 保存更新设置
        self.settings.set_auto_check_update(self.auto_update_checkbox.isChecked())

        if new_lang != old_lang:
            init_language(new_lang)
            QMessageBox.information(self, tr("msg.success"), tr("settings.saved_restart_hint"))
        else:
            QMessageBox.information(self, tr("msg.success"), tr("settings.saved"))
        self.accept()

    def setup_general_tab(self):
        """设置通用配置页面（语言等）"""
        layout = QVBoxLayout(self.general_tab)

        # 语言设置
        lang_group = QGroupBox(tr("settings.general.language_group"))
        lang_layout = QFormLayout()

        from i18n import SUPPORTED_LANGUAGES
        self.lang_combo = QComboBox()
        for code, name in SUPPORTED_LANGUAGES.items():
            self.lang_combo.addItem(f"{name} ({code})")
        lang_layout.addRow(tr("settings.general.ui_language"), self.lang_combo)

        hint = QLabel(tr("settings.general.language_restart_hint"))
        hint.setStyleSheet(scaled_style("color: #7f8c8d; font-size: 11px;"))
        lang_layout.addRow("", hint)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        layout.addStretch()

    def setup_update_tab(self):
        """设置更新配置页面"""
        layout = QVBoxLayout(self.update_tab)

        # 当前版本信息
        version_group = QGroupBox(tr("settings.update.version_info"))
        version_layout = QGridLayout()

        version_layout.addWidget(QLabel(tr("settings.update.current_version")), 0, 0)
        self.current_version_label = QLabel(f"v{get_current_version()}")
        self.current_version_label.setStyleSheet(scaled_style("font-weight: bold; color: #2980b9;"))
        version_layout.addWidget(self.current_version_label, 0, 1)

        version_layout.addWidget(QLabel(tr("settings.update.latest_version")), 1, 0)
        self.latest_version_label = QLabel(tr("settings.update.not_checked"))
        self.latest_version_label.setStyleSheet(scaled_style("color: #7f8c8d;"))
        version_layout.addWidget(self.latest_version_label, 1, 1)

        version_group.setLayout(version_layout)
        layout.addWidget(version_group)

        # 更新设置
        settings_group = QGroupBox(tr("settings.update.settings_group"))
        settings_layout = QVBoxLayout()

        self.auto_update_checkbox = QCheckBox(tr("settings.update.auto_check"))
        self.auto_update_checkbox.setChecked(True)
        self.auto_update_checkbox.setToolTip(tr("settings.update.auto_check_tooltip"))
        settings_layout.addWidget(self.auto_update_checkbox)

        preserve_label = QLabel(tr("settings.update.preserve_data_html"))
        preserve_label.setStyleSheet(scaled_style("color: #34495e; font-size: 11px; padding: 10px; background: #ecf0f1; border-radius: 4px;"))
        settings_layout.addWidget(preserve_label)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # 更新操作
        action_group = QGroupBox(tr("settings.update.action_group"))
        action_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()

        self.check_update_btn = QPushButton(tr("settings.update.check_btn"))
        self.check_update_btn.setStyleSheet(scaled_style("""
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
        """))
        self.check_update_btn.clicked.connect(self.check_for_updates)
        btn_layout.addWidget(self.check_update_btn)

        self.do_update_btn = QPushButton(tr("settings.update.download_btn"))
        self.do_update_btn.setStyleSheet(scaled_style("""
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
        """))
        self.do_update_btn.clicked.connect(self.do_update)
        self.do_update_btn.setEnabled(False)
        btn_layout.addWidget(self.do_update_btn)

        action_layout.addLayout(btn_layout)

        # 更新进度条
        self.update_progress_bar = QProgressBar()
        self.update_progress_bar.setVisible(False)
        self.update_progress_bar.setStyleSheet(scaled_style("""
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
        """))
        action_layout.addWidget(self.update_progress_bar)

        # 状态标签
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet(scaled_style("color: #7f8c8d; font-size: 11px; padding: 5px;"))
        action_layout.addWidget(self.update_status_label)

        # 更新日志
        self.release_notes_text = QTextEdit()
        self.release_notes_text.setReadOnly(True)
        self.release_notes_text.setMaximumHeight(scaled(120))
        self.release_notes_text.setPlaceholderText(tr("settings.update.release_notes_placeholder"))
        self.release_notes_text.setStyleSheet(scaled_style("""
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 5px;
                font-size: 11px;
            }
        """))
        action_layout.addWidget(self.release_notes_text)

        action_group.setLayout(action_layout)
        layout.addWidget(action_group)

        layout.addStretch()

        # 存储下载信息
        self._update_download_url = None
        self._update_version = None
        self._update_package_type = None

    def check_for_updates(self):
        """检查更新"""
        self.check_update_btn.setEnabled(False)
        self.update_status_label.setText(tr("settings.update.checking"))
        self.latest_version_label.setText(tr("settings.update.checking_label"))
        self.latest_version_label.setStyleSheet(scaled_style("color: #f39c12;"))

        self.update_check_thread = UpdateCheckThread()
        self.update_check_thread.check_finished.connect(self.on_check_finished)
        self.update_check_thread.error_signal.connect(self.on_check_error)
        self.update_check_thread.start()

    def on_check_finished(self, has_update, latest_version, download_url, release_notes, package_type):
        """检查更新完成"""
        self.check_update_btn.setEnabled(True)
        self.latest_version_label.setText(f"v{latest_version}")
        self._update_package_type = package_type

        if has_update:
            self.latest_version_label.setStyleSheet(scaled_style("color: #27ae60; font-weight: bold;"))
            self.update_status_label.setText(tr("settings.update.new_version_found", version=latest_version))
            self.do_update_btn.setEnabled(True)
            self._update_download_url = download_url
            self._update_version = latest_version
        else:
            self.latest_version_label.setStyleSheet(scaled_style("color: #7f8c8d;"))
            self.update_status_label.setText(tr("settings.update.already_latest"))
            self.do_update_btn.setEnabled(False)
            self._update_download_url = None
            self._update_version = None

        self.release_notes_text.setText(release_notes if release_notes else tr("settings.update.no_release_notes"))

    def on_check_error(self, error_msg):
        """检查更新出错"""
        self.check_update_btn.setEnabled(True)
        self.latest_version_label.setText(tr("settings.update.check_failed"))
        self.latest_version_label.setStyleSheet(scaled_style("color: #e74c3c;"))
        self.update_status_label.setText(error_msg)
        self.do_update_btn.setEnabled(False)
        self._update_download_url = None
        self._update_version = None
        self._update_package_type = None

    def do_update(self):
        """执行更新"""
        if not self._update_download_url:
            QMessageBox.warning(self, tr("msg.warning"), tr("settings.update.no_download_url"))
            return

        confirm_body_key = (
            "settings.update.confirm_body_binary"
            if self._update_package_type == PACKAGE_WINDOWS_EXE
            else "settings.update.confirm_body"
        )

        reply = QMessageBox.question(
            self, tr("settings.update.confirm_title"),
            tr(confirm_body_key, version=self._update_version),
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
            self._update_version,
            self._update_package_type
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
            if self._update_package_type == PACKAGE_WINDOWS_EXE:
                QMessageBox.information(self, tr("settings.update.success_title"), message)
                self.update_status_label.setText(tr("settings.update.binary_closing"))
                self.do_update_btn.setEnabled(False)
                QTimer.singleShot(500, self.quit_for_binary_update)
                return

            QMessageBox.information(self, tr("settings.update.success_title"), message)
            self.update_status_label.setText(tr("settings.update.complete_restart"))
            # 询问是否立即重启
            reply = QMessageBox.question(
                self, tr("settings.update.restart_title"),
                tr("settings.update.restart_confirm"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.restart_application()
        else:
            QMessageBox.critical(self, tr("settings.update.failed_title"), message)
            self.update_status_label.setText(tr("settings.update.update_failed"))
            self.do_update_btn.setEnabled(True)

    def restart_application(self):
        """重启应用程序"""
        import sys
        import os
        python = sys.executable
        if is_frozen():
            os.execl(python, python)
        script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py"
        )
        os.execl(python, python, script)

    def quit_for_binary_update(self):
        """关闭应用，交给外部替换脚本完成 exe 更新。"""
        self.accept()
        QCoreApplication.quit()
