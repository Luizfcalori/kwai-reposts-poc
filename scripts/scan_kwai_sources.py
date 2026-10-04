#!/usr/bin/env python3
"""Discover authorized public Kwai videos and prepare a phone download queue.

For sources explicitly marked rights_confirmed=true, this scanner also resolves a
public MP4 URL when available and generates a lightweight Portuguese caption plus
hashtags. The Android helper remains responsible for user-reviewed/manual posting.
"""

from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "config" / "kwai_sources.json"
QUEUE_PATH = ROOT / "data" / "kwai_queue.json"
MAX_VIDEOS_PER_SOURCE = 30
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36"
)

HOOKS = [
    "Olha só essa! 👀",
    "Essa merece replay 😄",
    "Você esperava por isso? 👀",
    "Mais um vídeo para conferir até o final ✨",
    "Passando na sua timeline com essa cena 👇",
    "Esse momento chamou atenção por aqui 🔥",
]

DEFAULT_TAG_SETS = [
    ["#Kwai", "#ParaVoce", "#VideoDoDia"],
    ["#KwaiBrasil", "#PraVoce", "#Confira"],
    ["#Kwai", "#Fyp", "#EmAlta"],
    ["#Video", "#KwaiBrasil", "#ParaVoce"],
]

STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das", "e", "em", "no", "na",
    "nos", "nas", "por", "para", "com", "sem", "que", "se", "ao", "aos", "mais", "muito", "muita",
    "video", "vídeo", "kwai", "www", "https", "http", "com", "br", "oficial", "perfil", "veja", "ver",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def unique(seq: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for value in seq:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def normalize_video_url(handle: str, href: str) -> tuple[str, str] | None:
    href = href.replace("\\u002F", "/").replace("\\/", "/")
    patterns = [
        rf"(?:https?://(?:www\.)?kwai\.com)?/@{re.escape(handle)}/video/(\d+)",
        r"(?:https?://(?:www\.)?kwai\.com)?/@[^/\s\"']+/video/(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, href, flags=re.IGNORECASE)
        if match:
            video_id = match.group(1)
            return video_id, f"https://www.kwai.com/@{handle}/video/{video_id}"
    return None


def extract_from_html(handle: str, page_html: str) -> list[tuple[str, str]]:
    page_html = page_html.replace("\\u002F", "/").replace("\\/", "/")
    hrefs = re.findall(
        r"(?:https?://(?:www\.)?kwai\.com)?/@[^\"'<>\s]+/video/\d+",
        page_html,
        flags=re.IGNORECASE,
    )
    results = []
    for href in hrefs:
        parsed = normalize_video_url(handle, href)
        if parsed:
            results.append(parsed)
    deduped = []
    seen = set()
    for item in results:
        if item[0] not in seen:
            seen.add(item[0])
            deduped.append(item)
    return deduped[:MAX_VIDEOS_PER_SOURCE]


def discover_with_browser(profile_url: str, handle: str) -> list[tuple[str, str]]:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except Exception as exc:  # pragma: no cover
        print(f"selenium_unavailable handle={handle} error={exc}", file=sys.stderr)
        return []

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,1800")
    options.add_argument("--lang=pt-BR")
    options.add_argument(f"--user-agent={USER_AGENT}")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
        driver.get(profile_url)
        time.sleep(5)

        urls: list[tuple[str, str]] = []
        for _ in range(3):
            for anchor in driver.find_elements("css selector", 'a[href*="/video/"]'):
                href = anchor.get_attribute("href") or ""
                parsed = normalize_video_url(handle, href)
                if parsed:
                    urls.append(parsed)
            if len(unique([video_id for video_id, _ in urls])) >= MAX_VIDEOS_PER_SOURCE:
                break
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        if not urls:
            urls = extract_from_html(handle, driver.page_source)

        deduped = []
        seen = set()
        for item in urls:
            if item[0] not in seen:
                seen.add(item[0])
                deduped.append(item)
        return deduped[:MAX_VIDEOS_PER_SOURCE]
    except Exception as exc:
        print(f"browser_discovery_failed handle={handle} error={exc}", file=sys.stderr)
        return []
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def decode_page_text(value: str) -> str:
    value = value.replace("\\u002F", "/").replace("\\/", "/").replace("\\u0026", "&")
    value = html_lib.unescape(value)
    value = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), value)
    return value


def meta_content(page_html: str, names: list[str]) -> str:
    for name in names:
        patterns = [
            rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html, flags=re.IGNORECASE)
            if match:
                return decode_page_text(match.group(1)).strip()
    return ""


