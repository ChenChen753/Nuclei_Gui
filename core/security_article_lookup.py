import html
import ipaddress
import json
import re
import socket
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import quote, urlencode, urljoin, urlsplit

import requests

from core.poc_generation import normalize_cve_id
from core.network_proxy import PROXY_SCOPE_ONLINE_RESOURCES, create_session
from core.paths import user_data_path


CVE_API_ROOT = "https://cveawg.mitre.org/api/cve"
GITHUB_REPOSITORY_SEARCH_URL = "https://api.github.com/search/repositories"
BING_SEARCH_URL = "https://www.bing.com/search"
REQUEST_TIMEOUT = (5, 18)
MAX_SEARCH_BYTES = 1024 * 1024
MAX_ARTICLE_BYTES = 512 * 1024
MAX_ARTICLE_TEXT = 18000
MAX_REDIRECTS = 2
MAX_GITHUB_TREE_BYTES = 8 * 1024 * 1024
GITHUB_TREE_CACHE_SECONDS = 24 * 60 * 60

GITHUB_POC_COLLECTIONS = (
    {
        "repository": "eeeeeeeeee-code/POC",
        "branch": "main",
        "path_prefix": "wpoc/",
    },
)

GITHUB_POC_EXTENSIONS = {
    ".go",
    ".java",
    ".json",
    ".md",
    ".php",
    ".py",
    ".rb",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9",
}

GENERIC_TERMS = {
    "analysis",
    "article",
    "bypass",
    "code",
    "execution",
    "exploit",
    "poc",
    "remote",
    "rce",
    "security",
    "vulnerability",
    "vuln",
}

SEARCH_QUALIFIERS = {
    "arbitrary",
    "authenticated",
    "pre-auth",
    "preauth",
    "remote",
    "unauthenticated",
}

COLLECTION_GENERIC_TERMS = GENERIC_TERMS | SEARCH_QUALIFIERS | {
    "command",
    "disclosure",
    "file",
    "injection",
    "read",
    "sql",
    "ssrf",
    "upload",
    "write",
    "xss",
}


@dataclass(frozen=True)
class SecurityArticleReference:
    source: str
    content: str
    source_type: str

    def to_prompt_dict(self):
        return {
            "source": self.source,
            "source_type": self.source_type,
            "article_text": self.content,
        }


class _ArticleTextParser(HTMLParser):
    BLOCK_TAGS = {
        "article",
        "blockquote",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "main",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
    }
    SKIP_TAGS = {"canvas", "noscript", "script", "style", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        elif not self._skip_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif not self._skip_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth:
            self.parts.append(data)

    def text(self):
        value = html.unescape(" ".join(self.parts))
        value = re.sub(r"[ \t\f\v]+", " ", value)
        value = re.sub(r"\n\s*\n+", "\n\n", value)
        return value.strip()


def _query_parts(vulnerability_name, cve_id="", user_hint=""):
    text = " ".join(
        str(value or "") for value in (vulnerability_name, cve_id, user_hint)
    )[:2000]
    normalized_cve = normalize_cve_id(text)
    latin_tokens = re.findall(r"[a-z0-9][a-z0-9._-]{2,}", text.lower())
    chinese_tokens = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    tokens = []
    for token in latin_tokens + chinese_tokens:
        if token in GENERIC_TERMS or token.isdigit() or token in tokens:
            continue
        if token.startswith("cve-"):
            continue
        tokens.append(token)
    return normalized_cve, tokens[:12], text.strip()


def _bounded_content(response, max_bytes):
    content_length = response.headers.get("Content-Length", "")
    try:
        if content_length and int(content_length) > max_bytes:
            return b""
    except ValueError:
        return b""

    if hasattr(response, "iter_content"):
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=16384):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                return b""
            chunks.append(chunk)
        return b"".join(chunks)

    content = response.content
    return content if len(content) <= max_bytes else b""


def _public_web_url(url):
    try:
        parsed = urlsplit(str(url or ""))
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    if port not in (None, 80, 443):
        return False
    host = parsed.hostname.rstrip(".").lower()
    if host in ("localhost", "localhost.localdomain") or host.endswith(".localhost"):
        return False
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(host, port or (443 if parsed.scheme == "https" else 80))
        }
    except OSError:
        return False
    if not addresses:
        return False
    try:
        return all(ipaddress.ip_address(address).is_global for address in addresses)
    except ValueError:
        return False


