"""
AI 漏洞报告生成对话框
根据扫描结果生成专业的漏洞报告
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QProgressBar, QMessageBox, QApplication,
    QComboBox, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.settings_manager import get_settings
from core.ai_client import AIWorkerThreadV2, AIClient


class AIVulnReportDialog(QDialog):
    """AI 漏洞报告生成对话框"""

    def __init__(self, parent=None, vuln_info="", raw_result=None, colors=None):
        super().__init__(parent)
        self.settings = get_settings()
        self.vuln_info = vuln_info
        self.raw_result = raw_result or {}
        self.ai_worker = None
        # 获取主题颜色
        if colors:
            self.colors = colors
        else:
            from core.fortress_style import FORTRESS_COLORS
            self.colors = FORTRESS_COLORS
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("AI 漏洞报告生成")
        self.resize(700, 600)
        self.setMinimumSize(500, 400)

        # 应用主题样式
        from core.fortress_style import get_dialog_stylesheet, get_button_style, get_secondary_button_style
        self.setStyleSheet(get_dialog_stylesheet(self.colors))

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 漏洞信息显示
        info_group = QGroupBox("漏洞信息")
        info_layout = QVBoxLayout(info_group)
        self.info_display = QTextEdit()
        self.info_display.setPlainText(self.vuln_info)
        self.info_display.setMaximumHeight(120)
        self.info_display.setReadOnly(True)
        info_layout.addWidget(self.info_display)
        layout.addWidget(info_group)

        # 报告类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("报告类型:"))
        self.report_type_combo = QComboBox()
        self.report_type_combo.setMinimumWidth(200)
        self.report_type_combo.addItems([
            "补天/SRC 提交报告",
            "详细技术分析报告",
            "简要漏洞说明",
            "修复建议报告"
        ])
        type_layout.addWidget(self.report_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # 生成按钮
        btn_generate = QPushButton("生成报告")
        btn_generate.setStyleSheet(get_button_style('primary', self.colors))
        btn_generate.setMinimumHeight(36)
        btn_generate.clicked.connect(self.generate_report)
        layout.addWidget(btn_generate)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        # 报告输出
        report_group = QGroupBox("生成的报告")
        report_layout = QVBoxLayout(report_group)
        self.report_output = QTextEdit()
        self.report_output.setReadOnly(True)
        self.report_output.setFont(QFont("Microsoft YaHei", 10))
        self.report_output.setPlaceholderText("点击上方按钮生成报告...")
        report_layout.addWidget(self.report_output)
        layout.addWidget(report_group)

        # 底部按钮
        btn_layout = QHBoxLayout()

        btn_copy = QPushButton("复制报告")
        btn_copy.setStyleSheet(get_button_style('info', self.colors))
        btn_copy.setMinimumWidth(100)
        btn_copy.clicked.connect(self.copy_report)
        btn_layout.addWidget(btn_copy)

        btn_save = QPushButton("保存为文件")
        btn_save.setStyleSheet(get_button_style('success', self.colors))
        btn_save.setMinimumWidth(100)
        btn_save.clicked.connect(self.save_report)
        btn_layout.addWidget(btn_save)

        btn_layout.addStretch()

        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet(get_secondary_button_style(self.colors))
        btn_close.setMinimumWidth(80)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def get_current_ai_config(self):
        """获取当前 AI 配置"""
        presets = self.settings.get_ai_presets()
        if not presets:
            return None, None, None
        current_index = self.settings.get_current_ai_preset_index()
        if current_index < 0 or current_index >= len(presets):
            current_index = 0
        config = presets[current_index]
        return config.get("api_url", ""), config.get("api_key", ""), config.get("model", "")

    def generate_report(self):
        """生成漏洞报告"""
        api_url, api_key, model = self.get_current_ai_config()
        if not api_key:
            QMessageBox.warning(self, "错误", "请先在设置中配置 AI 模型")
            return

        report_type = self.report_type_combo.currentText()
        prompt = self.build_prompt(report_type)

        self.progress.show()
        self.report_output.setPlainText("⏳ 正在生成报告，请稍候...")

        # 使用自定义的报告生成任务
        self.ai_worker = VulnReportWorker(api_url, api_key, model, prompt)
        self.ai_worker.result_signal.connect(self.on_result)
        self.ai_worker.error_signal.connect(self.on_error)
        self.ai_worker.start()

    def build_prompt(self, report_type):
        """构建不同类型的报告提示词"""
        # 提取更多信息
        template_id = self.raw_result.get("template-id", self.raw_result.get("templateID", ""))
        matched_at = self.raw_result.get("matched-at", self.raw_result.get("matched", ""))
        severity = self.raw_result.get("info", {}).get("severity", "unknown")
        name = self.raw_result.get("info", {}).get("name", "")
        description = self.raw_result.get("info", {}).get("description", "")
        tags = self.raw_result.get("info", {}).get("tags", [])
        reference = self.raw_result.get("info", {}).get("reference", [])

        # 提取请求包信息
        request_data = self.raw_result.get("request", "")
        curl_command = self.raw_result.get("curl-command", "")

        # 提取基础 URL (不含路径)
        import re
        base_url_match = re.match(r'(https?://[^/]+)', matched_at)
        base_url = base_url_match.group(1) if base_url_match else matched_at

        # 危害等级映射
        severity_map = {
            "critical": "严重",
            "high": "高危",
            "medium": "中危",
            "low": "低危",
            "info": "信息"
        }
        severity_cn = severity_map.get(severity.lower(), severity)

        # 漏洞分类映射
        vuln_type = "Web漏洞"
        if any(t in str(tags).lower() for t in ["rce", "command", "exec"]):
            vuln_category = "远程命令执行"
        elif any(t in str(tags).lower() for t in ["sqli", "sql"]):
            vuln_category = "SQL注入"
        elif any(t in str(tags).lower() for t in ["xss"]):
            vuln_category = "跨站脚本攻击"
        elif any(t in str(tags).lower() for t in ["lfi", "rfi", "file", "read"]):
            vuln_category = "任意文件读取"
        elif any(t in str(tags).lower() for t in ["upload"]):
            vuln_category = "任意文件上传"
        elif any(t in str(tags).lower() for t in ["ssrf"]):
            vuln_category = "服务端请求伪造"
        elif any(t in str(tags).lower() for t in ["unauth", "bypass"]):
            vuln_category = "未授权访问"
        elif any(t in str(tags).lower() for t in ["disclosure", "exposure", "leak"]):
            vuln_category = "信息泄露"
        else:
            vuln_category = "其他漏洞"

        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")

        base_info = f"""漏洞名称: {name}
