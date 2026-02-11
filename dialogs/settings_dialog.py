"""
设置弹窗 - 统一管理 AI、FOFA、扫描参数配置
使用 Tab 页分类，保持界面整洁
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox,
    QCheckBox, QGroupBox, QGridLayout, QMessageBox, QListWidget,
    QListWidgetItem, QFormLayout, QTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.settings_manager import get_settings


class SettingsDialog(QDialog):
    """
    统一设置弹窗
    包含 AI 配置、FOFA 配置、扫描参数三个 Tab 页
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
    
    # ============== AI 配置 Tab ==============
    
    def setup_ai_tab(self):
        layout = QVBoxLayout(self.ai_tab)
        
        # 预设选择区
        preset_group = QGroupBox("模型预设")
        preset_layout = QHBoxLayout()
        
        self.ai_preset_combo = QComboBox()
        self.ai_preset_combo.setMinimumWidth(200)
        self.ai_preset_combo.currentIndexChanged.connect(self.on_ai_preset_changed)
        preset_layout.addWidget(QLabel("选择预设:"))
        preset_layout.addWidget(self.ai_preset_combo)
        preset_layout.addStretch()
        
        btn_add_preset = QPushButton("➕ 添加")
        btn_add_preset.clicked.connect(self.add_ai_preset)
        preset_layout.addWidget(btn_add_preset)
        
        btn_del_preset = QPushButton("🗑️ 删除")
        btn_del_preset.clicked.connect(self.delete_ai_preset)
        preset_layout.addWidget(btn_del_preset)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # 配置编辑区
        config_group = QGroupBox("当前预设配置")
        config_layout = QFormLayout()
        
        self.ai_name_input = QLineEdit()
        self.ai_name_input.setPlaceholderText("预设名称，如：DeepSeek")
        config_layout.addRow("预设名称:", self.ai_name_input)
        
        self.ai_url_input = QLineEdit()
        self.ai_url_input.setPlaceholderText("https://api.deepseek.com")
        config_layout.addRow("API 地址:", self.ai_url_input)
        
        self.ai_model_input = QLineEdit()
        self.ai_model_input.setPlaceholderText("deepseek-chat")
        config_layout.addRow("模型名称:", self.ai_model_input)
        
        self.ai_key_input = QLineEdit()
        self.ai_key_input.setEchoMode(QLineEdit.Password)
        self.ai_key_input.setPlaceholderText("sk-...")
        config_layout.addRow("API 密钥:", self.ai_key_input)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # 提示
        tip = QLabel("💡 提示：支持 OpenAI 兼容接口（DeepSeek、通义千问、本地 Ollama 等）")
        tip.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(tip)
        
        layout.addStretch()
    
    def on_ai_preset_changed(self, index):
        """切换预设时更新编辑区"""
        if index < 0:
            return
        presets = self.settings.get_ai_presets()
        if index < len(presets):
            preset = presets[index]
            self.ai_name_input.setText(preset.get("name", ""))
            self.ai_url_input.setText(preset.get("api_url", ""))
            self.ai_model_input.setText(preset.get("model", ""))
            self.ai_key_input.setText(preset.get("api_key", ""))
    
    def add_ai_preset(self):
        """添加新预设"""
        presets = self.settings.get_ai_presets()
        new_preset = {
            "name": f"新预设 {len(presets) + 1}",
            "api_url": "",
            "model": "",
            "api_key": ""
        }
        presets.append(new_preset)
        self.settings.save_ai_presets(presets)
        self.load_ai_presets()
        self.ai_preset_combo.setCurrentIndex(len(presets) - 1)
    
    def delete_ai_preset(self):
        """删除当前预设"""
        index = self.ai_preset_combo.currentIndex()
        presets = self.settings.get_ai_presets()
        if len(presets) <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留一个预设")
            return
        if 0 <= index < len(presets):
            del presets[index]
            self.settings.save_ai_presets(presets)
            self.load_ai_presets()
    
    def load_ai_presets(self):
        """加载 AI 预设到下拉框"""
        self.ai_preset_combo.blockSignals(True)
        self.ai_preset_combo.clear()
        presets = self.settings.get_ai_presets()
        for preset in presets:
            self.ai_preset_combo.addItem(preset.get("name", "未命名"))
        
        current_index = self.settings.get_current_ai_preset_index()
        if 0 <= current_index < len(presets):
            self.ai_preset_combo.setCurrentIndex(current_index)
        
        self.ai_preset_combo.blockSignals(False)
        self.on_ai_preset_changed(self.ai_preset_combo.currentIndex())
    
    def save_current_ai_preset(self):
        """保存当前编辑的预设"""
        index = self.ai_preset_combo.currentIndex()
        presets = self.settings.get_ai_presets()
        if 0 <= index < len(presets):
            presets[index] = {
                "name": self.ai_name_input.text().strip(),
                "api_url": self.ai_url_input.text().strip(),
                "model": self.ai_model_input.text().strip(),
                "api_key": self.ai_key_input.text().strip()
            }
            self.settings.save_ai_presets(presets)
            self.settings.set_current_ai_preset_index(index)
    
    # ============== FOFA 配置 Tab ==============
    
    def setup_fofa_tab(self):
        layout = QVBoxLayout(self.fofa_tab)
        
        config_group = QGroupBox("FOFA API 配置")
        config_layout = QFormLayout()
        
        self.fofa_url_input = QLineEdit()
        self.fofa_url_input.setPlaceholderText("https://fofa.info/api/v1/search/all 或第三方 API 地址")
        config_layout.addRow("API 地址:", self.fofa_url_input)
        
        self.fofa_email_input = QLineEdit()
        self.fofa_email_input.setPlaceholderText("your@email.com（第三方 API 可能不需要）")
        config_layout.addRow("邮箱:", self.fofa_email_input)
        
        self.fofa_key_input = QLineEdit()
        self.fofa_key_input.setEchoMode(QLineEdit.Password)
        self.fofa_key_input.setPlaceholderText("FOFA API Key")
        config_layout.addRow("API Key:", self.fofa_key_input)
        
        self.fofa_size_spin = QSpinBox()
        self.fofa_size_spin.setRange(10, 10000)
        self.fofa_size_spin.setValue(100)
        self.fofa_size_spin.setToolTip("每次搜索返回的最大结果数")
        config_layout.addRow("结果数量:", self.fofa_size_spin)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # 测试按钮
        btn_test = QPushButton("🔗 测试连接")
        btn_test.clicked.connect(self.test_fofa_connection)
        layout.addWidget(btn_test)
        
        # 提示
        tip = QLabel("💡 提示：支持官方 FOFA API 和第三方兼容接口。如果使用第三方接口，请填写对应的 API 地址。")
        tip.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        
        layout.addStretch()
    
    def test_fofa_connection(self):
        """测试 FOFA API 连接"""
        from core.fofa_client import FofaClient
        try:
            client = FofaClient(
                self.fofa_url_input.text().strip(),
                self.fofa_email_input.text().strip(),
                self.fofa_key_input.text().strip()
            )
            if client.test_connection():
                QMessageBox.information(self, "成功", "FOFA API 连接成功！")
            else:
                QMessageBox.warning(self, "失败", "FOFA API 连接失败，请检查配置")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接测试失败: {str(e)}")
    
    # ============== 扫描参数 Tab ==============
    
    def setup_scan_tab(self):
        layout = QVBoxLayout(self.scan_tab)
        
        # 基础参数
        basic_group = QGroupBox("基础参数")
        basic_layout = QGridLayout()
        
        basic_layout.addWidget(QLabel("并发数 (RateLimit):"), 0, 0)
        self.scan_rate_spin = QSpinBox()
        self.scan_rate_spin.setRange(1, 1000)
        self.scan_rate_spin.setValue(150)
        self.scan_rate_spin.setToolTip("每秒最大请求数")
        basic_layout.addWidget(self.scan_rate_spin, 0, 1)
        
        basic_layout.addWidget(QLabel("批量数 (BulkSize):"), 0, 2)
        self.scan_bulk_spin = QSpinBox()
        self.scan_bulk_spin.setRange(1, 100)
        self.scan_bulk_spin.setValue(25)
        self.scan_bulk_spin.setToolTip("每个模板并发执行的主机数")
        basic_layout.addWidget(self.scan_bulk_spin, 0, 3)
        
        basic_layout.addWidget(QLabel("超时时间 (秒):"), 1, 0)
        self.scan_timeout_spin = QSpinBox()
        self.scan_timeout_spin.setRange(1, 600)
        self.scan_timeout_spin.setValue(5)
        basic_layout.addWidget(self.scan_timeout_spin, 1, 1)
        
        basic_layout.addWidget(QLabel("重试次数:"), 1, 2)
        self.scan_retries_spin = QSpinBox()
        self.scan_retries_spin.setRange(0, 10)
        self.scan_retries_spin.setValue(0)
        basic_layout.addWidget(self.scan_retries_spin, 1, 3)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 高级选项
        adv_group = QGroupBox("高级选项")
        adv_layout = QGridLayout()
        
        self.scan_redirects_check = QCheckBox("跟随重定向 (-fr)")
        adv_layout.addWidget(self.scan_redirects_check, 0, 0)
        
        self.scan_stop_check = QCheckBox("发现即停 (-spm)")
        adv_layout.addWidget(self.scan_stop_check, 0, 1)
        
        self.scan_no_httpx_check = QCheckBox("跳过探测 (-nh)")
        adv_layout.addWidget(self.scan_no_httpx_check, 1, 0)
        
        self.scan_verbose_check = QCheckBox("详细日志 (-v)")
        adv_layout.addWidget(self.scan_verbose_check, 1, 1)
        
        self.scan_native_check = QCheckBox("🚀 启用内置扫描器")
        self.scan_native_check.setStyleSheet("color: #27ae60; font-weight: bold;")
        self.scan_native_check.setToolTip("使用 Python 原生引擎替代 nuclei.exe，解决进程卡顿问题，支持基础 POC")
        adv_layout.addWidget(self.scan_native_check, 2, 0)
        
        adv_layout.addWidget(QLabel("默认代理:"), 3, 0)
        self.scan_proxy_input = QLineEdit()
        self.scan_proxy_input.setPlaceholderText("例如: http://127.0.0.1:8080")
        adv_layout.addWidget(self.scan_proxy_input, 3, 1)
        
        adv_group.setLayout(adv_layout)
        layout.addWidget(adv_group)
        
        # 提示
        tip = QLabel("💡 提示：这些参数将作为扫描任务的默认值，每次扫描时仍可单独调整。")
        tip.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(tip)
        
        layout.addStretch()
    
    # ============== 加载和保存 ==============
    
    def load_settings(self):
        """从设置管理器加载所有配置"""
        # AI 配置
        self.load_ai_presets()
        
        # FOFA 配置
        fofa = self.settings.get_fofa_config()
        self.fofa_url_input.setText(fofa.get("api_url", ""))
        self.fofa_email_input.setText(fofa.get("email", ""))
        self.fofa_key_input.setText(fofa.get("api_key", ""))
        self.fofa_size_spin.setValue(fofa.get("page_size", 100))
        
        # 扫描配置
        scan = self.settings.get_scan_config()
        self.scan_rate_spin.setValue(scan.get("rate_limit", 150))
        self.scan_bulk_spin.setValue(scan.get("bulk_size", 25))
        self.scan_timeout_spin.setValue(scan.get("timeout", 5))
        self.scan_retries_spin.setValue(scan.get("retries", 0))
        self.scan_redirects_check.setChecked(scan.get("follow_redirects", False))
        self.scan_stop_check.setChecked(scan.get("stop_at_first_match", False))
        self.scan_no_httpx_check.setChecked(scan.get("no_httpx", False))
        self.scan_verbose_check.setChecked(scan.get("verbose", False))
        self.scan_native_check.setChecked(scan.get("use_native_scanner", False))
        self.scan_proxy_input.setText(scan.get("proxy", ""))
    
    def save_and_close(self):
        """保存所有配置并关闭"""
        # 保存 AI 配置
        self.save_current_ai_preset()
        
        # 保存 FOFA 配置
        self.settings.save_fofa_config({
            "api_url": self.fofa_url_input.text().strip(),
            "email": self.fofa_email_input.text().strip(),
            "api_key": self.fofa_key_input.text().strip(),
            "page_size": self.fofa_size_spin.value()
        })
        
        # 保存扫描配置
        self.settings.save_scan_config({
            "rate_limit": self.scan_rate_spin.value(),
            "bulk_size": self.scan_bulk_spin.value(),
            "timeout": self.scan_timeout_spin.value(),
            "retries": self.scan_retries_spin.value(),
            "follow_redirects": self.scan_redirects_check.isChecked(),
            "stop_at_first_match": self.scan_stop_check.isChecked(),
            "no_httpx": self.scan_no_httpx_check.isChecked(),
            "verbose": self.scan_verbose_check.isChecked(),
            "use_native_scanner": self.scan_native_check.isChecked(),
            "proxy": self.scan_proxy_input.text().strip()
        })
        
        QMessageBox.information(self, "成功", "设置已保存")
        self.accept()