def _get_public_content(session, url, max_bytes=MAX_ARTICLE_BYTES):
    current_url = str(url or "")
    for _ in range(MAX_REDIRECTS + 1):
        if not _public_web_url(current_url):
            return "", b"", ""
        response = session.get(
            current_url,
            headers=BROWSER_HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
            stream=True,
        )
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location", "")
            if not location:
                return "", b"", ""
            current_url = urljoin(current_url, location)
            continue
        if response.status_code != 200:
            return "", b"", ""
        content_type = response.headers.get("Content-Type", "").lower()
        supported_type = any(
            value in content_type
            for value in ("text/", "application/xhtml+xml", "application/json")
        )
        if content_type and not supported_type:
            return "", b"", ""
        content = _bounded_content(response, max_bytes)
        return current_url, content, content_type
    return "", b"", ""


def _decode_text(content, content_type=""):
    charset_match = re.search(r"charset=([a-z0-9._-]+)", content_type, re.IGNORECASE)
    encodings = [charset_match.group(1)] if charset_match else []
    encodings.extend(["utf-8", "gb18030", "latin-1"])
    for encoding in encodings:
        try:
            return content.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return content.decode("utf-8", errors="replace")


def _article_text(content, content_type):
    text = _decode_text(content, content_type)
    if "html" in content_type or re.search(r"<\s*(html|body|article)\b", text, re.IGNORECASE):
        parser = _ArticleTextParser()
        try:
            parser.feed(text)
            text = parser.text()
        except Exception:
            text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_ARTICLE_TEXT]


def _text_match_score(text, cve_id, tokens):
    lowered = str(text or "").lower()
    if cve_id and cve_id.lower() not in lowered:
        return 0
    matched = sum(1 for token in tokens if token.lower() in lowered)
    if not cve_id and tokens and matched < min(2, len(tokens)):
        return 0
    return (100 if cve_id else 0) + matched * 10


def _fixed_json_request(session, url, max_bytes=MAX_SEARCH_BYTES, headers=None):
    response = session.get(
        url,
        headers=headers or {"User-Agent": "Nuclei-GUI"},
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )
    if response.status_code != 200:
        return None
    content = _bounded_content(response, max_bytes)
    if not content:
        return None
    try:
        return json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _github_tree_cache_path(repository, branch):
    cache_name = re.sub(r"[^a-z0-9_.-]+", "_", f"{repository}_{branch}".lower())
    return user_data_path("cache", f"github_poc_tree_{cache_name}.json")


def _load_github_tree_cache(repository, branch):
    path = _github_tree_cache_path(repository, branch)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("repository") != repository or payload.get("branch") != branch:
            return None
        if time.time() - float(payload.get("fetched_at", 0)) > GITHUB_TREE_CACHE_SECONDS:
            return None
        files = payload.get("files", [])
        return files if isinstance(files, list) else None
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _save_github_tree_cache(repository, branch, files):
    path = _github_tree_cache_path(repository, branch)
    temporary_path = path.with_suffix(".tmp")
    payload = {
        "repository": repository,
        "branch": branch,
        "fetched_at": time.time(),
        "files": files,
    }
    try:
        temporary_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary_path.replace(path)
    except OSError:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def _github_collection_files(session, repository, branch, path_prefix):
    cached = _load_github_tree_cache(repository, branch)
    if cached is not None:
        return cached
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        return []
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", branch):
        return []

    tree_url = (
        f"https://api.github.com/repos/{repository}/git/trees/"
        f"{quote(branch, safe='')}?recursive=1"
    )
    payload = _fixed_json_request(
        session,
        tree_url,
        max_bytes=MAX_GITHUB_TREE_BYTES,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Nuclei-GUI"},
    )
    if not isinstance(payload, dict) or payload.get("truncated") is True:
        return []

    files = []
    for item in payload.get("tree", []) or []:
        if not isinstance(item, dict) or item.get("type") != "blob":
            continue
        path = str(item.get("path", ""))
        if path_prefix and not path.startswith(path_prefix):
            continue
        extension = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if extension not in GITHUB_POC_EXTENSIONS:
            continue
        try:
            size = int(item.get("size", 0) or 0)
        except (TypeError, ValueError):
            size = 0
        if size > MAX_ARTICLE_BYTES:
            continue
        files.append({"path": path, "size": size})
    if files:
        _save_github_tree_cache(repository, branch, files)
    return files


