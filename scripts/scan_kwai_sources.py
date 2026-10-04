#!/usr/bin/env python3
"""Discover public Kwai video page URLs for configured source profiles.

This stage intentionally does NOT download media. It only records public video
page URLs/IDs and marks each item according to the source's rights_confirmed
flag. Media acquisition/publishing must remain disabled until reuse rights are
confirmed for that source.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "config" / "kwai_sources.json"
QUEUE_PATH = ROOT / "data" / "kwai_queue.json"
MAX_VIDEOS_PER_SOURCE = 30


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
    href = href.replace("\\/", "/")
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


def extract_from_html(handle: str, html: str) -> list[tuple[str, str]]:
    html = html.replace("\\u002F", "/").replace("\\/", "/")
    hrefs = re.findall(r"(?:https?://(?:www\.)?kwai\.com)?/@[^\"'<>\s]+/video/\d+", html, flags=re.IGNORECASE)
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
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )

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


def main() -> int:
    config = load_json(SOURCES_PATH, {"sources": []})
    queue = load_json(QUEUE_PATH, {"items": []})
    items = queue.setdefault("items", [])
    existing = {(str(item.get("source_id")), str(item.get("video_id"))) for item in items}

    total_found = 0
    total_added = 0
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

        for video_id, video_url in found:
            key = (source_id, video_id)
            if key in existing:
                continue

            items.append(
                {
                    "source_id": source_id,
                    "source_handle": handle,
                    "source_display_name": source.get("display_name", handle),
                    "video_id": video_id,
                    "video_url": video_url,
                    "discovered_at": utc_now(),
                    "rights_confirmed": rights_confirmed,
                    "status": "ready_for_media" if rights_confirmed else "awaiting_rights_confirmation",
                }
            )
            existing.add(key)
            total_added += 1
            added_here += 1

        source_summaries.append(
            {
                "source_id": source_id,
                "handle": handle,
                "found": len(found),
                "added": added_here,
                "rights_confirmed": rights_confirmed,
            }
        )

    if total_added:
        QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "sources": source_summaries,
                "videos_found": total_found,
                "videos_added": total_added,
                "queue_size": len(items),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
