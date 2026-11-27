
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

SOURCES = [
    {
        "name": "ReoNa 官方網站",
        "pages": [
            "https://www.reona-reona.com/",
            "https://www.reona-reona.com/news/",
            "https://www.reona-reona.com/live/",
        ],
        "domain": "www.reona-reona.com",
    },
    {
        "name": "Sony Music",
        "pages": [
            "https://www.sonymusic.co.jp/artist/ReoNa/",
            "https://www.sonymusic.co.jp/artist/ReoNa/info/",
            "https://www.sonymusic.co.jp/artist/ReoNa/live/",
        ],
        "domain": "www.sonymusic.co.jp",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 ReoNaEventTracker/2.0"
}

DATE_PATTERN = re.compile(
    r"20\d{2}[./年-]\d{1,2}[./月-]\d{1,2}日?"
)

KEYWORDS = [
    "ReoNa", "ライブ", "公演", "イベント",
    "チケット", "リリース", "発売",
    "グッズ", "配信", "出演", "開催",
    "受付", "振替", "中止", "延期",
]

def fetch_page(url):
    response = requests.get(
        url, headers=HEADERS, timeout=30
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def scan_source(source):
    results = []
    errors = []

    for page_url in source["pages"]:
        try:
            soup = fetch_page(page_url)

            for link in soup.find_all("a", href=True):
                title = " ".join(
                    link.get_text(" ", strip=True).split()
                )

                if not title:
                    image = link.find("img")
                    if image:
                        title = image.get("alt", "").strip()

                if len(title) < 4:
                    continue

                url = urljoin(page_url, link["href"])
                parsed = urlparse(url)

                if parsed.netloc != source["domain"]:
                    continue

                context = title
                parent = link

                for _ in range(4):
                    if parent.parent:
                        parent = parent.parent
                        context += " " + parent.get_text(
                            " ", strip=True
                        )

                context = " ".join(context.split())

                has_keyword = any(
                    word.lower() in context.lower()
                    for word in KEYWORDS
                )

                has_date = bool(
                    DATE_PATTERN.search(context)
                )

                is_detail = (
                    "/info/" in parsed.path
                    or "/news/" in parsed.path
                    or "/live/" in parsed.path
                )

                if not (
                    has_keyword
                    and (has_date or is_detail)
                ):
                    continue

                date_match = DATE_PATTERN.search(context)

                results.append({
                    "title": title,
                    "url": url,
                    "source": source["name"],
                    "publicationDate": (
                        date_match.group(0)
                        if date_match else None
                    ),
                })

        except Exception as error:
            errors.append(
                f"{page_url}: {error}"
            )

    return results, errors


def main():
    all_results = []
    errors = []

    for source in SOURCES:
        results, source_errors = scan_source(source)

        print(
            f'{source["name"]}: '
            f'找到 {len(results)} 筆公告候選'
        )

        all_results.extend(results)
        errors.extend(source_errors)

    unique = {}

    for item in all_results:
        unique[item["url"]] = item

    output = {
        "checkedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "announcements": list(unique.values()),
        "errors": errors,
        "note": "公告候選清單，尚未人工確認。",
    }

    Path("site").mkdir(exist_ok=True)

    Path("site/discovered.json").write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8",
    )

    print(
        f"完成：共整理 {len(unique)} 筆公告候選。"
    )

    if errors:
        print(f"另有 {len(errors)} 個頁面讀取錯誤。")


if __name__ == "__main__":
    main()