def _collection_query_terms(tokens):
    terms = []
    for token in tokens:
        normalized = str(token).lower()
        if normalized in COLLECTION_GENERIC_TERMS:
            continue
        if re.search(r"[\u4e00-\u9fff]", normalized):
            if normalized not in terms:
                terms.append(normalized)
            continue
        for part in re.findall(r"[a-z0-9]+", normalized):
            if len(part) < 3 or part in COLLECTION_GENERIC_TERMS or part.isdigit():
                continue
            if part not in terms:
                terms.append(part)
    return terms[:10]


def _collection_path_score(path, cve_id, query_terms):
    normalized_path = str(path or "").lower()
    if cve_id and cve_id.lower() in normalized_path:
        return 10000
    if cve_id:
        return 0

    path_latin_terms = set(re.findall(r"[a-z0-9]+", normalized_path))
    matched = []
    for term in query_terms:
        if re.search(r"[\u4e00-\u9fff]", term):
            if term in normalized_path:
                matched.append(term)
        elif term in path_latin_terms:
            matched.append(term)
    required_matches = 1 if len(query_terms) <= 1 else 2
    if len(matched) < required_matches:
        return 0
    return sum(20 + len(term) for term in matched)


def _fetch_github_collection_file(session, repository, branch, path):
    encoded_path = quote(path, safe="/")
    raw_url = (
        f"https://raw.githubusercontent.com/{repository}/"
        f"{quote(branch, safe='')}/{encoded_path}"
    )
    response = session.get(
        raw_url,
        headers={"User-Agent": "Nuclei-GUI"},
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )
    if response.status_code != 200:
        return None
    content = _bounded_content(response, MAX_ARTICLE_BYTES)
    if not content:
        return None
    text = _article_text(content, response.headers.get("Content-Type", "text/plain"))
    if not text:
        return None
    source_url = (
        f"https://github.com/{repository}/blob/"
        f"{quote(branch, safe='')}/{encoded_path}"
    )
    return SecurityArticleReference(source_url, text, "github-poc-file")


def _github_collection_references(session, cve_id, tokens, max_results):
    query_terms = _collection_query_terms(tokens)
    if not cve_id and not query_terms:
        return []

    candidates = []
    for collection in GITHUB_POC_COLLECTIONS:
        repository = collection["repository"]
        branch = collection["branch"]
        files = _github_collection_files(
            session, repository, branch, collection.get("path_prefix", "")
        )
        for item in files:
            path = str(item.get("path", ""))
            score = _collection_path_score(path, cve_id, query_terms)
            if score > 0:
                candidates.append((score, repository, branch, path))

    references = []
    seen_sources = set()
    for _, repository, branch, path in sorted(candidates, reverse=True)[: max_results * 4]:
        reference = _fetch_github_collection_file(
            session, repository, branch, path
        )
        if not reference or reference.source in seen_sources:
            continue
        verification_text = f"{path}\n{reference.content}"
        if _text_match_score(verification_text, cve_id, query_terms) <= 0:
            continue
        seen_sources.add(reference.source)
        references.append(reference)
        if len(references) >= max_results:
            break
    return references


def _cve_article_candidates(session, cve_id):
    if not cve_id:
        return []
    payload = _fixed_json_request(session, f"{CVE_API_ROOT}/{cve_id}")
    if not isinstance(payload, dict):
        return []

    scored = []
    containers = payload.get("containers", {})
    for container in [containers.get("cna", {})] + list(containers.get("adp", []) or []):
        if not isinstance(container, dict):
            continue
        for reference in container.get("references", []) or []:
            if not isinstance(reference, dict):
                continue
            url = str(reference.get("url", ""))
            tags = {str(tag).lower() for tag in reference.get("tags", []) or []}
            score = 60
            if "technical-description" in tags:
                score += 50
            if "vendor-advisory" in tags:
                score += 35
            if "exploit" in tags:
                score += 45
            if url:
                scored.append((score, url, "cve-article"))
    return sorted(set(scored), reverse=True)


