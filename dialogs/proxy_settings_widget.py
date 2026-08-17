"""Reusable proxy settings panel for application network features."""

from PyQt5.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from core.network_proxy import (
    PROXY_MODE_CUSTOM,
    PROXY_MODE_DIRECT,
    PROXY_MODE_SYSTEM,
    PROXY_SCOPE_AI,
    PROXY_SCOPE_ASSET_SEARCH,
    PROXY_SCOPE_FOFA,
    PROXY_SCOPE_ONLINE_RESOURCES,
    PROXY_SCOPE_SCAN,
    PROXY_SCOPE_UPDATE,
)
from i18n import tr


class ProxySettingsWidget(QWidget):
    """Edit the proxy mode and optional custom URL for each network scope."""

    SCOPE_ROWS = (
        (PROXY_SCOPE_AI, "settings.proxy.scope_ai"),
        (PROXY_SCOPE_FOFA, "settings.proxy.scope_fofa"),
        (PROXY_SCOPE_ASSET_SEARCH, "settings.proxy.scope_asset_search"),
        (PROXY_SCOPE_SCAN, "settings.proxy.scope_scan"),
        (PROXY_SCOPE_ONLINE_RESOURCES, "settings.proxy.scope_online_resources"),
        (PROXY_SCOPE_UPDATE, "settings.proxy.scope_update"),
    )

    MODE_ITEMS = (
        ("settings.proxy.mode_direct", PROXY_MODE_DIRECT),
        ("settings.proxy.mode_system", PROXY_MODE_SYSTEM),
        ("settings.proxy.mode_custom", PROXY_MODE_CUSTOM),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode_inputs = {}
        self._url_inputs = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(2, 1)

        grid.addWidget(QLabel(tr("settings.proxy.scope_header")), 0, 0)
        grid.addWidget(QLabel(tr("settings.proxy.mode_header")), 0, 1)
        grid.addWidget(QLabel(tr("settings.proxy.address_header")), 0, 2)

        for row, (scope, label_key) in enumerate(self.SCOPE_ROWS, start=1):
            grid.addWidget(QLabel(tr(label_key)), row, 0)

            mode_input = QComboBox()
            for text_key, mode in self.MODE_ITEMS:
                mode_input.addItem(tr(text_key), mode)
            mode_input.setMinimumWidth(120)
            grid.addWidget(mode_input, row, 1)

            url_input = QLineEdit()
            url_input.setPlaceholderText(tr("settings.proxy.address_placeholder"))
            url_input.setEchoMode(QLineEdit.PasswordEchoOnEdit)
            url_input.setClearButtonEnabled(True)
            grid.addWidget(url_input, row, 2)

            mode_input.currentIndexChanged.connect(
                lambda _index, current_scope=scope: self._update_url_input(current_scope)
            )
            self._mode_inputs[scope] = mode_input
            self._url_inputs[scope] = url_input

        layout.addLayout(grid)
        layout.addStretch()

    def _update_url_input(self, scope):
        is_custom = self._mode_inputs[scope].currentData() == PROXY_MODE_CUSTOM
        self._url_inputs[scope].setEnabled(is_custom)

    def load_configurations(self, configurations):
        for scope, _label_key in self.SCOPE_ROWS:
            config = configurations.get(scope, {})
            mode_input = self._mode_inputs[scope]
            mode_index = mode_input.findData(config.get("mode", PROXY_MODE_DIRECT))
            mode_input.setCurrentIndex(mode_index if mode_index >= 0 else 0)
            self._url_inputs[scope].setText(config.get("url", ""))
            self._update_url_input(scope)

    def configurations(self):
        return {
            scope: {
                "mode": self._mode_inputs[scope].currentData(),
                "url": self._url_inputs[scope].text().strip(),
            }
            for scope, _label_key in self.SCOPE_ROWS
        }
