import json
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


class _ScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts = []
        self._in_script = False
        self._script_type = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "script":
            return
        self._in_script = True
        self._script_type = None
        self._buf = []
        for key, value in attrs:
            if key.lower() == "type":
                self._script_type = value

    def handle_data(self, data):
        if self._in_script:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag.lower() != "script" or not self._in_script:
            return
        content = "".join(self._buf).strip()
        self.scripts.append((self._script_type, content))
        self._in_script = False
        self._script_type = None
        self._buf = []


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"br", "p", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in {"p", "li", "ul", "ol"}:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self) -> str:
        text = "".join(self.parts)
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join([line for line in lines if line])


class _MetaExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        attrs_dict = dict(attrs)
        key = attrs_dict.get("property") or attrs_dict.get("name")
        value = attrs_dict.get("content")
        if key and value:
            self.meta[key] = value


class _IndeedHTMLExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts = []
        self.company_parts = []
        self.description_parts = []
        self._title_depth = 0
        self._company_depth = 0
        self._desc_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = dict(attrs)

        if self._title_depth:
            self._title_depth += 1
        if self._company_depth:
            self._company_depth += 1
        if self._desc_depth:
            self._desc_depth += 1

        if self._title_depth == 0 and tag == "h1":
            self._title_depth = 1

        if self._company_depth == 0 and _is_company_tag(attrs_dict):
            self._company_depth = 1

        if self._desc_depth == 0 and _is_description_tag(attrs_dict):
            self._desc_depth = 1

        if self._desc_depth and tag in {"br", "p", "li"}:
            self.description_parts.append("\n")

        company_attr = attrs_dict.get("data-company-name") or attrs_dict.get(
            "data-companyname"
        )
        if company_attr and _looks_like_name(company_attr):
            self.company_parts.append(company_attr)

    def handle_endtag(self, tag):
        tag = tag.lower()

        if self._desc_depth and tag in {"p", "li", "ul", "ol"}:
            self.description_parts.append("\n")

        if self._title_depth:
            self._title_depth -= 1
        if self._company_depth:
            self._company_depth -= 1
        if self._desc_depth:
            self._desc_depth -= 1

    def handle_data(self, data):
        if self._title_depth:
            self.title_parts.append(data)
        if self._company_depth:
            self.company_parts.append(data)
        if self._desc_depth:
            self.description_parts.append(data)

    def get_title(self) -> str:
        return _clean_text(" ".join(self.title_parts))

    def get_company(self) -> str:
        return _clean_text(" ".join(self.company_parts))

    def get_description(self) -> str:
        return _clean_lines("".join(self.description_parts))


def _read_local(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _http_get(url: str, headers: dict) -> str:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    request = urllib.request.Request(url, headers=headers)
    with opener.open(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_html(url: str) -> str:
    local_path = None
    if url.startswith("file://"):
        local_path = Path(url[7:])
    else:
        candidate = Path(url)
        if candidate.exists():
            local_path = candidate

    if local_path:
        return _read_local(local_path)

    header_sets = [
        {"User-Agent": "Mozilla/5.0 (job-tool)"},
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-CA,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
    ]

    last_error = None
    for headers in header_sets:
        try:
            return _http_get(url, headers)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {403, 429}:
                break

    if last_error:
        raise last_error

    raise RuntimeError("Failed to fetch HTML.")


def _extract_json_ld(html: str):
    collector = _ScriptCollector()
    collector.feed(html)
    payloads = []
    for script_type, content in collector.scripts:
        if not content:
            continue
        if script_type and script_type.lower() != "application/ld+json":
            continue
        try:
            payloads.append(json.loads(content))
        except json.JSONDecodeError:
            continue
    return payloads


def _is_job_posting(data) -> bool:
    if not isinstance(data, dict):
        return False
    job_type = data.get("@type")
    if isinstance(job_type, list):
        return "JobPosting" in job_type
    return job_type == "JobPosting"


def _find_job_posting(data):
    if isinstance(data, dict):
        if _is_job_posting(data):
            return data
        for value in data.values():
            found = _find_job_posting(value)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_job_posting(item)
            if found:
                return found
    return None


def _strip_html(value: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(value or "")
    return extractor.get_text()


def _clean_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def _clean_lines(value: str) -> str:
    lines = [line.strip() for line in (value or "").splitlines()]
    return "\n".join([line for line in lines if line])


def _looks_like_name(value: str) -> bool:
    cleaned = (value or "").strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if lowered in {"true", "false"}:
        return False
    return any(char.isalpha() for char in cleaned)


def _is_company_tag(attrs: dict) -> bool:
    if "data-company-name" in attrs or "data-companyname" in attrs:
        return True
    testid = (attrs.get("data-testid") or "").strip().lower()
    if testid in {"company-name", "companyname", "company-name-link"}:
        return True
    if "company" in testid and "name" in testid:
        return True
    class_attr = attrs.get("class") or ""
    class_lower = class_attr.lower()
    return "companyname" in class_lower or "company-name" in class_lower


def _is_description_tag(attrs: dict) -> bool:
    if attrs.get("id") == "jobDescriptionText":
        return True
    testid = (attrs.get("data-testid") or "").strip()
    if testid in {"jobDescriptionText", "job-description"}:
        return True
    class_attr = attrs.get("class") or ""
    return "jobDescriptionText" in class_attr or "jobsearch-jobDescriptionText" in class_attr


def _normalize_job(job_posting: dict) -> dict:
    title = job_posting.get("title") or job_posting.get("name") or ""
    org = job_posting.get("hiringOrganization")
    company = ""
    if isinstance(org, dict):
        company = org.get("name") or ""
    elif isinstance(org, list):
        for item in org:
            if isinstance(item, dict) and item.get("name"):
                company = item.get("name")
                break
    description_html = job_posting.get("description") or ""
    return {
        "title": title.strip(),
        "company": company.strip(),
        "description": _strip_html(description_html).strip(),
    }


def parse_indeed_job(html: str):
    for payload in _extract_json_ld(html):
        job_posting = _find_job_posting(payload)
        if job_posting:
            return _normalize_job(job_posting)
    return None


def parse_indeed_html(html: str):
    extractor = _IndeedHTMLExtractor()
    extractor.feed(html)
    title = extractor.get_title()
    company = extractor.get_company()
    description = extractor.get_description()

    if not title or not company:
        meta = _MetaExtractor()
        meta.feed(html)
        if not title:
            title = _clean_text(
                meta.meta.get("og:title") or meta.meta.get("twitter:title") or ""
            )

    if not description:
        meta = _MetaExtractor()
        meta.feed(html)
        description = _clean_lines(
            meta.meta.get("og:description") or meta.meta.get("description") or ""
        )

    if title or company or description:
        return {
            "title": title.strip(),
            "company": company.strip(),
            "description": description.strip(),
        }
    return None


def scrape_job(url: str) -> dict:
    html = fetch_html(url)
    job = parse_indeed_job(html)
    if not job:
        job = parse_indeed_html(html)
    if not job:
        lower_html = html.lower()
        if "captcha" in lower_html or "verify you are a human" in lower_html:
            raise ValueError(
                "Blocked by Indeed. Save the page as HTML in your browser and pass the file path."
            )
        raise ValueError(
            "No job posting data found in the page. Try quoting the URL or save the page as HTML."
        )
    return job