漏洞ID: {template_id}
危害等级: {severity}
目标地址: {matched_at}
基础URL: {base_url}
漏洞描述: {description}
标签: {', '.join(tags) if isinstance(tags, list) else tags}
参考链接: {', '.join(reference) if isinstance(reference, list) else reference}
请求包:
{request_data if request_data else '无'}"""

        if report_type == "补天/SRC 提交报告":
            return f"""你是一个专业的安全研究员，请根据以下漏洞信息生成一份适合提交到补天、漏洞盒子等 SRC 平台的漏洞报告。

{base_info}

请严格按照以下 Markdown 表格格式生成报告：

# 漏洞报告

## 一、 漏洞概述

| **描述** | **内容** |
| :--- | :--- |
| **标题** | {base_url}存在{name} |
| **漏洞报送时间** | {today} |
| **漏洞单位** | （从URL提取IP或域名） |
| **漏洞分类** | {vuln_category} |
| **漏洞类型** | {vuln_type} |
| **漏洞等级** | {severity_cn} |
| **URL地址** | {base_url} |

## 二、 漏洞说明

### 描述漏洞过程
（根据漏洞类型详细描述攻击者可利用此漏洞实施的攻击，列出5-7条危害，每条用【】标注关键词）

### 复现步骤

（如果漏洞复现需要多个步骤，请按以下格式详细说明每个步骤：）

**步骤1：xxx（说明这一步的目的）**
```http
（第一个请求包）
```
说明：解释这个请求的作用，为什么需要这一步，返回什么结果

**步骤2：xxx（说明这一步的目的）**
```http
（第二个请求包）
```
说明：解释这个请求的作用，如何利用上一步的结果

