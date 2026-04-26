import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


STANDARD_OAST_MARKERS = (
    "{{interactsh-url}}",
    "interactsh_protocol",
    "interactsh_request",
    "interactsh_response",
)

LEGACY_DNSLOG_PLACEHOLDERS = (
    "{{dnslog}}",
    "{{dnslog_domain}}",
    "{{dnslog-domain}}",
    "{{dnslog_url}}",
    "{{dnslog-url}}",
    "{{callback_url}}",
    "{{callback-url}}",
    "{{callback_domain}}",
    "{{callback-domain}}",
    "{{oast}}",
    "{{oast_url}}",
    "{{oast-url}}",
    "{{oast_domain}}",
    "{{oast-domain}}",
    "{{ceye_domain}}",
    "{{ceye-domain}}",
    "{{ceye_url}}",
    "{{ceye-url}}",
)


@dataclass
class OASTScanPlan:
    templates: list
    args: list = field(default_factory=list)
    enabled: bool = False
    disabled: bool = False
    mode: str = "auto"
    standard_count: int = 0
    legacy_count: int = 0
    adapted_count: int = 0
    temp_dir: str = ""
    warnings: list = field(default_factory=list)


def get_default_oast_config():
    return {
        "oast_mode": "auto",
        "oast_server": "",
        "oast_token": "",
        "oast_poll_duration": 5,
        "oast_cooldown_period": 5,
        "oast_cache_size": 5000,
        "oast_eviction": 60,
        "oast_adapt_legacy": True,
    }


def normalize_oast_config(config):
    normalized = get_default_oast_config()
    normalized.update(config or {})

    mode = str(normalized.get("oast_mode", "auto")).lower()
    if mode not in {"auto", "off", "force"}:
        mode = "auto"
    normalized["oast_mode"] = mode

    for key in (
        "oast_poll_duration",
        "oast_cooldown_period",
        "oast_cache_size",
        "oast_eviction",
    ):
        try:
            normalized[key] = int(normalized.get(key, 0))
        except (TypeError, ValueError):
            normalized[key] = get_default_oast_config()[key]

    normalized["oast_adapt_legacy"] = _to_bool(normalized.get("oast_adapt_legacy", True))
    normalized["oast_server"] = str(normalized.get("oast_server", "") or "").strip()
    normalized["oast_token"] = str(normalized.get("oast_token", "") or "").strip()
    return normalized


def prepare_oast_scan(template_paths, config):
    config = normalize_oast_config(config)
    template_paths = list(template_paths or [])
    standard_paths, legacy_paths = analyze_oast_templates(template_paths)
    mode = config["oast_mode"]

    plan = OASTScanPlan(
        templates=template_paths,
        mode=mode,
        standard_count=len(standard_paths),
        legacy_count=len(legacy_paths),
    )

    if mode == "off":
        plan.disabled = True
        plan.args = ["-ni"]
        return plan

    if config["oast_adapt_legacy"] and legacy_paths:
        plan.templates, plan.temp_dir, plan.adapted_count = adapt_legacy_templates(template_paths, legacy_paths)
    elif legacy_paths:
        plan.warnings.append("legacy_placeholders_not_adapted")

    plan.enabled = mode == "force" or plan.standard_count > 0 or plan.legacy_count > 0
    if plan.enabled:
        plan.args = build_interactsh_args(config)

    return plan


def cleanup_oast_plan(plan):
    if plan and plan.temp_dir and os.path.isdir(plan.temp_dir):
        shutil.rmtree(plan.temp_dir, ignore_errors=True)


def analyze_oast_templates(template_paths):
    standard_paths = set()
    legacy_paths = set()

    for template_path in template_paths or []:
        path = Path(str(template_path))
        for file_path in _iter_template_files(path):
            text = _read_text(file_path)
            if not text:
                continue
            if any(marker in text for marker in STANDARD_OAST_MARKERS):
                standard_paths.add(str(file_path))
            if any(marker in text for marker in LEGACY_DNSLOG_PLACEHOLDERS):
                legacy_paths.add(str(file_path))

    return standard_paths, legacy_paths


def adapt_legacy_templates(template_paths, legacy_paths):
    temp_dir = tempfile.mkdtemp(prefix="nuclei_gui_oast_")
    adapted_count = 0
    adapted_map = {}
    adapted_dirs = {}

    for legacy_path in legacy_paths:
        source = Path(legacy_path)
        if not source.is_file():
            continue

        text = _read_text(source)
        replaced = replace_legacy_placeholders(text)
        if replaced == text:
            continue

        digest = hashlib.sha1(str(source).encode("utf-8", errors="ignore")).hexdigest()[:10]
        temp_name = f"{source.stem}_{digest}{source.suffix or '.yaml'}"
        temp_path = Path(temp_dir) / temp_name
        temp_path.write_text(replaced, encoding="utf-8")
        adapted_map[str(source)] = str(temp_path)
        adapted_count += 1

    prepared_templates = []
    for template_path in template_paths or []:
        path = Path(str(template_path))
        if path.is_dir():
            if str(path) in adapted_dirs:
                prepared_templates.append(adapted_dirs[str(path)])
                continue
            legacy_children = [Path(p) for p in legacy_paths if _is_relative_to(Path(p), path)]
            if legacy_children:
                digest = hashlib.sha1(str(path).encode("utf-8", errors="ignore")).hexdigest()[:10]
                temp_subdir = Path(temp_dir) / f"{path.name}_{digest}"
                shutil.copytree(path, temp_subdir)
                for legacy_child in legacy_children:
                    target_file = temp_subdir / legacy_child.relative_to(path)
                    text = _read_text(target_file)
                    replaced = replace_legacy_placeholders(text)
                    if replaced != text:
                        target_file.write_text(replaced, encoding="utf-8")
                adapted_dirs[str(path)] = str(temp_subdir)
                prepared_templates.append(str(temp_subdir))
                continue
        prepared_templates.append(adapted_map.get(str(path), str(template_path)))

    return prepared_templates, temp_dir, adapted_count


def replace_legacy_placeholders(text):
    replaced = text or ""
    for placeholder in LEGACY_DNSLOG_PLACEHOLDERS:
        replaced = replaced.replace(placeholder, "{{interactsh-url}}")
    return replaced


def build_interactsh_args(config):
    args = []

    server = config.get("oast_server")
    if server:
        args.extend(["-iserver", server])

    token = config.get("oast_token")
    if token:
        args.extend(["-itoken", token])

    option_map = (
        ("oast_cache_size", "-interactions-cache-size"),
        ("oast_eviction", "-interactions-eviction"),
        ("oast_poll_duration", "-interactions-poll-duration"),
        ("oast_cooldown_period", "-interactions-cooldown-period"),
    )
    for config_key, cli_flag in option_map:
        value = int(config.get(config_key, 0) or 0)
        if value > 0:
            args.extend([cli_flag, str(value)])

    return args


def _iter_template_files(path):
    if path.is_file():
        yield path
        return

    if path.is_dir():
        for root, _, files in os.walk(path):
            for filename in files:
                file_path = Path(root) / filename
                if file_path.suffix.lower() in {".yaml", ".yml"}:
                    yield file_path


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def _is_relative_to(path, parent):
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False
