
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SOURCES = [
    {
        "name": "ReoNa 官方網站",
        "url": "https://www.reona-reona.com/",
        "domain": "reona-reona.com",
    },
    {
        "name": "Sony Music 官方",
        "url": "https://www.sonymusic.co.jp/artist/ReoNa/",
        "domain": "sonymusic.co.jp",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ReoNaEventTracker/1.0)"
}

DATE_PATTERN = re.compile(
    r"20\d{2}[./年-]\d{1,2}[./月-]\d{1,2}日?"
)


def fetch_announcements(source):
    response = requests.get(
        source["url"],
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for link in soup.find_all("a", href=True):
        title = " ".join(link.get_text(" ", strip=True).split())
        if not title or len(title) < 4:
            continue

        url = urljoin(source["url"], link["href"])

        if source["domain"] not in url:
            continue

        parent = link.parent
        context = " ".join(
            parent.get_text(" ", strip=True).split()
        ) if parent else title

        if not DATE_PATTERN.search(context):
            continue

        results.append({
            "title": title,
            "url": url,
            "source": source["name"],
            "publicationDate": (
                DATE_PATTERN.search(context).group(0)
            ),
            "checkedAt": datetime.now(
                timezone.utc
            ).isoformat(),
        })

    return results


def main():
    all_results = []
    errors = []

    for source in SOURCES:
        try:
            items = fetch_announcements(source)
            print(
                f'{source["name"]}: '
                f'找到 {len(items)} 筆公告候選'
            )
            all_results.extend(items)
        except Exception as error:
            message = f'{source["name"]}: {error}'
            errors.append(message)
            print(f"ERROR: {message}")

    if not all_results and errors:
        raise RuntimeError(
            "所有官方來源都無法取得，停止更新。"
        )

    unique = {}
    for item in all_results:
        unique[item["url"]] = item

    output = {
        "checkedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "sourcesChecked": len(SOURCES),
        "announcements": list(unique.values()),
        "errors": errors,
        "note": "公告候選清單，尚未確認為實際活動。",
    }

    path = Path("site/discovered.json")
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"完成：共整理 {len(unique)} 筆公告候選。"
    )


if __name__ == "__main__":
    main()