（如果只有单个请求，则直接展示：）

### Payload
```http
（完整的 HTTP 请求包）
```

## 三、 修复建议

```text
（列出5-8条具体的修复建议，每条用数字编号，用【】标注关键词）
```

重要要求：
1. URL地址只填写基础URL（如 https://123.166.159.14），不要拼接接口路径
2. 如果是多步骤漏洞（如先获取token再利用），必须分步骤说明每一步的作用和原因
3. 每个步骤要解释：这一步做什么、为什么需要这一步、预期返回什么
4. 漏洞说明要详细描述危害，每条危害用【】标注关键词
5. 修复建议要具体可操作"""

        elif report_type == "详细技术分析报告":
            return f"""你是一个资深安全分析师，请根据以下漏洞信息生成一份详细的技术分析报告。

{base_info}

请包含以下内容：

## 一、漏洞概述
- 漏洞类型和危害等级
- 影响范围

## 二、技术分析
- 漏洞原理深入分析
- 漏洞触发条件
- 攻击向量分析

## 三、利用方式
- 漏洞利用的前置条件
- 利用步骤说明
- 可能的利用场景

## 四、影响评估
- 机密性影响
- 完整性影响
- 可用性影响
- 业务风险评估

## 五、检测方法
- 如何检测该漏洞
- 日志特征
- 流量特征

## 六、修复方案
- 临时缓解措施
- 永久修复方案
- 安全加固建议

## 七、参考资料
- 相关 CVE
- 官方公告
- 技术文档"""

        elif report_type == "简要漏洞说明":
            return f"""请根据以下漏洞信息生成一份简要的漏洞说明，适合快速了解漏洞情况。

{base_info}

请简洁地说明：
1. 这是什么漏洞
2. 危害程度如何
3. 如何修复

控制在 200 字以内。"""

        else:  # 修复建议报告
            return f"""你是一个安全顾问，请根据以下漏洞信息生成一份专业的修复建议报告。

{base_info}

请提供：

## 一、漏洞简述
（简要说明漏洞情况）

## 二、风险评估
（评估该漏洞的风险等级和影响）

## 三、紧急处置措施
（立即可以采取的临时措施）

## 四、根本修复方案
（彻底解决问题的方案）

## 五、安全加固建议
（防止类似问题再次发生的建议）

## 六、验证方法
（如何验证漏洞已被修复）

请确保建议具体、可操作。"""

    def on_result(self, result):
        """处理生成结果"""
        self.progress.hide()
        self.report_output.setPlainText(result)

    def on_error(self, error):
        """处理错误"""
        self.progress.hide()
        self.report_output.setPlainText(f"❌ 生成失败: {error}")

    def copy_report(self):
        """复制报告"""
        text = self.report_output.toPlainText()
        if text and not text.startswith("⏳") and not text.startswith("❌"):
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "成功", "报告已复制到剪贴板")
        else:
            QMessageBox.warning(self, "提示", "请先生成报告")

    def save_report(self):
        """保存报告为文件"""
        text = self.report_output.toPlainText()
        if not text or text.startswith("⏳") or text.startswith("❌"):
            QMessageBox.warning(self, "提示", "请先生成报告")
            return

        from PyQt5.QtWidgets import QFileDialog
        from datetime import datetime

        # 生成默认文件名
        template_id = self.raw_result.get("template-id", self.raw_result.get("templateID", "vuln"))
        default_name = f"漏洞报告_{template_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存报告", default_name,
            "Markdown 文件 (*.md);;文本文件 (*.txt);;所有文件 (*)"
        )

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(text)
                QMessageBox.information(self, "成功", f"报告已保存到:\n{filepath}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")


class VulnReportWorker(AIWorkerThreadV2):
    """漏洞报告生成工作线程"""

    def __init__(self, api_url, api_key, model, prompt):
        # 不调用父类 __init__，直接初始化
        from PyQt5.QtCore import QThread
        QThread.__init__(self)
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.prompt = prompt

    def run(self):
        try:
            client = AIClient(self.api_url, self.api_key, self.model)
            result = client._call_api(self.prompt)
            self.result_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(f"发生错误: {str(e)}")
