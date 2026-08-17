import heapq
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from core.paths import external_path, user_data_path
from core.network_proxy import PROXY_SCOPE_ONLINE_RESOURCES, create_session
from core.poc_generation import normalize_cve_id
from core.security_article_lookup import find_security_article_references


OFFICIAL_REPOSITORY = "projectdiscovery/nuclei-templates"
OFFICIAL_TREE_URL = (
    "https://api.github.com/repos/projectdiscovery/"
    "nuclei-templates/git/trees/main?recursive=1"
)
OFFICIAL_RAW_ROOT = (
    "https://raw.githubusercontent.com/projectdiscovery/"
    "nuclei-templates/main"
)
MAX_TEMPLATE_BYTES = 256 * 1024
MAX_TREE_BYTES = 8 * 1024 * 1024
MAX_LOCAL_FILES = 50000
MAX_LOCAL_CANDIDATES = 20
TREE_CACHE_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT = (5, 20)

GENERIC_QUERY_TERMS = {
    "arbitrary",
    "auth",
    "authenticated",
    "authentication",
    "bypass",
    "code",
    "command",
    "cve",
    "execution",
    "exploit",
    "injection",
    "poc",
    "remote",
    "rce",
    "sql",
    "unauthenticated",
    "vulnerability",
    "vuln",
}


@dataclass(frozen=True)
class PublicPOCReference:
    source: str
    content: str
    source_type: str

    def to_prompt_dict(self):
        return {
            "source": self.source,
            "source_type": self.source_type,
            "template": self.content,
        }


def _query_parts(vulnerability_name, cve_id="", user_hint=""):
    text = " ".join(
        str(value or "") for value in (vulnerability_name, cve_id, user_hint)
    )[:2000]
    normalized_cve = normalize_cve_id(text)
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]{3,}", text.lower())
        if token not in GENERIC_QUERY_TERMS and not token.isdigit()
    }
    if normalized_cve:
        year, number = normalized_cve.lower().split("-")[1:]
        tokens.discard(year)
        tokens.discard(number)
    return normalized_cve, sorted(tokens, key=lambda item: (-len(item), item))[:12]


def _candidate_score(path_text, cve_id, tokens):
    normalized_path = path_text.lower()
    if cve_id and cve_id.lower() in normalized_path:
        return 10000
    if cve_id:
        return 0
    path_tokens = set(re.findall(r"[a-z0-9]+", normalized_path))
    matched = [token for token in tokens if token in path_tokens]
    required_matches = 1 if len(tokens) <= 1 else 2
    if len(matched) < required_matches:
        return 0
    return sum(20 + len(token) for token in matched)


def _read_template(path):
    try:
        if path.stat().st_size > MAX_TEMPLATE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _default_local_roots():
    roots = []
    official_local = Path.home() / "nuclei-templates"
    cloud_library = external_path("poc_library", "cloud")
    for root in (official_local, cloud_library):
        if root.exists() and root.is_dir():
            roots.append(root)
    return roots


def _search_local_references(cve_id, tokens, local_roots, max_results):
    if cve_id:
        year = cve_id.split("-")[1]
        direct_references = []
        for root in local_roots:
            root = Path(root)
            direct_candidates = (
                root / "http" / "cves" / year / f"{cve_id}.yaml",
                root / "cves" / year / f"{cve_id}.yaml",
                root / f"{cve_id}.yaml",
            )
            for path in direct_candidates:
                if not path.is_file():
                    continue
                content = _read_template(path)
                if not content:
                    continue
                relative = path.relative_to(root).as_posix()
                root_label = "nuclei-templates" if root.name == "nuclei-templates" else "poc_library/cloud"
                direct_references.append(
                    PublicPOCReference(
                        source=f"local:{root_label}/{relative}",
                        content=content,
                        source_type="official-local" if root.name == "nuclei-templates" else "cloud-local",
                    )
                )
                if len(direct_references) >= max_results:
                    return direct_references
        if direct_references:
            return direct_references

    candidates = []
    visited = 0
    for root in local_roots:
        root = Path(root)
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if visited >= MAX_LOCAL_FILES:
                break
            if not path.is_file() or path.suffix.lower() not in (".yaml", ".yml"):
                continue
            visited += 1
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                relative = path.name
            score = _candidate_score(relative, cve_id, tokens)
            if score <= 0:
                continue
            item = (score, -len(relative), relative, path, root)
            if len(candidates) < MAX_LOCAL_CANDIDATES:
                heapq.heappush(candidates, item)
            elif item[:3] > candidates[0][:3]:
                heapq.heapreplace(candidates, item)

    references = []
    for _, _, relative, path, root in sorted(candidates, reverse=True):
        content = _read_template(path)
        if not content:
            continue
        if cve_id and cve_id.lower() not in content.lower() and cve_id.lower() not in relative.lower():
            continue
        root_label = "nuclei-templates" if root.name == "nuclei-templates" else "poc_library/cloud"
        references.append(
            PublicPOCReference(
                source=f"local:{root_label}/{relative}",
                content=content,
                source_type="official-local" if root.name == "nuclei-templates" else "cloud-local",
            )
        )
        if len(references) >= max_results:
            break
    return references


