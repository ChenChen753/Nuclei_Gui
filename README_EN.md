# Nuclei GUI Scanner

A PyQt5-based graphical interface for Nuclei. It provides POC management, asset import/search, task queue scanning, scan history, report export, AI-assisted analysis, and DNSLog/OAST verification.

[简体中文](README.md)

## Project Info

- **Version**: 2.5.5
- **Author**: 辰辰
- **Tech Stack**: Python 3.x + PyQt5 + Nuclei
- **Platforms**: Windows / macOS / Linux

## Quick Start

### Requirements

- Python 3.8+
- Windows 10/11, macOS 10.14+, or Linux
- Nuclei scanner binary

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Install Nuclei

You can install Nuclei from inside the GUI. If the download fails, try using a proxy and retry.

Manual installation is also supported:

1. Download Nuclei from the official ProjectDiscovery release page.
2. Put the binary in the `bin/` directory.
3. Rename it to the expected platform filename, such as `nuclei.exe` on Windows.

The repository does not include `bin/nuclei.exe`. Large Nuclei binaries should not be committed to GitHub.

### Run

```bash
python main.py
```

### Windows Binary Packaging

The project includes a reusable PyInstaller configuration for portable releases:

```powershell
.\build_package.ps1
# or
.\build_package.bat
```

The build creates:

```text
dist/Nuclei_GUI_portable/
  Nuclei_GUI.exe
  bin/
    nuclei.exe
  poc_library/
    custom/
    cloud/
    user_generated/
```

Python modules, `i18n/`, and `resources/` are bundled into the executable. `bin/` and `poc_library/` stay beside the executable so Nuclei and POCs can be updated independently. Logs and SQLite databases are stored in the user data directory, such as `%APPDATA%/NucleiGUI/` on Windows.

The executable icon uses `resources/icon.ico` first. If it does not exist, the build automatically converts `resources/icon.png` to a temporary `.ico` file and embeds it into the exe. To change the exe icon, replace `resources/icon.png` and rebuild.

### macOS/Linux Local Packaging

PyInstaller is not a cross-compiler. Build macOS and Linux executables on the corresponding operating system. The project provides one-click local packaging scripts, while official binary release assets are maintained for Windows only.

**macOS**:

```bash
bash build_package_macos.sh
```

Output:

```text
dist/Nuclei_GUI_macos_portable/
  Nuclei_GUI.app
  bin/
    nuclei_darwin
  poc_library/
    custom/
    cloud/
    user_generated/
```

To use a native macOS icon, add `resources/icon.icns` before packaging. For public distribution, macOS signing and notarization are recommended.

**Linux**:

```bash
bash build_package_linux.sh
```

Output:

```text
dist/Nuclei_GUI_linux_portable/
  Nuclei_GUI
  bin/
    nuclei_linux
  poc_library/
    custom/
    cloud/
    user_generated/
```

For better Linux compatibility, build on a stable distribution such as Ubuntu 20.04 or 22.04. Both scripts support `--skip-install`, `--skip-build`, and `--no-archive`.

### Release Asset Policy

- Windows: upload `Nuclei_GUI*.exe`, for example `Nuclei_GUI_v2.5.5.exe` or `Nuclei_GUI_windows_x64_v2.5.5.exe`. Binary update support is currently limited to the Windows exe build.
- Source runs: the updater uses GitHub's generated source zip for source-code updates, so no extra source zip asset is required.
- Windows exe runs: the updater detects the PyInstaller build, downloads the matching `Nuclei_GUI*.exe`, closes the current app, replaces the exe, and restarts automatically.
- macOS/Linux: this repository provides local packaging scripts, but does not publish official binary assets for these systems.
- `bin/nuclei.exe`, `bin/nuclei_darwin`, and `bin/nuclei_linux` are third-party tool binaries and should not be committed.

## Features

