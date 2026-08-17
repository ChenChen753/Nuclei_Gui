import json
import re
from dataclasses import asdict, dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SQL_DETECTION_TYPES = {"sql_time"}
SQL_DBMS_TYPES = {"auto", "mysql", "postgresql", "mssql", "oracle"}
MIN_VALIDATION_ROUNDS = 2
MAX_VALIDATION_ROUNDS = 5


@dataclass(frozen=True)
class InjectionPoint:
    location: str
    parameter: str
    original_value: str = ""

    def to_dict(self):
        return asdict(self)


def normalize_cve_id(value):
    match = re.search(r"\bCVE-\d{4}-\d{4,7}\b", str(value or ""), re.IGNORECASE)
    return match.group(0).upper() if match else ""


def _split_raw_request(raw_request):
    text = str(raw_request or "").replace("\r\n", "\n").strip("\n")
    header_text, separator, body = text.partition("\n\n")
    lines = header_text.split("\n") if header_text else []
    if not lines:
        return None

    request_parts = lines[0].strip().split()
    if len(request_parts) < 2:
        return None

    method = request_parts[0].upper()
    target = request_parts[1]
    version = request_parts[2] if len(request_parts) > 2 else "HTTP/1.1"
    headers = []
    for line in lines[1:]:
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers.append([name.strip(), value.strip()])

    return {
        "method": method,
        "target": target,
        "version": version,
        "headers": headers,
        "body": body if separator else "",
    }


def _header_value(headers, name):
    for header_name, value in headers:
        if header_name.lower() == name.lower():
            return value
    return ""


def discover_injection_points(raw_request, include_advanced=True):
    parsed = _split_raw_request(raw_request)
    if not parsed:
        return []

    points = []
    target_parts = urlsplit(parsed["target"])
    for name, value in parse_qsl(target_parts.query, keep_blank_values=True):
        points.append(InjectionPoint("query", name, value))

    body = parsed["body"].strip()
    content_type = _header_value(parsed["headers"], "Content-Type").lower()
    if body:
        if "json" in content_type or body.startswith("{"):
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    for name, value in data.items():
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            points.append(InjectionPoint("json", str(name), "" if value is None else str(value)))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        elif "application/x-www-form-urlencoded" in content_type or "=" in body:
            for name, value in parse_qsl(body, keep_blank_values=True):
                points.append(InjectionPoint("form", name, value))

    if include_advanced:
        cookie = _header_value(parsed["headers"], "Cookie")
        for item in cookie.split(";"):
            if "=" not in item:
                continue
            name, value = item.split("=", 1)
            points.append(InjectionPoint("cookie", name.strip(), value.strip()))

        excluded_headers = {"host", "content-length", "content-type", "cookie", "connection"}
        for name, value in parsed["headers"]:
            if name.lower() not in excluded_headers:
                points.append(InjectionPoint("header", name, value))

    unique = []
    seen = set()
    for point in points:
        key = (point.location, point.parameter)
        if key not in seen:
            seen.add(key)
            unique.append(point)
    return unique


def _append_payload(value, payload):
    return f"{value}{payload}"


def inject_raw_request(raw_request, point, payload):
    parsed = _split_raw_request(raw_request)
    if not parsed:
        raise ValueError("Invalid raw HTTP request")

    if isinstance(point, dict):
        point = InjectionPoint(
            point.get("location", ""),
            point.get("parameter", ""),
            point.get("original_value", ""),
        )

    if point.location == "query":
        target_parts = urlsplit(parsed["target"])
        pairs = parse_qsl(target_parts.query, keep_blank_values=True)
        pairs = [
            (name, _append_payload(value, payload) if name == point.parameter else value)
            for name, value in pairs
        ]
        parsed["target"] = urlunsplit(
            (target_parts.scheme, target_parts.netloc, target_parts.path, urlencode(pairs), target_parts.fragment)
        )
    elif point.location == "form":
        pairs = parse_qsl(parsed["body"], keep_blank_values=True)
        pairs = [
            (name, _append_payload(value, payload) if name == point.parameter else value)
            for name, value in pairs
        ]
        parsed["body"] = urlencode(pairs)
    elif point.location == "json":
        data = json.loads(parsed["body"])
        if point.parameter not in data:
            raise ValueError("JSON injection parameter not found")
        data[point.parameter] = _append_payload(str(data[point.parameter]), payload)
        parsed["body"] = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    elif point.location == "cookie":
        for header in parsed["headers"]:
            if header[0].lower() != "cookie":
                continue
            cookie_parts = []
            for item in header[1].split(";"):
                if "=" not in item:
                    cookie_parts.append(item.strip())
                    continue
                name, value = item.split("=", 1)
                value = _append_payload(value.strip(), payload) if name.strip() == point.parameter else value.strip()
                cookie_parts.append(f"{name.strip()}={value}")
            header[1] = "; ".join(cookie_parts)
    elif point.location == "header":
        for header in parsed["headers"]:
            if header[0].lower() == point.parameter.lower():
                header[1] = _append_payload(header[1], payload)
                break
    else:
        raise ValueError(f"Unsupported injection location: {point.location}")

    lines = [f"{parsed['method']} {parsed['target']} {parsed['version']}"]
    for name, value in parsed["headers"]:
        if name.lower() == "host":
            value = "{{Host}}"
        elif name.lower() == "content-length":
            continue
        lines.append(f"{name}: {value}")
    if parsed["body"]:
        lines.extend(["", parsed["body"]])
    else:
        lines.append("")
    return "\n".join(lines)