def _bing_article_candidates(session, query_text, cve_id, tokens):
    if not query_text:
        return [], []
    search_query = f'"{cve_id or query_text[:160]}" vulnerability analysis POC'
    url = f"{BING_SEARCH_URL}?{urlencode({'q': search_query, 'format': 'rss', 'mkt': 'en-US', 'setlang': 'en-US'})}"
    response = session.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )
    if response.status_code != 200:
        return [], []
    content = _bounded_content(response, MAX_SEARCH_BYTES)
    if not content:
        return [], []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return [], []

    candidates = []
    discovered_cves = []
    for item in root.findall("./channel/item")[:10]:
        title = item.findtext("title", default="")
        link = item.findtext("link", default="")
        description = item.findtext("description", default="")
        summary = f"{title}\n{description}\n{link}"
        score = _text_match_score(summary, cve_id, tokens)
        if score <= 0 or not link:
            continue
        lowered = summary.lower()
        score += sum(
            8 for word in ("analysis", "advisory", "exploit", "technical", "writeup")
            if word in lowered
        )
        candidates.append((score, link, "search-article"))
        discovered = normalize_cve_id(summary)
        if discovered and discovered not in discovered_cves:
            discovered_cves.append(discovered)
    return sorted(set(candidates), reverse=True), discovered_cves


def _github_writeups(session, query_text, cve_id, tokens, max_results):
    if cve_id:
        terms = [cve_id, "POC"]
    else:
        terms = [token for token in tokens if token not in SEARCH_QUALIFIERS][:4]
    if not terms:
        return []
    query = " ".join(terms)
    url = f"{GITHUB_REPOSITORY_SEARCH_URL}?{urlencode({'q': query, 'sort': 'stars', 'order': 'desc', 'per_page': 5})}"
    payload = _fixed_json_request(
        session,
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Nuclei-GUI"},
    )
    if not isinstance(payload, dict):
        return []

    references = []
    for item in payload.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        full_name = str(item.get("full_name", ""))
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", full_name):
            continue
        summary = " ".join(
            str(item.get(key, "")) for key in ("full_name", "description", "html_url")
        )
        if _text_match_score(summary, cve_id, tokens) <= 0:
            continue
        readme_url = f"https://api.github.com/repos/{full_name}/readme"
        response = session.get(
            readme_url,
            headers={"Accept": "application/vnd.github.raw+json", "User-Agent": "Nuclei-GUI"},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        if response.status_code != 200:
            continue
        content = _bounded_content(response, MAX_ARTICLE_BYTES)
        if not content:
            continue
        text = _article_text(content, response.headers.get("Content-Type", "text/plain"))
        if _text_match_score(f"{summary}\n{text}", cve_id, tokens) <= 0:
            continue
        references.append(
            SecurityArticleReference(
                source=str(item.get("html_url", f"https://github.com/{full_name}")),
                content=text,
                source_type="github-writeup",
            )
        )
        if len(references) >= max_results:
            break
    return references


def find_security_article_references(
    vulnerability_name,
    cve_id="",
    user_hint="",
    session=None,
    max_results=2,
):
    normalized_cve, tokens, query_text = _query_parts(
        vulnerability_name, cve_id, user_hint
    )
    if not normalized_cve and not tokens:
        return []

    http = session or create_session(PROXY_SCOPE_ONLINE_RESOURCES)
    try:
        references = _github_collection_references(
            http, normalized_cve, tokens, max_results
        )
        if len(references) >= max_results:
            return references

        bing_candidates, discovered_cves = _bing_article_candidates(
            http, query_text, normalized_cve, tokens
        )
        if not normalized_cve and discovered_cves:
            normalized_cve = discovered_cves[0]

        candidates = _cve_article_candidates(http, normalized_cve)
        candidates.extend(bing_candidates)
        deduplicated = []
        seen_urls = set()
        for score, url, source_type in sorted(candidates, reverse=True):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            deduplicated.append((score, url, source_type))

        for _, url, source_type in deduplicated[:6]:
            final_url, content, content_type = _get_public_content(http, url)
            if not content:
                continue
            text = _article_text(content, content_type)
            if _text_match_score(text, normalized_cve, tokens) <= 0:
                continue
            references.append(SecurityArticleReference(final_url, text, source_type))
            if len(references) >= max_results:
                return references

        remaining = max_results - len(references)
        if remaining > 0:
            references.extend(
                _github_writeups(http, query_text, normalized_cve, tokens, remaining)
            )
        return references[:max_results]
    except requests.RequestException:
        return []