- **Dashboard**: scan statistics, vulnerability distribution, history records, quick actions
- **Scanning**: official Nuclei engine integration, task queue, pause/resume, stop, progress, logs
- **POC Management**: search, filter, sync, favorite, edit, test, and select POCs
- **Asset Input**: manual targets, file import, FOFA import, automatic target normalization and deduplication
- **Asset Search**: FOFA, Hunter, Quake, Shodan integrations
- **AI Assistant**: OpenAI-compatible API support for analysis and POC-related assistance
- **Reports**: vulnerability report generation and bilingual report export
- **DNSLog/OAST**: automatic Interactsh detection, dedicated DNSLog settings tab, legacy DNSLog placeholder adaptation
- **Settings**: scan parameters, API credentials, themes, language, Nuclei management, updates
- **Database Cleanup**: clearing scan, AI, and FOFA history also clears the SQLite tables and vacuums the database

## DNSLog/OAST

The GUI uses Nuclei's native Interactsh support for OAST/DNSLog verification.

Supported behavior:

- Auto mode enables Interactsh when selected POCs use `{{interactsh-url}}`, `interactsh_protocol`, `interactsh_request`, or `interactsh_response`.
- Off mode disables Interactsh/OAST for scans that should not make external callbacks.
- Force mode appends Interactsh options even when no OAST marker is detected.
- Self-hosted Interactsh server and token can be configured.
- Legacy placeholders such as `{{dnslog}}`, `{{dnslog_domain}}`, and `{{callback_url}}` can be adapted to `{{interactsh-url}}` through temporary template copies.

Legacy adaptation does not modify the original POC files.

## Data Storage

| File | Description |
|------|-------------|
| `scan_history.db` | Scan records and vulnerability results |
| `history.db` | FOFA history, AI history, and legacy scan history |
| `QSettings` | User configuration and encrypted API keys |

## Disclaimer

This tool is provided only for cybersecurity learning, research, internal security work, and explicitly authorized security testing.

Before using this tool, you must ensure that you have clear authorization from the owner of the target systems, assets, domains, IP addresses, applications, or data. You are responsible for complying with all applicable laws, regulations, service agreements, and authorization boundaries.

You must not use this tool for:

- Unauthorized vulnerability scanning, penetration testing, asset discovery, or bulk detection
- Attacking, intruding into, damaging, disrupting, stealing data from, or bypassing access controls of third-party systems
- Unauthorized scans against public Internet targets or high-frequency requests that may affect third-party services
- Any activity that violates laws, regulations, agreements, or the granted authorization scope

The author and contributors are not responsible for any misuse, abuse, unauthorized use, or direct or indirect damages caused by this tool. By downloading, installing, running, or redistributing this tool, you acknowledge that you understand and accept all risks and legal responsibilities.

## Changelog

### v2.5.5

- Improved Windows exe self-update reliability with a persistent update directory, old-exe backup, SHA256 verification, and `logs/update_apply.log` diagnostics.

### v2.5.4

- Fixed the Windows exe update fallback so exe download URLs are never processed as source zip packages.
- Fixed update prompt rendering so newline escapes and Yes/No buttons are localized correctly.

### v2.5.3

- Fixed Windows exe self-update restarts for PyInstaller onefile builds by resetting inherited bootloader environment variables before launching the new exe.

### v2.5.2

- Added one-click local packaging scripts for macOS and Linux.
- Improved update detection so source runs use the source zip, while Windows exe builds download, replace, and restart with the new exe.
- Fixed first-run binary startup failures caused by scan history database migration order.

### v2.5.1

- Improved portable packaging by generating the Windows exe icon from `resources/icon.png` during builds.
- Fixed the localized report export success prompt and buttons in the Chinese UI.

### v2.5.0

- Improved Chinese/English UI translations, dialogs, statuses, scan records, and report export language handling.
- Improved high-DPI and high-resolution UI layout, button sizing, spacing, and settings page layout.
- Fixed built-in Nuclei download flow while keeping large binaries out of the repository.
- Fixed scan pause/resume behavior in both scan page and task manager.
- Added unified target normalization and deduplication for manual input, file import, FOFA import, task queue, and scan thread.
- Added DNSLog/OAST support with a dedicated DNSLog settings tab, automatic Interactsh detection, and temporary legacy placeholder adaptation.
- Fixed English report export language.
- Improved database cleanup so scan, AI, and FOFA history clearing also vacuums SQLite databases.
- Improved dashboard scan history status, clear confirmation dialog, and record action display.

## License

See [LICENSE](LICENSE).
