"""课题组网站成果附件管理器。

仅监听本机 127.0.0.1。上传 PDF 后提取可识别的元数据，
经人工确认后保存 PDF，并把成果记录写入 data/achievements.json。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import shutil
import threading
import uuid
import webbrowser
from datetime import datetime
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

try:
    from pypdf import PdfReader
except ImportError as exc:
    raise SystemExit(
        "缺少 pypdf。请在 PyCharm 当前解释器中安装 pypdf，"
        "或使用“启动成果管理器.bat”启动。"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "achievements.json"
PDF_ROOT = ROOT / "files" / "achievements"
INCOMING_ROOT = ROOT / "incoming-achievements"
PUBLICATIONS_FILE = ROOT / "publications.html"
ACHIEVEMENT_END_MARKER = (
    "<!-- ===== 成果条目：编辑到这里结束 ===== -->"
)
MAX_UPLOAD_BYTES = 80 * 1024 * 1024
VALID_TYPES = {
    "project",
    "paper",
    "intellectual-property",
    "award",
}
TYPE_LABELS = {
    "project": "科研与教改项目",
    "paper": "学术论文",
    "intellectual-property": "专利与软件著作权",
    "award": "竞赛与科研奖励",
}
DOI_PATTERN = re.compile(
    r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+",
    flags=re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")


def ensure_storage() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    PDF_ROOT.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]\n", encoding="utf-8")


def load_achievements() -> list[dict[str, Any]]:
    ensure_storage()
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError("data/achievements.json 无法读取或格式不正确") from exc
    if not isinstance(data, list):
        raise ValueError("data/achievements.json 顶层必须是数组")
    return data


def save_achievements(records: list[dict[str, Any]]) -> None:
    ensure_storage()
    temporary = DATA_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(DATA_FILE)


def achievement_html(record: dict[str, Any]) -> str:
    """把一个成果记录生成可直接编辑的静态 HTML。"""
    indent = " " * 20
    inner = indent + " " * 4
    detail = inner + " " * 4
    value_indent = detail + " " * 4

    record_id = html.escape(str(record["id"]), quote=True)
    year = html.escape(str(record["year"]), quote=True)
    achievement_type = html.escape(str(record["type"]), quote=True)
    type_label = html.escape(
        TYPE_LABELS.get(str(record["type"]), "其他成果")
    )
    title = html.escape(str(record["title"]))

    lines = [
        (
            f'{indent}<article class="achievement-record" '
            f'data-achievement-record data-achievement-id="{record_id}" '
            f'data-year="{year}" data-type="{achievement_type}">'
        ),
        f'{inner}<div class="record-meta">',
        f'{detail}<span class="record-year">{year}</span>',
        f'{detail}<span class="record-type">{type_label}</span>',
        f"{inner}</div>",
        f'{inner}<div class="record-content">',
        f"{detail}<h3>{title}</h3>",
    ]

    author_line = str(record.get("authorLine", "")).strip()
    if author_line:
        lines.append(
            f'{detail}<p class="record-author-line">'
            f"{html.escape(author_line)}</p>"
        )

    bibliography: list[tuple[str, str, str]] = []
    for label, key in (
        ("作者", "authors"),
        ("期刊", "journal"),
        ("卷期页码", "citation"),
    ):
        value = str(record.get(key, "")).strip()
        if value:
            bibliography.append((label, value, ""))

    doi = str(record.get("doi", "")).strip()
    if doi:
        doi_href = (
            doi
            if doi.startswith(("http://", "https://"))
            else f"https://doi.org/{doi}"
        )
        bibliography.append(("DOI", doi, doi_href))

    if bibliography:
        lines.append(f'{detail}<div class="record-bibliography">')
        for label, value, href in bibliography:
            item_class = (
                "bibliography-item doi-item"
                if label == "DOI"
                else "bibliography-item"
            )
            lines.extend(
                [
                    f'{value_indent}<div class="{item_class}">',
                    (
                        f'{value_indent}    <span '
                        f'class="bibliography-label">'
                        f"{html.escape(label)}</span>"
                    ),
                    (
                        f'{value_indent}    <span '
                        f'class="bibliography-value">'
                    ),
                ]
            )
            if href:
                lines.append(
                    f'{value_indent}        <a '
                    f'class="bibliography-link" '
                    f'href="{html.escape(href, quote=True)}" '
                    f'target="_blank" rel="noopener noreferrer">'
                    f"{html.escape(value)}</a>"
                )
            else:
                lines.append(
                    f"{value_indent}        {html.escape(value)}"
                )
            lines.extend(
                [
                    f"{value_indent}    </span>",
                    f"{value_indent}</div>",
                ]
            )
        lines.append(f"{detail}</div>")

    pdf_path = str(record.get("pdf", "")).strip()
    if pdf_path:
        escaped_pdf = html.escape(pdf_path, quote=True)
        download_name = html.escape(
            str(record.get("originalFilename", "achievement.pdf")),
            quote=True,
        )
        lines.extend(
            [
                f'{detail}<div class="record-actions">',
                (
                    f'{value_indent}<a class="record-file-button '
                    f'record-file-button-primary" href="{escaped_pdf}" '
                    f'target="_blank" rel="noopener noreferrer">'
                    "在线浏览 PDF</a>"
                ),
                (
                    f'{value_indent}<a class="record-file-button '
                    f'record-file-button-secondary" href="{escaped_pdf}" '
                    f'download="{download_name}">下载 PDF</a>'
                ),
                f"{detail}</div>",
            ]
        )

    lines.extend(
        [
            f"{inner}</div>",
            f"{indent}</article>",
        ]
    )
    return "\n".join(lines)


def insert_achievement_into_publications(
    record: dict[str, Any],
) -> None:
    """在成果编辑区末尾插入真实 HTML 代码。"""
    if not PUBLICATIONS_FILE.exists():
        raise ValueError("找不到 publications.html")

    source = PUBLICATIONS_FILE.read_text(encoding="utf-8")
    record_id = html.escape(str(record["id"]), quote=True)
    if f'data-achievement-id="{record_id}"' in source:
        return
    if ACHIEVEMENT_END_MARKER not in source:
        raise ValueError("publications.html 中缺少成果结束标记")

    block = achievement_html(record)
    marker_line = f"{' ' * 20}{ACHIEVEMENT_END_MARKER}"
    if marker_line in source:
        updated = source.replace(
            marker_line,
            f"{block}\n\n{marker_line}",
            1,
        )
    else:
        updated = source.replace(
            ACHIEVEMENT_END_MARKER,
            f"{block}\n\n{ACHIEVEMENT_END_MARKER}",
            1,
        )
    temporary = PUBLICATIONS_FILE.with_suffix(".html.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(PUBLICATIONS_FILE)


def normalize_metadata(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def useful_metadata(value: str) -> bool:
    lowered = value.lower()
    rejected = {
        "untitled",
        "microsoft word",
        "wps office",
        "document",
        "anonymous",
    }
    return bool(value) and not any(item in lowered for item in rejected)


def clean_pdf_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if re.fullmatch(r"\d{1,4}", line):
            continue
        lines.append(line)
    return lines


def title_from_lines(lines: list[str]) -> tuple[str, int]:
    skip_words = (
        "doi:",
        "http://",
        "https://",
        "abstract",
        "摘要",
        "关键词",
        "keywords",
        "received",
        "accepted",
        "copyright",
        "issn",
    )
    for index, line in enumerate(lines[:50]):
        lowered = line.lower()
        if any(word in lowered for word in skip_words):
            continue
        if not 8 <= len(line) <= 320:
            continue
        if len(re.findall(r"\d", line)) > len(line) * 0.45:
            continue
        return line, index
    return "", -1


def title_end_index(
    lines: list[str],
    title: str,
    fallback_index: int,
) -> int:
    """定位多行题目的末行，避免把题目续行误判成作者。"""
    compact_title = re.sub(r"[^0-9a-z\u3400-\u9fff]", "", title.lower())
    if not compact_title:
        return fallback_index

    for start in range(min(30, len(lines))):
        combined = ""
        for end in range(start, min(start + 6, len(lines))):
            combined += re.sub(
                r"[^0-9a-z\u3400-\u9fff]",
                "",
                lines[end].lower(),
            )
            if compact_title in combined:
                return end
            if (
                len(combined) >= max(12, int(len(compact_title) * 0.82))
                and combined in compact_title
            ):
                continue
            if len(combined) > len(compact_title) * 1.35:
                break
    return fallback_index


def author_names_from_lines(
    lines: list[str],
    title_index: int,
) -> list[str]:
    """逐行提取题目之后、单位或摘要之前的全部作者。"""
    if title_index < 0:
        return []

    stop_words = (
        "abstract",
        "摘要",
        "keyword",
        "关键词",
        "doi",
        "orcid",
        "corresponding author",
        "e-mail",
        "email",
        "department",
        "school of",
        "institute",
        "university",
        "大学",
        "学院",
        "研究院",
        "交通运输部",
        "key laboratory",
        "laboratory",
        "journal",
        "volume",
        "received",
        "accepted",
        "available online",
    )

    author_names: list[str] = []
    seen: set[str] = set()
    for line in lines[title_index + 1 : title_index + 30]:
        lowered = line.lower()

        # Elsevier 等 PDF 常把 a、b、c、星号和逗号单独拆成一行。
        if re.fullmatch(
            r"[\s,;:*†‡§#]*[a-z]?[\s,;:*†‡§#]*",
            line,
        ):
            continue

        if any(word in lowered for word in stop_words):
            if author_names:
                break
            continue
        if YEAR_PATTERN.search(line) or DOI_PATTERN.search(line):
            if author_names:
                break
            continue
        if not 2 <= len(line) <= 500:
            continue

        candidate = re.sub(r"^[\s,;:]+", "", line).strip()

        # 作者区通常由逗号、分号、and 或若干短姓名组成。
        has_separator = bool(
            re.search(
                r"[,;，；]|\s(?:and|&)\s",
                candidate,
                re.IGNORECASE,
            )
        )
        word_count = len(candidate.split())
        if not has_separator and word_count > 8:
            if author_names:
                break
            continue

        for name in parse_author_names(candidate):
            key = re.sub(r"[\W_]", "", name).lower()
            if key and key not in seen:
                seen.add(key)
                author_names.append(name)

    return author_names


def clean_author_name(name: str) -> str:
    name = normalize_metadata(name)
    name = re.sub(r"^[,;:\s]+|[,;:\s]+$", "", name)
    name = re.sub(r"^(?:dr|prof|professor)\.?\s+", "", name, flags=re.I)
    name = re.sub(r"\s*[\*†‡§#]+$", "", name)
    name = re.sub(r"\s*[¹²³⁴⁵⁶⁷⁸⁹⁰ᵃᵇᶜ]+$", "", name)
    name = re.sub(r"\s+(?:\d+(?:\s*,\s*\d+)*|[a-z])$", "", name)
    return name.strip()


def format_author_name(name: str) -> str:
    """把英文姓名统一为 Last, First；中文姓名保持原顺序。"""
    name = clean_author_name(name)
    if not name:
        return ""

    if re.search(r"[\u3400-\u9fff]", name) and not re.search(
        r"[A-Za-z]",
        name,
    ):
        return name.replace(",", "").strip()

    if "," in name:
        last_name, given_name = name.split(",", 1)
        last_name = clean_author_name(last_name)
        given_name = clean_author_name(given_name)
        if last_name and given_name:
            return f"{last_name}, {given_name}"
        return last_name or given_name

    tokens = name.split()
    if len(tokens) == 1:
        return tokens[0]

    last_name = tokens[-1]
    given_name = " ".join(tokens[:-1])
    return f"{last_name}, {given_name}"


def parse_author_names(raw_authors: str) -> list[str]:
    """拆分作者并去重，输出统一的分号分隔姓名列表。"""
    raw_authors = normalize_metadata(raw_authors)
    if not raw_authors:
        return []

    raw_authors = raw_authors.replace("；", ";").replace("，", ",")
    raw_authors = re.sub(
        r"\s+(?:and|&)\s+",
        ";",
        raw_authors,
        flags=re.IGNORECASE,
    )
    raw_authors = re.sub(r"\bet\s+al\.?", "", raw_authors, flags=re.I)

    if ";" in raw_authors:
        candidates = raw_authors.split(";")
    else:
        comma_parts = [
            part.strip()
            for part in raw_authors.split(",")
            if part.strip()
        ]
        if (
            len(comma_parts) >= 2
            and len(comma_parts) % 2 == 0
            and all(len(part.split()) == 1 for part in comma_parts)
        ):
            candidates = [
                f"{comma_parts[index]}, {comma_parts[index + 1]}"
                for index in range(0, len(comma_parts), 2)
            ]
        elif len(comma_parts) > 1:
            candidates = comma_parts
        else:
            candidates = [raw_authors]

    formatted: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        name = format_author_name(candidate)
        if not name:
            continue
        key = re.sub(r"[\W_]", "", name).lower()
        if key and key not in seen:
            seen.add(key)
            formatted.append(name)
    return formatted


def analyze_pdf(pdf_bytes: bytes, filename: str) -> dict[str, Any]:
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("所选文件不是有效的 PDF")

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        raise ValueError("PDF 无法解析，文件可能损坏或已加密") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ValueError("暂不支持有密码的 PDF") from exc

    metadata = reader.metadata or {}
    page_text: list[str] = []
    for page in reader.pages[: min(3, len(reader.pages))]:
        try:
            page_text.append(page.extract_text() or "")
        except Exception:
            page_text.append("")

    text = "\n".join(page_text)
    lines = clean_pdf_lines(text)

    metadata_title = normalize_metadata(metadata.get("/Title"))
    metadata_author = normalize_metadata(metadata.get("/Author"))
    metadata_subject = normalize_metadata(metadata.get("/Subject"))

    detected_title, detected_title_index = title_from_lines(lines)
    title = (
        metadata_title
        if useful_metadata(metadata_title)
        else detected_title
    )
    if not title:
        title = Path(filename).stem

    title_index = title_end_index(
        lines,
        title,
        detected_title_index,
    )
    body_authors = author_names_from_lines(lines, title_index)
    metadata_authors = (
        parse_author_names(metadata_author)
        if useful_metadata(metadata_author)
        else []
    )

    # PDF 元数据常常只有第一作者；正文识别到更多作者时优先采用正文。
    author_names = (
        body_authors
        if len(body_authors) > len(metadata_authors)
        else metadata_authors
    )
    authors = "; ".join(author_names)
    main_authors = "; ".join(author_names[:3])

    journal = (
        metadata_subject
        if useful_metadata(metadata_subject)
        else ""
    )

    doi_match = DOI_PATTERN.search(text)
    doi = ""
    if doi_match:
        doi = doi_match.group(0).rstrip(".,;:)]}")

    current_year = datetime.now().year
    years = [
        int(year)
        for year in YEAR_PATTERN.findall(text)
        if 1900 <= int(year) <= current_year + 2
    ]
    year = str(years[0] if years else current_year)

    preview = "\n".join(lines[:24])
    return {
        "type": "paper",
        "year": year,
        "title": title,
        "authors": authors,
        "authorLine": main_authors,
        "journal": journal,
        "citation": "",
        "doi": doi,
        "pages": len(reader.pages),
        "originalFilename": filename,
        "textPreview": preview,
        "_detectedTitle": bool(
            useful_metadata(metadata_title) or detected_title
        ),
        "_detectedAuthors": bool(author_names),
        "_detectedYear": bool(years),
    }


def clean_crossref_text(value: Any) -> str:
    """把 Crossref 字段整理成可直接显示的纯文本。"""
    if isinstance(value, list):
        value = value[0] if value else ""
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def crossref_metadata(doi: str) -> dict[str, str]:
    """按 DOI 获取出版商提交到 Crossref 的标准书目信息。"""
    if not doi:
        return {}

    request = Request(
        f"https://api.crossref.org/works/{quote(doi, safe='')}",
        headers={
            "Accept": "application/json",
            "User-Agent": "CHD-research-site-achievement-uploader/1.0",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Crossref 元数据读取失败，将使用 PDF 识别结果：{exc}")
        return {}

    message = payload.get("message", {})
    if not isinstance(message, dict):
        return {}

    author_names: list[str] = []
    for author in message.get("author", []):
        if not isinstance(author, dict):
            continue
        family = clean_crossref_text(author.get("family"))
        given = clean_crossref_text(author.get("given"))
        name = clean_crossref_text(author.get("name"))
        formatted = (
            f"{family}, {given}" if family and given else family or given or name
        )
        if formatted:
            author_names.append(formatted)

    year = ""
    for date_key in ("published-print", "published-online", "issued"):
        date_parts = message.get(date_key, {}).get("date-parts", [])
        if date_parts and date_parts[0]:
            candidate = str(date_parts[0][0])
            if re.fullmatch(r"(?:19|20)\d{2}", candidate):
                year = candidate
                break

    volume = clean_crossref_text(message.get("volume"))
    issue = clean_crossref_text(message.get("issue"))
    page = clean_crossref_text(
        message.get("page") or message.get("article-number")
    )
    volume_issue = volume
    if issue:
        volume_issue = f"{volume}({issue})" if volume else f"({issue})"
    citation_parts = [part for part in (volume_issue, f"({year})" if year else "", page) if part]

    return {
        "title": clean_crossref_text(message.get("title")),
        "authors": "; ".join(author_names),
        "authorLine": "; ".join(author_names[:3]),
        "journal": clean_crossref_text(message.get("container-title")),
        "citation": " ".join(citation_parts),
        "year": year,
        "doi": clean_crossref_text(message.get("DOI")) or doi,
    }


def load_sidecar(pdf_path: Path) -> dict[str, str]:
    """读取与 PDF 同名的可选 JSON 覆盖文件。"""
    sidecar_path = pdf_path.with_suffix(".json")
    if not sidecar_path.exists():
        return {}
    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{sidecar_path.name} 无法读取或 JSON 格式错误") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{sidecar_path.name} 顶层必须是 JSON 对象")
    allowed = {
        "type",
        "year",
        "title",
        "authorLine",
        "authors",
        "journal",
        "citation",
        "doi",
    }
    return {
        key: str(value).strip()
        for key, value in payload.items()
        if key in allowed and value is not None
    }


def existing_pdf_hashes(records: list[dict[str, Any]]) -> set[str]:
    """计算已发布附件哈希，防止重复上传同一篇 PDF。"""
    hashes = {
        str(record.get("sourceSha256", "")).lower()
        for record in records
        if record.get("sourceSha256")
    }
    for record in records:
        pdf_relative = str(record.get("pdf", "")).strip()
        if not pdf_relative:
            continue
        pdf_path = ROOT / Path(pdf_relative)
        if pdf_path.is_file():
            hashes.add(hashlib.sha256(pdf_path.read_bytes()).hexdigest())
    return hashes


def write_action_summary(lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.write("## 成果 PDF 自动处理\n\n")
        summary.write("\n".join(f"- {line}" for line in lines) + "\n")


def process_incoming_achievements() -> int:
    """处理 GitHub 网页上传目录中的 PDF，并生成公开成果记录。"""
    ensure_storage()
    INCOMING_ROOT.mkdir(parents=True, exist_ok=True)
    pdf_paths = sorted(
        path for path in INCOMING_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    if not pdf_paths:
        print("incoming-achievements 中没有待处理 PDF。")
        write_action_summary(["没有发现待处理 PDF。"])
        return 0

    records = load_achievements()
    known_hashes = existing_pdf_hashes(records)
    processed: list[str] = []

    for pdf_path in pdf_paths:
        pdf_bytes = pdf_path.read_bytes()
        digest = hashlib.sha256(pdf_bytes).hexdigest()
        sidecar_path = pdf_path.with_suffix(".json")
        if digest in known_hashes:
            pdf_path.unlink()
            sidecar_path.unlink(missing_ok=True)
            processed.append(f"跳过重复文件：{pdf_path.name}")
            continue

        detected = analyze_pdf(pdf_bytes, pdf_path.name)
        crossref = crossref_metadata(str(detected.get("doi", "")))
        sidecar = load_sidecar(pdf_path)
        merged = {
            key: str(value).strip()
            for key, value in detected.items()
            if not key.startswith("_") and isinstance(value, (str, int))
        }
        merged.update({key: value for key, value in crossref.items() if value})
        merged.update({key: value for key, value in sidecar.items() if value})

        achievement_type = merged.get("type", "paper")
        year = merged.get("year", "")
        title = merged.get("title", "")
        authors = merged.get("authors", "")
        if achievement_type not in VALID_TYPES:
            raise ValueError(f"{pdf_path.name}：成果类型不正确")
        if not re.fullmatch(r"(?:19|20)\d{2}", year):
            raise ValueError(f"{pdf_path.name}：未可靠识别四位成果年份")
        if not title or (
            title == pdf_path.stem
            and not detected.get("_detectedTitle")
            and not sidecar.get("title")
        ):
            raise ValueError(f"{pdf_path.name}：未可靠识别成果题目")
        if achievement_type == "paper" and not authors:
            raise ValueError(
                f"{pdf_path.name}：未可靠识别作者；请上传同名 JSON 覆盖文件"
            )

        author_line = merged.get("authorLine", "")
        if authors and not author_line:
            author_line = "; ".join(
                part.strip() for part in authors.split(";")[:3] if part.strip()
            )

        record_id = f"{year}-{digest[:12]}"
        year_folder = PDF_ROOT / year
        year_folder.mkdir(parents=True, exist_ok=True)
        stored_filename = f"{record_id}.pdf"
        destination = year_folder / stored_filename
        shutil.move(str(pdf_path), str(destination))
        sidecar_path.unlink(missing_ok=True)

        doi = re.sub(
            r"^https?://(?:dx\.)?doi\.org/",
            "",
            merged.get("doi", ""),
            flags=re.IGNORECASE,
        )
        record = {
            "id": record_id,
            "type": achievement_type,
            "year": year,
            "title": title,
            "authorLine": author_line,
            "authors": authors,
            "journal": merged.get("journal", ""),
            "citation": merged.get("citation", ""),
            "doi": doi,
            "pdf": f"files/achievements/{year}/{stored_filename}",
            "originalFilename": pdf_path.name,
            "addedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "sourceSha256": digest,
        }
        records.append(record)
        known_hashes.add(digest)
        processed.append(f"已发布：{title}")

    save_achievements(records)
    write_action_summary(processed)
    for message in processed:
        print(message)
    return len(processed)


def parse_multipart(
    handler: SimpleHTTPRequestHandler,
) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    content_type = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        raise ValueError("请求格式必须是 multipart/form-data")

    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("无效的上传大小") from exc
    if length <= 0 or length > MAX_UPLOAD_BYTES:
        raise ValueError("PDF 大小必须在 80MB 以内")

    body = handler.rfile.read(length)
    envelope = (
        f"Content-Type: {content_type}\r\n"
        "MIME-Version: 1.0\r\n\r\n"
    ).encode("utf-8") + body
    message = BytesParser(policy=policy.default).parsebytes(envelope)

    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename:
            files[name] = (Path(filename).name, payload)
        else:
            charset = part.get_content_charset() or "utf-8"
            fields[name] = payload.decode(charset, errors="replace").strip()
    return fields, files


def open_manager_page(url: str) -> None:
    """使用系统默认浏览器打开管理器，兼容直接从 PyCharm 运行。"""
    try:
        if os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
            return
        if webbrowser.open_new_tab(url):
            return
    except OSError as exc:
        print(f"浏览器未能自动打开：{exc}")

    print(f"请手动在浏览器中打开：{url}")


class AchievementRequestHandler(SimpleHTTPRequestHandler):
    server_version = "AchievementManager/1.0"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")

    def send_json(
        self,
        payload: dict[str, Any] | list[dict[str, Any]],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def send_api_error(
        self,
        message: str,
        status: HTTPStatus = HTTPStatus.BAD_REQUEST,
    ) -> None:
        self.send_json({"ok": False, "message": message}, status)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/achievements":
            try:
                self.send_json({"ok": True, "records": load_achievements()})
            except ValueError as exc:
                self.send_api_error(
                    str(exc),
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            fields, files = parse_multipart(self)
            file_item = files.get("file")
            if not file_item:
                raise ValueError("请选择 PDF 文件")
            filename, pdf_bytes = file_item

            if path == "/api/analyze":
                result = analyze_pdf(pdf_bytes, filename)
                self.send_json({"ok": True, "result": result})
                return

            if path == "/api/achievements":
                self.save_new_achievement(fields, filename, pdf_bytes)
                return

            self.send_api_error("接口不存在", HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_api_error(str(exc))
        except Exception as exc:
            print(f"未处理错误：{exc!r}")
            self.send_api_error(
                "处理失败，请检查终端中的错误信息",
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def save_new_achievement(
        self,
        fields: dict[str, str],
        original_filename: str,
        pdf_bytes: bytes,
    ) -> None:
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("所选文件不是有效的 PDF")

        achievement_type = fields.get("type", "paper")
        if achievement_type not in VALID_TYPES:
            raise ValueError("成果类型不正确")

        year = fields.get("year", "").strip()
        if not re.fullmatch(r"(?:19|20)\d{2}", year):
            raise ValueError("请输入四位成果年份")

        title = fields.get("title", "").strip()
        if not title:
            raise ValueError("成果题目不能为空")

        record_id = (
            datetime.now().strftime("%Y%m%d%H%M%S")
            + "-"
            + uuid.uuid4().hex[:8]
        )
        year_folder = PDF_ROOT / year
        year_folder.mkdir(parents=True, exist_ok=True)
        stored_filename = f"{record_id}.pdf"
        pdf_path = year_folder / stored_filename
        pdf_path.write_bytes(pdf_bytes)

        doi = fields.get("doi", "").strip()
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)

        record = {
            "id": record_id,
            "type": achievement_type,
            "year": year,
            "title": title,
            "authorLine": fields.get("authorLine", "").strip(),
            "authors": fields.get("authors", "").strip(),
            "journal": fields.get("journal", "").strip(),
            "citation": fields.get("citation", "").strip(),
            "doi": doi,
            "pdf": (
                f"files/achievements/{year}/{stored_filename}"
            ),
            "originalFilename": Path(original_filename).name,
            "addedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        }

        original_records: list[dict[str, Any]] = []
        records_loaded = False
        try:
            original_records = load_achievements()
            records_loaded = True
            updated_records = [*original_records, record]
            save_achievements(updated_records)
            insert_achievement_into_publications(record)
        except Exception:
            pdf_path.unlink(missing_ok=True)
            if records_loaded:
                save_achievements(original_records)
            raise

        self.send_json(
            {
                "ok": True,
                "message": "成果及 PDF 已保存",
                "record": record,
            },
            HTTPStatus.CREATED,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="启动成果附件管理器")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--process-incoming",
        action="store_true",
        help="处理 incoming-achievements 中由 GitHub 上传的 PDF",
    )
    args = parser.parse_args()

    if args.process_incoming:
        process_incoming_achievements()
        return

    ensure_storage()
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        AchievementRequestHandler,
    )
    manager_url = (
        f"http://127.0.0.1:{args.port}/achievement-manager.html"
    )
    print("成果附件管理器已启动：")
    print(manager_url)
    print("完成后在此窗口按 Ctrl+C 关闭。")

    if not args.no_browser:
        threading.Timer(
            0.6,
            open_manager_page,
            args=(manager_url,),
        ).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n成果附件管理器已关闭。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
