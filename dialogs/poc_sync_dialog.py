"""
POC 在线同步弹窗 - 从 nuclei-templates 同步 POC
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QGroupBox, QProgressBar, 
    QMessageBox, QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

import os
import sys
import zipfile
import shutil
import urllib.request
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SyncThread(QThread):
    """同步后台线程"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # 当前, 总数
    finished_signal = pyqtSignal(bool, str)  # 成功, 消息
    
    # GitHub 仓库地址
    REPO_URL = "https://github.com/projectdiscovery/nuclei-templates"
    ZIP_URL = "https://github.com/projectdiscovery/nuclei-templates/archive/refs/heads/main.zip"
    
    def __init__(self, target_dir: str, mirror_url: str = None):
        super().__init__()
        self.target_dir = target_dir
        self.mirror_url = mirror_url
        self._is_running = True
    
    def run(self):
        try:
            # 使用镜像或官方地址
            download_url = self.mirror_url or self.ZIP_URL
            
            self.log_signal.emit(f"[*] 开始从 GitHub 下载 nuclei-templates...")
            self.log_signal.emit(f"[*] 下载地址: {download_url}")
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, "templates.zip")
            
            # 下载 ZIP
            self.log_signal.emit("[*] 正在下载...")
            
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    downloaded = block_num * block_size
                    self.progress_signal.emit(downloaded, total_size)
            
            urllib.request.urlretrieve(download_url, zip_path, progress_hook)
            
            self.log_signal.emit("[*] 下载完成，正在解压...")
            
            # 解压
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 找到解压后的目录
            extracted_dir = None
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isdir(item_path) and item.startswith("nuclei-templates"):
                    extracted_dir = item_path
                    break
            
            if not extracted_dir:
                raise Exception("未找到解压后的模板目录")
            
            self.log_signal.emit("[*] 正在复制 POC 文件...")
            
            # 统计复制的文件数
            copied_count = 0
            yaml_files = []
            
            # 收集所有 YAML 文件
            for root, dirs, files in os.walk(extracted_dir):
                for file in files:
                    if file.endswith(('.yaml', '.yml')):
                        yaml_files.append(os.path.join(root, file))
            
            total_files = len(yaml_files)
            self.log_signal.emit(f"[*] 找到 {total_files} 个 POC 文件")
            
            # 确保目标目录存在
            os.makedirs(self.target_dir, exist_ok=True)
            
            # 复制文件
            for i, src_path in enumerate(yaml_files):
                if not self._is_running:
                    break
                
                filename = os.path.basename(src_path)
                dst_path = os.path.join(self.target_dir, filename)
                
                # 如果文件已存在，添加序号
                if os.path.exists(dst_path):
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(dst_path):
                        dst_path = os.path.join(self.target_dir, f"{base}_{counter}{ext}")
                        counter += 1
                
                shutil.copy2(src_path, dst_path)
                copied_count += 1
                
                if (i + 1) % 100 == 0:
                    self.log_signal.emit(f"[*] 已复制 {i + 1}/{total_files} 个文件")
                    self.progress_signal.emit(i + 1, total_files)
            
            # 清理临时文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            self.log_signal.emit(f"\n[✓] 同步完成！共复制 {copied_count} 个 POC 文件")
            self.finished_signal.emit(True, f"成功同步 {copied_count} 个 POC")
            
        except Exception as e:
            self.log_signal.emit(f"\n[!] 同步失败: {str(e)}")
            self.finished_signal.emit(False, str(e))
    
    def stop(self):
        self._is_running = False


class POCSyncDialog(QDialog):
    """
    POC 在线同步弹窗
    从 nuclei-templates 官方仓库同步 POC
    """
    
    def __init__(self, target_dir: str, parent=None, colors=None):
        super().__init__(parent)
        self.target_dir = target_dir
        self.colors = colors if colors else {}
        self.sync_thread = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("POC 在线同步")
        self.resize(650, 500)
        self.setMinimumSize(500, 350)
        
        # 应用 FORTRESS 样式
        # 应用 FORTRESS 样式
        from core.fortress_style import get_dialog_stylesheet, get_button_style, get_secondary_button_style
        self.setStyleSheet(get_dialog_stylesheet(self.colors))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 说明
        info_group = QGroupBox("同步说明")
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)
        
        info_label = QLabel(
            "从 GitHub nuclei-templates 官方仓库下载最新的 POC 模板。\n"
            "包含数千个各类漏洞检测 POC，涵盖 CVE、弱配置、信息泄露等。"
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        # 镜像地址（可选）
        mirror_layout = QHBoxLayout()
        mirror_layout.addWidget(QLabel("自定义下载地址 (可选):"))
        self.mirror_input = QLineEdit()
        self.mirror_input.setPlaceholderText("留空使用 GitHub 官方，如遇下载慢可填镜像地址")
        mirror_layout.addWidget(self.mirror_input)
        info_layout.addLayout(mirror_layout)
        
        # 目标目录
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("保存目录:"))
        self.dir_label = QLabel(self.target_dir)
        self.dir_label = QLabel(self.target_dir)
        btn_primary = self.colors.get('btn_primary', '#2563eb')
        self.dir_label.setStyleSheet(f"color: {btn_primary};")
        dir_layout.addWidget(self.dir_label)
        dir_layout.addStretch()
        info_layout.addLayout(dir_layout)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 进度
        progress_group = QGroupBox("同步进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMaximumHeight(180)
        bg_color = self.colors.get('input_bg', '#1e1e1e')
        text_color = self.colors.get('text_secondary', '#dcdcdc')
        border_color = self.colors.get('nav_border', '#3e4451')
        
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        progress_layout.addWidget(self.log_text)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        
        self.btn_sync = QPushButton("开始同步")
        self.btn_sync = QPushButton("开始同步")
        self.btn_sync.setStyleSheet(get_button_style('primary', self.colors))
        self.btn_sync.clicked.connect(self.start_sync)
        btn_layout.addWidget(self.btn_sync)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet(get_secondary_button_style(self.colors))
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def start_sync(self):
        """开始同步"""
        reply = QMessageBox.question(
            self, "确认同步",
            f"将从 GitHub 下载 nuclei-templates 到:\n{self.target_dir}\n\n"
            "这可能需要几分钟时间，确定继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("同步中...")
        self.log_text.clear()
        
        mirror = self.mirror_input.text().strip() or None
        
        self.sync_thread = SyncThread(self.target_dir, mirror)
        self.sync_thread.log_signal.connect(self.append_log)
        self.sync_thread.progress_signal.connect(self.update_progress)
        self.sync_thread.finished_signal.connect(self.on_sync_finished)
        self.sync_thread.start()
    
    def append_log(self, text):
        """追加日志"""
        self.log_text.append(text)
    
    def update_progress(self, current, total):
        """更新进度条"""
        if total > 0:
            percent = int(current * 100 / total)
            self.progress_bar.setValue(percent)
    
    def on_sync_finished(self, success, message):
        """同步完成"""
        self.btn_sync.setEnabled(True)
        self.btn_sync.setText("🔄 开始同步")
        
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "失败", f"同步失败: {message}")
