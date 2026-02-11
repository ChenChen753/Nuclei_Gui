"""
AI 助手弹窗 V2 - 多功能 Tab 界面
支持 FOFA 语法生成、漏洞分析、智能推荐、历史记录
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QComboBox, QGroupBox, QMessageBox,
    QProgressBar, QTabWidget, QWidget, QApplication, QListWidget,
    QListWidgetItem, QSplitter, QMenu
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.settings_manager import get_settings
from core.ai_client import AIWorkerThreadV2
from core.history_manager import get_history_manager


class AIAssistantDialog(QDialog):
    """
    AI 助手弹窗 V2
    支持多功能切换
    """
    
    def __init__(self, parent=None, initial_poc_name=""):
        super().__init__(parent)
        self.settings = get_settings()
        self.history_manager = get_history_manager()
        self.ai_worker = None
        self.initial_poc_name = initial_poc_name
        self.generated_fofa_query = ""
        self.current_input_text = ""  # 保存当前输入，用于历史记录
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("🤖 AI 助手")
        self.resize(750, 600)
        self.setMinimumSize(600, 450)
        
        layout = QVBoxLayout(self)

        # 功能 Tab
        self.tabs = QTabWidget()
        
        # Tab 1: FOFA 语法生成
        self.tabs.addTab(self.create_fofa_tab(), "🔍 FOFA 语法")

        # Tab 2: POC 生成
        self.tabs.addTab(self.create_poc_tab(), "🛠️ POC 生成")

        # Tab 3: 漏洞分析
        self.tabs.addTab(self.create_analyze_tab(), "📊 漏洞分析")

        # Tab 4: 智能推荐
        self.tabs.addTab(self.create_recommend_tab(), "💡 智能推荐")

        # Tab 5: 历史记录
        self.tabs.addTab(self.create_history_tab(), "📜 历史记录")
        
        layout.addWidget(self.tabs)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
    
    def create_fofa_tab(self):
        """FOFA 语法生成 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 输入
        layout.addWidget(QLabel("输入 POC 名称或漏洞描述:"))
        self.fofa_input = QLineEdit()
        self.fofa_input.setPlaceholderText("例如: ThinkPHP 5.0.23 远程代码执行")
        self.fofa_input.setText(self.initial_poc_name)
        layout.addWidget(self.fofa_input)
        
        btn = QPushButton("✨ 生成 FOFA 语法")
        btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 8px;")
        btn.clicked.connect(lambda: self.do_ai_task(AIWorkerThreadV2.TASK_FOFA, self.fofa_input, self.fofa_output))
        layout.addWidget(btn)
        
        self.fofa_progress = QProgressBar()
        self.fofa_progress.setRange(0, 0)
        self.fofa_progress.hide()
        layout.addWidget(self.fofa_progress)
        
        # 输出
        self.fofa_output = QTextEdit()
        self.fofa_output.setReadOnly(True)
        self.fofa_output.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(self.fofa_output)
        
        # 复制按钮
        copy_layout = QHBoxLayout()
        btn_copy_fofa = QPushButton("📋 复制并跳转 FOFA")
        btn_copy_fofa.setStyleSheet("background-color: #e67e22; color: white; padding: 5px 10px;")
        btn_copy_fofa.clicked.connect(self.copy_fofa_and_open)
        copy_layout.addWidget(btn_copy_fofa)
        btn_copy_all = QPushButton("📄 复制全部")
        btn_copy_all.clicked.connect(lambda: self.copy_text(self.fofa_output))
        copy_layout.addWidget(btn_copy_all)
        copy_layout.addStretch()
        layout.addLayout(copy_layout)

        return widget

    def create_poc_tab(self):
        """POC 生成 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("输入漏洞描述，AI 将生成 Nuclei YAML POC:"))
        self.poc_input = QTextEdit()
        self.poc_input.setPlaceholderText(
            "请详细描述漏洞信息，例如:\n"
            "- 漏洞名称: ThinkPHP 5.0.23 远程代码执行\n"
            "- 漏洞路径: /index.php?s=captcha\n"
            "- 请求方法: POST\n"
            "- 漏洞参数: _method=__construct&filter[]=system&method=get&server[REQUEST_METHOD]=id\n"
            "- 匹配特征: uid= 或 gid=\n"
            "- 影响版本: ThinkPHP 5.0.x < 5.0.24"
        )
        self.poc_input.setMaximumHeight(120)
        layout.addWidget(self.poc_input)

        btn = QPushButton("🛠️ 生成 POC")
        btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        btn.clicked.connect(self.do_poc_generate)
        layout.addWidget(btn)

        self.poc_progress = QProgressBar()
        self.poc_progress.setRange(0, 0)
        self.poc_progress.hide()
        layout.addWidget(self.poc_progress)

        self.poc_output = QTextEdit()
        self.poc_output.setReadOnly(True)
        self.poc_output.setFont(QFont("Consolas", 10))
        self.poc_output.setPlaceholderText("生成的 POC 将显示在这里...")
        layout.addWidget(self.poc_output)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("📋 复制 POC")
        btn_copy.clicked.connect(lambda: self.copy_text(self.poc_output))
        btn_layout.addWidget(btn_copy)

        btn_save = QPushButton("💾 保存到 POC 库")
        btn_save.setStyleSheet("background-color: #3498db; color: white;")
        btn_save.clicked.connect(self.save_generated_poc)
        btn_layout.addWidget(btn_save)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def do_poc_generate(self):
        """执行 POC 生成"""
        content = self.poc_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请输入漏洞描述")
            return

        api_url, api_key, model = self.get_current_ai_config()
        if not api_key:
            QMessageBox.warning(self, "错误", "请先配置 AI 模型")
            return

        self.current_input_text = content
        self.current_model_name = model

        self.poc_progress.show()
        self.poc_output.setPlainText("⏳ 正在生成 POC，请稍候...")

        self.ai_worker = AIWorkerThreadV2(api_url, api_key, model, AIWorkerThreadV2.TASK_POC, content)
        self.ai_worker.result_signal.connect(self.on_poc_result)
        self.ai_worker.error_signal.connect(lambda e: self.on_ai_error(e, self.poc_output, self.poc_progress))
        self.ai_worker.start()

    def on_poc_result(self, result):
        """POC 生成结果"""
        self.poc_progress.hide()
        self.poc_output.setPlainText(result)

        # 保存到历史记录
        try:
            self.history_manager.add_ai_history(
                task_type="poc",
                input_text=self.current_input_text,
                output_text=result,
                model_name=getattr(self, 'current_model_name', '')
            )
        except:
            pass

    def save_generated_poc(self):
        """保存生成的 POC 到 POC 库"""
        content = self.poc_output.toPlainText().strip()
        if not content or content.startswith("⏳") or content.startswith("❌"):
            QMessageBox.warning(self, "提示", "请先生成有效的 POC")
            return

        # 提取 YAML 代码块
        import re
        yaml_match = re.search(r'```ya?ml?\s*([\s\S]*?)```', content)
        if yaml_match:
            yaml_content = yaml_match.group(1).strip()
        else:
            yaml_content = content

        # 尝试提取 POC ID 作为文件名
        id_match = re.search(r'^id:\s*(.+)$', yaml_content, re.MULTILINE)
        if id_match:
            poc_id = id_match.group(1).strip()
            filename = f"{poc_id}.yaml"
        else:
            from datetime import datetime
            filename = f"ai-generated-{datetime.now().strftime('%Y%m%d%H%M%S')}.yaml"

        # 保存到 user_generated 目录
        import os
        poc_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "poc_library", "user_generated")
        os.makedirs(poc_dir, exist_ok=True)

        filepath = os.path.join(poc_dir, filename)

        # 检查文件是否存在
        if os.path.exists(filepath):
            reply = QMessageBox.question(
                self, "文件已存在",
                f"POC 文件 {filename} 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            QMessageBox.information(self, "成功", f"POC 已保存到:\n{filepath}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")

    def create_analyze_tab(self):
        """漏洞分析 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("输入漏洞信息，获取深入分析和修复建议:"))
        self.analyze_input = QLineEdit()
        self.analyze_input.setPlaceholderText("例如: CVE-2024-1234 SQL Injection in User Login")
        layout.addWidget(self.analyze_input)
        
        btn = QPushButton("📊 分析漏洞")
        btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 8px;")
        btn.clicked.connect(lambda: self.do_ai_task(AIWorkerThreadV2.TASK_ANALYZE, self.analyze_input, self.analyze_output))
        layout.addWidget(btn)
        
        self.analyze_progress = QProgressBar()
        self.analyze_progress.setRange(0, 0)
        self.analyze_progress.hide()
        layout.addWidget(self.analyze_progress)
        
        self.analyze_output = QTextEdit()
        self.analyze_output.setReadOnly(True)
        self.analyze_output.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(self.analyze_output)
        
        copy_layout = QHBoxLayout()
        btn_copy = QPushButton("📋 复制分析报告")
        btn_copy.clicked.connect(lambda: self.copy_text(self.analyze_output))
        copy_layout.addWidget(btn_copy)
        copy_layout.addStretch()
        layout.addLayout(copy_layout)
        
        return widget
    
    def create_recommend_tab(self):
        """智能推荐 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("输入目标信息，获取 POC 推荐:"))
        self.recommend_input = QLineEdit()
        self.recommend_input.setPlaceholderText("例如: Apache/2.4.49, PHP/7.4, WordPress 5.8")
        layout.addWidget(self.recommend_input)
        
        btn = QPushButton("💡 获取推荐")
        btn.setStyleSheet("background-color: #9b59b6; color: white; font-weight: bold; padding: 8px;")
        btn.clicked.connect(lambda: self.do_ai_task(AIWorkerThreadV2.TASK_RECOMMEND, self.recommend_input, self.recommend_output))
        layout.addWidget(btn)
        
        self.recommend_progress = QProgressBar()
        self.recommend_progress.setRange(0, 0)
        self.recommend_progress.hide()
        layout.addWidget(self.recommend_progress)
        
        self.recommend_output = QTextEdit()
        self.recommend_output.setReadOnly(True)
        self.recommend_output.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(self.recommend_output)
        
        copy_layout = QHBoxLayout()
        btn_copy = QPushButton("📋 复制推荐")
        btn_copy.clicked.connect(lambda: self.copy_text(self.recommend_output))
        copy_layout.addWidget(btn_copy)
        copy_layout.addStretch()
        layout.addLayout(copy_layout)
        
        return widget
    
    def get_current_ai_config(self):
        """获取当前 AI 配置（从设置管理器）"""
        config = self.settings.get_current_ai_config()
        if not config:
            return None, None, None
        return config.get("api_url", ""), config.get("api_key", ""), config.get("model", "")
    
    def do_ai_task(self, task_type, input_widget, output_widget):
        """执行 AI 任务"""
        content = input_widget.text().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请输入内容")
            return
        
        api_url, api_key, model = self.get_current_ai_config()
        if not api_key:
            QMessageBox.warning(self, "错误", "请先配置 AI 模型")
            return
        
        # 保存当前输入（用于历史记录）
        self.current_input_text = content
        self.current_model_name = model

        # 根据 tab 获取对应的进度条
        progress_map = {
            AIWorkerThreadV2.TASK_FOFA: self.fofa_progress,
            AIWorkerThreadV2.TASK_ANALYZE: self.analyze_progress,
            AIWorkerThreadV2.TASK_RECOMMEND: self.recommend_progress,
        }
        progress = progress_map.get(task_type)
        if progress:
            progress.show()
        
        output_widget.setPlainText("⏳ 正在请求 AI 生成中，请稍候...")
        
        self.ai_worker = AIWorkerThreadV2(api_url, api_key, model, task_type, content)
        self.ai_worker.result_signal.connect(lambda r: self.on_ai_result(r, output_widget, progress, task_type))
        self.ai_worker.error_signal.connect(lambda e: self.on_ai_error(e, output_widget, progress))
        self.ai_worker.start()
    
    def on_ai_result(self, result, output_widget, progress, task_type):
        """AI 返回结果"""
        if progress:
            progress.hide()
        output_widget.setPlainText(result)
        
        # 保存到历史记录
        task_type_map = {
            AIWorkerThreadV2.TASK_FOFA: "fofa",
            AIWorkerThreadV2.TASK_ANALYZE: "analyze",
            AIWorkerThreadV2.TASK_RECOMMEND: "recommend",
        }
        try:
            self.history_manager.add_ai_history(
                task_type=task_type_map.get(task_type, "unknown"),
                input_text=self.current_input_text,
                output_text=result,
                model_name=getattr(self, 'current_model_name', '')
            )
        except Exception as e:
            pass  # 忽略保存错误
        
        if task_type == AIWorkerThreadV2.TASK_FOFA:
            self.extract_fofa_query(result)
    
    def on_ai_error(self, error, output_widget, progress):
        """AI 返回错误"""
        if progress:
            progress.hide()
        output_widget.setPlainText(f"❌ 错误: {error}")
    
    def extract_fofa_query(self, text):
        """提取 FOFA 语法"""
        import re
        patterns = [
            r'`([^`]*(?:app=|title=|body=|header=|server=|icon_hash=)[^`]*)`',
            r'FOFA[^:：]*[:：]\s*`?([^`\n]+(?:app=|title=|body=|header=|server=|icon_hash=)[^`\n]*)`?',
            r'((?:app|title|body|header|server|icon_hash)\s*=\s*"[^"]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.generated_fofa_query = match.group(1).strip()
                return
        self.generated_fofa_query = ""
    
    def copy_fofa_query(self):
        """复制 FOFA 语法"""
        if self.generated_fofa_query:
            QApplication.clipboard().setText(self.generated_fofa_query)
            QMessageBox.information(self, "成功", f"已复制:\n{self.generated_fofa_query}")
        else:
            QMessageBox.warning(self, "提示", "未能提取 FOFA 语法，请手动复制")
    
    def copy_fofa_and_open(self):
        """复制 FOFA 语法并跳转到内置 FOFA 搜索页面"""
        if self.generated_fofa_query:
            # 复制到剪贴板
            QApplication.clipboard().setText(self.generated_fofa_query)
            
            # 关闭当前窗口
            self.close()
            
            # 调用主窗口的打开 FOFA 弹窗方法，并传递查询语句
            # 假设 parent 是 MainWindow 实例
            if self.parent() and hasattr(self.parent(), 'open_fofa_dialog'):
                self.parent().open_fofa_dialog(query=self.generated_fofa_query)
        else:
            QMessageBox.warning(self, "提示", "未能提取 FOFA 语法，请先生成")
    
    def copy_text(self, widget):
        """复制文本"""
        text = widget.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "成功", "已复制到剪贴板")
    
    
    def create_history_tab(self):
        """历史记录 Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 提示
        layout.addWidget(QLabel("💡 双击历史记录查看详情，右键删除"))
        
        # 任务类型筛选
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("类型筛选:"))
        self.history_type_combo = QComboBox()
        self.history_type_combo.addItems(["全部", "FOFA语法", "POC生成", "漏洞分析", "智能推荐"])
        self.history_type_combo.currentTextChanged.connect(self.refresh_ai_history)
        filter_row.addWidget(self.history_type_combo)
        filter_row.addStretch()
        
        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.clicked.connect(self.refresh_ai_history)
        filter_row.addWidget(btn_refresh)
        
        btn_clear = QPushButton("🗑️ 清空")
        btn_clear.clicked.connect(self.clear_ai_history)
        filter_row.addWidget(btn_clear)
        
        layout.addLayout(filter_row)
        
        # 历史列表
        self.ai_history_list = QListWidget()
        self.ai_history_list.itemDoubleClicked.connect(self.show_ai_history_detail)
        self.ai_history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ai_history_list.customContextMenuRequested.connect(self.show_ai_history_menu)
        layout.addWidget(self.ai_history_list)
        
        # 详情显示
        self.history_detail = QTextEdit()
        self.history_detail.setReadOnly(True)
        self.history_detail.setMaximumHeight(150)
        self.history_detail.setFont(QFont("Microsoft YaHei", 9))
        layout.addWidget(self.history_detail)
        
        # 初始加载
        self.refresh_ai_history()
        
        return widget
    
    def refresh_ai_history(self):
        """刷新 AI 历史记录"""
        self.ai_history_list.clear()

        # 任务类型映射
        type_map = {
            "全部": None,
            "FOFA语法": "fofa",
            "POC生成": "poc",
            "漏洞分析": "analyze",
            "智能推荐": "recommend"
        }

        filter_type = self.history_type_combo.currentText()
        task_type = type_map.get(filter_type)

        histories = self.history_manager.get_ai_history(task_type=task_type, limit=50)

        type_labels = {
            "fofa": "🔍 FOFA",
            "poc": "🛠️ POC",
            "analyze": "📊 分析",
            "recommend": "💡 推荐"
        }

        for h in histories:
            t_type = h.get('task_type', '')
            input_text = h.get('input_text', '')[:50]
            time_str = h.get('create_time', '')[:16]
            label = type_labels.get(t_type, t_type)

            item = QListWidgetItem(f"[{label}] {input_text}...")
            item.setToolTip(f"时间: {time_str}\n输入: {h.get('input_text', '')}")
            item.setData(Qt.UserRole, h)
            self.ai_history_list.addItem(item)
    
    def show_ai_history_detail(self, item):
        """显示历史记录详情"""
        history = item.data(Qt.UserRole)
        if history:
            detail = f"【输入】\n{history.get('input_text', '')}\n\n【输出】\n{history.get('output_text', '')}"
            self.history_detail.setPlainText(detail)
    
    def show_ai_history_menu(self, pos):
        """AI 历史记录右键菜单"""
        item = self.ai_history_list.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        view_action = menu.addAction("👁️ 查看详情")
        view_action.triggered.connect(lambda: self.show_ai_history_detail(item))
        
        copy_action = menu.addAction("📋 复制输出")
        copy_action.triggered.connect(lambda: self.copy_ai_history_output(item))
        
        delete_action = menu.addAction("🗑️ 删除")
        delete_action.triggered.connect(lambda: self.delete_ai_history_item(item))
        
        menu.exec_(self.ai_history_list.mapToGlobal(pos))
    
    def copy_ai_history_output(self, item):
        """复制历史记录输出"""
        history = item.data(Qt.UserRole)
        if history:
            QApplication.clipboard().setText(history.get('output_text', ''))
            QMessageBox.information(self, "成功", "已复制到剪贴板")
    
    def delete_ai_history_item(self, item):
        """删除 AI 历史记录"""
        history = item.data(Qt.UserRole)
        if history:
            self.history_manager.delete_ai_history(history.get('id'))
            self.refresh_ai_history()
    
    def clear_ai_history(self):
        """清空 AI 历史记录"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有 AI 生成历史吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.history_manager.clear_ai_history()
            self.refresh_ai_history()
            self.history_detail.clear()
