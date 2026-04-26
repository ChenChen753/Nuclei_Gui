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
from core.ui_scale import scaled, scaled_style
from i18n import tr


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
            
            self.log_signal.emit(f"[*] {tr('poc.sync.start_download')}")
            self.log_signal.emit(tr("poc.sync.download_url", download_url=download_url))
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, "templates.zip")
            
            # 下载 ZIP
            self.log_signal.emit(f"[*] {tr('poc.sync.downloading')}")
            
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    downloaded = block_num * block_size
                    self.progress_signal.emit(downloaded, total_size)
            
            urllib.request.urlretrieve(download_url, zip_path, progress_hook)
            
            self.log_signal.emit(f"[*] {tr('poc.sync.download_done_extracting')}")
            
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
                raise Exception(tr("poc.sync.template_dir_not_found"))
            
            self.log_signal.emit(f"[*] {tr('poc.sync.copying_files')}")
            
            # 统计复制的文件数
            copied_count = 0
            yaml_files = []
            
            # 收集所有 YAML 文件
            for root, dirs, files in os.walk(extracted_dir):
                for file in files:
                    if file.endswith(('.yaml', '.yml')):
                        yaml_files.append(os.path.join(root, file))
            
            total_files = len(yaml_files)
            self.log_signal.emit(f"[*] {tr('poc.sync.found_files', count=total_files)}")
            
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
                    self.log_signal.emit(f"[*] {tr('poc.sync.copied_progress', current=i + 1, total=total_files)}")
                    self.progress_signal.emit(i + 1, total_files)
            
            # 清理临时文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            self.log_signal.emit(f"\n[✓] {tr('poc.sync.complete', count=copied_count)}")
            self.finished_signal.emit(True, tr("poc.sync.success", count=copied_count))
            
        except Exception as e:
            self.log_signal.emit(f"\n[!] {tr('poc.sync.failed', error=str(e))}")
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
        self.setWindowTitle(tr("poc.sync.title"))
        self.resize(scaled(650), scaled(500))
        self.setMinimumSize(scaled(500), scaled(350))
        
        # 应用 FORTRESS 样式
        # 应用 FORTRESS 样式
        from core.fortress_style import get_dialog_stylesheet, get_button_style, get_secondary_button_style
        self.setStyleSheet(get_dialog_stylesheet(self.colors))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(scaled(15))
        layout.setContentsMargins(scaled(20), scaled(20), scaled(20), scaled(20))
        
        # 说明
        info_group = QGroupBox(tr("poc.sync.info_group"))
        info_layout = QVBoxLayout()
        info_layout.setSpacing(scaled(10))
        
        info_label = QLabel(tr("poc.sync.description"))
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        # 镜像地址（可选）
        mirror_layout = QHBoxLayout()
        mirror_layout.addWidget(QLabel(tr("poc.sync.custom_url")))
        self.mirror_input = QLineEdit()
        self.mirror_input.setPlaceholderText(tr("poc.sync.custom_url_placeholder"))
        mirror_layout.addWidget(self.mirror_input)
        info_layout.addLayout(mirror_layout)
        
        # 目标目录
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel(tr("poc.sync.save_dir")))
        self.dir_label = QLabel(self.target_dir)
        self.dir_label = QLabel(self.target_dir)
        btn_primary = self.colors.get('btn_primary', '#2563eb')
        self.dir_label.setStyleSheet(scaled_style(f"color: {btn_primary};"))
        dir_layout.addWidget(self.dir_label)
        dir_layout.addStretch()
        info_layout.addLayout(dir_layout)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 进度
        progress_group = QGroupBox(tr("poc.sync.progress_group"))
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", scaled(9)))
        self.log_text.setMaximumHeight(scaled(180))
        bg_color = self.colors.get('input_bg', '#1e1e1e')
        text_color = self.colors.get('text_secondary', '#dcdcdc')
        border_color = self.colors.get('nav_border', '#3e4451')
        
        self.log_text.setStyleSheet(scaled_style(f"""
            QTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 10px;
            }}
        """))
        progress_layout.addWidget(self.log_text)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        
        self.btn_sync = QPushButton(tr("poc.sync.start"))
        self.btn_sync = QPushButton(tr("poc.sync.start"))
        self.btn_sync.setStyleSheet(get_button_style('primary', self.colors))
        self.btn_sync.clicked.connect(self.start_sync)
        btn_layout.addWidget(self.btn_sync)
        
        btn_layout.addStretch()
        
        btn_close = QPushButton(tr("common.close"))
        btn_close.setStyleSheet(get_secondary_button_style(self.colors))
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def start_sync(self):
        """开始同步"""
        reply = QMessageBox.question(
            self, tr("poc.sync.confirm_title"),
            tr("poc.sync.confirm_body", target_dir=self.target_dir),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText(tr("poc.sync.syncing"))
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
        self.btn_sync.setText(tr("poc.sync.start"))

        if success:
            QMessageBox.information(self, tr("msg.success"), message)
        else:
            QMessageBox.warning(self, tr("msg.failed"), tr("poc.sync.failed", error=message))