def _tree_cache_path():
    return user_data_path("cache", "official_nuclei_tree.json")


def _load_tree_cache():
    path = _tree_cache_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = float(payload.get("fetched_at", 0))
        paths = payload.get("paths", [])
        if time.time() - fetched_at > TREE_CACHE_SECONDS or not isinstance(paths, list):
            return None
        return [str(item) for item in paths]
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _save_tree_cache(paths):
    cache_path = _tree_cache_path()
    temporary_path = cache_path.with_suffix(".tmp")
    payload = {"fetched_at": time.time(), "paths": paths}
    try:
        temporary_path.write_text(json.dumps(payload), encoding="utf-8")
        temporary_path.replace(cache_path)
    except OSError:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def _response_content(response, max_bytes):
    content_length = response.headers.get("Content-Length", "")
    try:
        if content_length and int(content_length) > max_bytes:
            return b""
    except ValueError:
        return b""
    content = response.content
    if len(content) > max_bytes:
        return b""
    return content


def _fetch_official_tree(session):
    cached_paths = _load_tree_cache()
    if cached_paths is not None:
        return cached_paths

    response = session.get(
        OFFICIAL_TREE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Nuclei-GUI"},
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )
    if response.status_code != 200:
        return []
    content = _response_content(response, MAX_TREE_BYTES)
    if not content:
        return []
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    paths = [
        item.get("path", "")
        for item in payload.get("tree", [])
        if item.get("type") == "blob"
        and str(item.get("path", "")).lower().endswith((".yaml", ".yml"))
    ]
    paths = [path for path in paths if path]
    if paths:
        _save_tree_cache(paths)
    return paths


def _fetch_official_template(session, template_path):
    url = f"{OFFICIAL_RAW_ROOT}/{template_path}"
    response = session.get(
        url,
        headers={"User-Agent": "Nuclei-GUI"},
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )
    if response.status_code != 200:
        return None
    content = _response_content(response, MAX_TEMPLATE_BYTES)
    if not content:
        return None
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")
    return PublicPOCReference(url, text, "official-remote")


def _search_official_references(session, cve_id, tokens, max_results):
    references = []
    if cve_id:
        year = cve_id.split("-")[1]
        direct_path = f"http/cves/{year}/{cve_id}.yaml"
        direct_reference = _fetch_official_template(session, direct_path)
        if direct_reference:
            return [direct_reference]

    paths = _fetch_official_tree(session)
    scored_paths = []
    for path in paths:
        score = _candidate_score(path, cve_id, tokens)
        if score > 0:
            scored_paths.append((score, -len(path), path))
    for _, _, path in sorted(scored_paths, reverse=True)[: max_results * 3]:
        reference = _fetch_official_template(session, path)
        if not reference:
            continue
        references.append(reference)
        if len(references) >= max_results:
            break
    return references


def find_public_poc_references(
    vulnerability_name,
    cve_id="",
    user_hint="",
    local_roots=None,
    allow_remote=True,
    session=None,
    max_results=2,
):
    normalized_cve, tokens = _query_parts(vulnerability_name, cve_id, user_hint)
    if not normalized_cve and not tokens:
        return []

    roots = _default_local_roots() if local_roots is None else list(local_roots)
    references = _search_local_references(normalized_cve, tokens, roots, max_results)
    if references or not allow_remote:
        return references

    http = session or create_session(PROXY_SCOPE_ONLINE_RESOURCES)
    try:
        references = _search_official_references(
            http, normalized_cve, tokens, max_results
        )
        if references:
            return references
        return find_security_article_references(
            vulnerability_name,
            normalized_cve,
            user_hint,
            session=http,
            max_results=max_results,
        )
    except requests.RequestException:
        return []
