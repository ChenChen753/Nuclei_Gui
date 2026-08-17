from urllib.parse import urlsplit, urlunsplit


def normalize_target(target):
    """Return a root asset URL used for display, queueing, and scanning."""
    if not isinstance(target, str):
        return ""

    target = target.strip()
    if not target:
        return ""

    if not target.lower().startswith(("http://", "https://")):
        target = "http://" + target

    parts = urlsplit(target)
    if not parts.scheme or not parts.netloc:
        return target

    scheme = parts.scheme.lower()
    hostname = parts.hostname
    if not hostname:
        return target

    try:
        port = parts.port
    except ValueError:
        return target

    host = hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    userinfo = ""
    if parts.username:
        userinfo = parts.username
        if parts.password is not None:
            userinfo += f":{parts.password}"
        userinfo += "@"

    is_default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    port_suffix = "" if port is None or is_default_port else f":{port}"
    netloc = f"{userinfo}{host}{port_suffix}"
    return urlunsplit((scheme, netloc, "", "", ""))


def dedupe_targets(targets):
    """Normalize targets and remove duplicates while preserving input order."""
    unique_targets = []
    seen = set()

    for target in targets or []:
        normalized = normalize_target(target)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_targets.append(normalized)

    return unique_targets


def parse_targets_text(text):
    """Parse multiline target text into normalized, deduplicated targets."""
    return dedupe_targets((text or "").splitlines())


def get_target_url_context(target):
    """Build the URL variables used by Nuclei-style HTTP templates."""
    normalized = normalize_target(target)
    parts = urlsplit(normalized)
    if not parts.scheme or not parts.netloc:
        return {
            "target": normalized,
            "base_url": normalized.rstrip("/"),
            "root_url": normalized.rstrip("/"),
            "hostname": "",
            "host": "",
        }

    root_url = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
    host = parts.netloc.rsplit("@", 1)[-1]
    return {
        "target": normalized,
        "base_url": root_url,
        "root_url": root_url,
        "hostname": parts.hostname or "",
        "host": host,
    }


def substitute_template_url_variables(target, value):
    """Replace the URL variables shared by Nuclei HTTP templates."""
    context = get_target_url_context(target)
    text = str(value or "")
    replacements = {
        "{{BaseURL}}": context["base_url"],
        "{{RootURL}}": context["root_url"],
        "{{Hostname}}": context["hostname"],
        "{{Host}}": context["host"],
    }
    for placeholder, replacement in replacements.items():
        text = text.replace(placeholder, replacement)
    return text


def get_result_target_url(*results):
    """Prefer the original scan URL over the final matched URL."""
    mappings = [result for result in results if isinstance(result, dict)]
    for keys in (("url", "target"), ("matched-at", "matched_at", "matched")):
        for result in mappings:
            for key in keys:
                value = result.get(key)
                if value:
                    return str(value)
    return ""


def resolve_template_url(target, template_path):
    """Resolve a Nuclei-style template path against a scan target."""
    context = get_target_url_context(target)
    value = substitute_template_url_variables(target, template_path).strip()

    lower_value = value.lower()
    if lower_value.startswith(("http://", "https://")):
        return value
    if value.startswith("//"):
        scheme = urlsplit(context["root_url"]).scheme or "http"
        return f"{scheme}:{value}"
    if value.startswith("/"):
        return f"{context['root_url']}{value}"
    if value.startswith(("?", "#")):
        return f"{context['base_url']}{value}"
    if not value:
        return context["base_url"]
    return f"{context['base_url'].rstrip('/')}/{value.lstrip('/')}"