def extract_public_metadata_http(video_url: str) -> dict:
    try:
        request = Request(video_url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})
        with urlopen(request, timeout=35) as response:
            raw = response.read(5_000_000)
        page_html = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"video_http_metadata_failed url={video_url} error={exc}", file=sys.stderr)
        return {}

    normalized = decode_page_text(page_html)
    media_url = meta_content(page_html, ["og:video", "og:video:url", "twitter:player:stream"])
    if not media_url or ".mp4" not in media_url.lower():
        candidates = re.findall(r'https?://[^"\'<>\\\s]+?\.mp4(?:\?[^"\'<>\\\s]*)?', normalized, flags=re.IGNORECASE)
        if candidates:
            media_url = candidates[0]

    description = meta_content(page_html, ["og:description", "description", "twitter:description"])
    title = meta_content(page_html, ["og:title", "twitter:title"])
    if not title:
        match = re.search(r"<title[^>]*>(.*?)</title>", page_html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            title = decode_page_text(re.sub(r"<[^>]+>", " ", match.group(1))).strip()

    thumbnail = meta_content(page_html, ["og:image", "twitter:image"])
    return {
        "media_url": media_url if media_url.startswith("http") else "",
        "source_caption": description,
        "page_title": title,
        "thumbnail_url": thumbnail if thumbnail.startswith("http") else "",
    }


def normalize_hashtag_word(word: str) -> str:
    word = unicodedata.normalize("NFKD", word)
    word = "".join(ch for ch in word if not unicodedata.combining(ch))
    word = re.sub(r"[^A-Za-z0-9]", "", word)
    return word[:24]


def clean_source_caption(text: str, display_name: str) -> str:
    text = html_lib.unescape(text or "")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    boilerplate = [
        rf"^.*?Kwai.*?{re.escape(display_name)}.*?:\s*",
        r"^Kwai.*?:\s*",
    ]
    for pattern in boilerplate:
        candidate = re.sub(pattern, "", text, flags=re.IGNORECASE)
        if candidate != text and candidate.strip():
            text = candidate.strip()
            break
    return text[:280]


def generate_post_text(source: dict, video_id: str, source_caption: str) -> tuple[str, list[str], str]:
    display_name = str(source.get("display_name") or source.get("handle") or "")
    cleaned = clean_source_caption(source_caption, display_name)
    seed = int(hashlib.sha256(video_id.encode("utf-8")).hexdigest()[:8], 16)
    hook = HOOKS[seed % len(HOOKS)]

    existing_tags = re.findall(r"#[\wÀ-ÿ]+", cleaned)
    body = re.sub(r"#[\wÀ-ÿ]+", "", cleaned)
    body = re.sub(r"\s+", " ", body).strip(" -–—|:;,")
    if len(body) > 190:
        body = body[:187].rsplit(" ", 1)[0] + "..."
    if not body:
        body = "Confira esse vídeo até o final."

    keyword_tags: list[str] = []
    for token in re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", cleaned.lower()):
        if token in STOPWORDS:
            continue
        normalized = normalize_hashtag_word(token)
        if normalized and f"#{normalized}".lower() not in {tag.lower() for tag in keyword_tags}:
            keyword_tags.append(f"#{normalized}")
        if len(keyword_tags) >= 3:
            break

    tags: list[str] = []
    for tag in existing_tags[:3] + keyword_tags + DEFAULT_TAG_SETS[seed % len(DEFAULT_TAG_SETS)]:
        normalized_tag = "#" + normalize_hashtag_word(tag.lstrip("#"))
        if len(normalized_tag) > 1 and normalized_tag.lower() not in {value.lower() for value in tags}:
            tags.append(normalized_tag)
        if len(tags) >= 6:
            break

    generated_caption = f"{hook}\n{body}"
    post_text = generated_caption + ("\n\n" + " ".join(tags) if tags else "")
    return generated_caption, tags, post_text


def main() -> int:
    config = load_json(SOURCES_PATH, {"sources": []})
    queue = load_json(QUEUE_PATH, {"items": []})
    items = queue.setdefault("items", [])
    by_key = {(str(item.get("source_id")), str(item.get("video_id"))): item for item in items}

    total_found = 0
    total_added = 0
    total_enriched = 0
    changed = False
    source_summaries = []

    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue

        source_id = str(source["id"])
        handle = str(source["handle"]).lstrip("@")
        profile_url = source.get("profile_url") or f"https://www.kwai.com/@{handle}"
        rights_confirmed = bool(source.get("rights_confirmed", False))

        found = discover_with_browser(profile_url, handle)
        total_found += len(found)
        added_here = 0
        enriched_here = 0

        for video_id, video_url in found:
            key = (source_id, video_id)
            item = by_key.get(key)
            if item is None:
                item = {
                    "source_id": source_id,
                    "source_handle": handle,
                    "source_display_name": source.get("display_name", handle),
                    "video_id": video_id,
                    "video_url": video_url,
                    "discovered_at": utc_now(),
                }
                items.append(item)
                by_key[key] = item
                total_added += 1
                added_here += 1
                changed = True

            desired_rights = rights_confirmed
            if item.get("rights_confirmed") != desired_rights:
                item["rights_confirmed"] = desired_rights
                changed = True

            if not rights_confirmed:
                if item.get("status") != "awaiting_rights_confirmation":
                    item["status"] = "awaiting_rights_confirmation"
                    changed = True
                continue

            metadata = extract_public_metadata_http(video_url)
            media_url = metadata.get("media_url", "")
            source_caption = metadata.get("source_caption", "")
            generated_caption, hashtags, post_text = generate_post_text(source, video_id, source_caption)

            updates = {
                "video_url": video_url,
                "media_url": media_url,
                "media_refreshed_at": utc_now(),
                "source_caption": source_caption,
                "page_title": metadata.get("page_title", ""),
                "thumbnail_url": metadata.get("thumbnail_url", ""),
                "generated_caption": generated_caption,
                "hashtags": hashtags,
                "post_text": post_text,
                "status": "ready_for_phone" if media_url else "ready_for_media_refresh",
            }
            item_changed = False
            for field, value in updates.items():
                if item.get(field) != value:
                    item[field] = value
                    item_changed = True
            if item_changed:
                changed = True
                total_enriched += 1
                enriched_here += 1

        source_summaries.append(
            {
                "source_id": source_id,
                "handle": handle,
                "found": len(found),
                "added": added_here,
                "enriched": enriched_here,
                "rights_confirmed": rights_confirmed,
            }
        )

    if changed:
        QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "sources": source_summaries,
                "videos_found": total_found,
                "videos_added": total_added,
                "videos_enriched": total_enriched,
                "queue_size": len(items),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