def time_sql_payloads(dbms="auto", delay_seconds=5):
    dbms = str(dbms or "auto").lower()
    if dbms not in SQL_DBMS_TYPES:
        dbms = "auto"
    effective_dbms = "mysql" if dbms == "auto" else dbms
    delay = max(1, min(int(delay_seconds or 5), 30))

    control_payloads = {
        "mysql": "' AND 1=1-- -",
        "postgresql": "' AND 1=1--",
        "mssql": "' AND 1=1--",
        "oracle": "' AND 1=1--",
    }
    time_payloads = {
        "mysql": f"' AND SLEEP({delay})-- -",
        "postgresql": f"'; SELECT pg_sleep({delay})--",
        "mssql": f"'; WAITFOR DELAY '0:0:{delay}'--",
        "oracle": f"' AND 1=(SELECT DBMS_PIPE.RECEIVE_MESSAGE('a',{delay}) FROM dual)--",
    }

    return {
        "control": control_payloads[effective_dbms],
        "delay": time_payloads[effective_dbms],
        "delay_seconds": delay,
    }


def clamp_validation_rounds(value):
    try:
        rounds = int(value or MIN_VALIDATION_ROUNDS)
    except (TypeError, ValueError):
        rounds = MIN_VALIDATION_ROUNDS
    return max(MIN_VALIDATION_ROUNDS, min(rounds, MAX_VALIDATION_ROUNDS))


def build_time_probe_requests(raw_request, point, dbms="auto", delay_seconds=5, validation_rounds=2):
    payloads = time_sql_payloads(dbms, delay_seconds)
    rounds = clamp_validation_rounds(validation_rounds)
    requests = []
    for _ in range(rounds):
        requests.extend([
            inject_raw_request(raw_request, point, ""),
            inject_raw_request(raw_request, point, payloads["control"]),
            inject_raw_request(raw_request, point, payloads["delay"]),
        ])
    return requests


def time_matcher_config(delay_seconds=5, validation_rounds=2):
    delay = max(1, min(int(delay_seconds or 5), 30))
    rounds = clamp_validation_rounds(validation_rounds)
    threshold = max(1, delay - 1)
    expressions = []
    for round_index in range(rounds):
        baseline_index = round_index * 3 + 1
        control_index = baseline_index + 1
        delay_index = baseline_index + 2
        expressions.extend([
            f"duration_{delay_index} >= {delay}",
            f"duration_{delay_index} - duration_{baseline_index} >= {threshold}",
            f"duration_{delay_index} - duration_{control_index} >= {threshold}",
        ])
    return {
        "req-condition": True,
        "matchers": [
            {
                "type": "dsl",
                "dsl": expressions,
                "condition": "and",
            }
        ],
    }


def parse_ai_analysis_result(text):
    source = str(text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", source, re.IGNORECASE | re.DOTALL)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(source)

    decoder = json.JSONDecoder()
    for candidate in candidates:
        for index, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                data, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue

            detection_type = str(data.get("detection_type", "normal")).lower()
            if detection_type not in SQL_DETECTION_TYPES | {"normal"}:
                detection_type = "normal"
            dbms = str(data.get("dbms", "auto")).lower()
            if dbms not in SQL_DBMS_TYPES:
                dbms = "auto"

            data["detection_type"] = detection_type
            data["dbms"] = dbms
            data["cve_id"] = normalize_cve_id(data.get("cve_id"))
            try:
                data["delay_seconds"] = max(1, min(int(data.get("delay_seconds", 5)), 30))
            except (TypeError, ValueError):
                data["delay_seconds"] = 5
            data["validation_rounds"] = clamp_validation_rounds(data.get("validation_rounds", 2))
            if not isinstance(data.get("steps"), list):
                data["steps"] = []
            if not isinstance(data.get("injection"), dict):
                data["injection"] = {}
            return data
    return None
