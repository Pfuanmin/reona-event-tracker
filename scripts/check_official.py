
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

from playwright.sync_api import sync_playwright

SOURCES = [
    {
        "name": "ReoNa 官方網站",
        "pages": [
            "https://www.reona-reona.com/",
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

SONY_ARTICLE_PATTERN = re.compile(
    r"^/artist/ReoNa/(?:info|live)/\d+/?$"
)

DATE_PATTERN = re.compile(
    r"20\d{2}[./年-]\d{1,2}[./月-]\d{1,2}日?"
)


def main():
    all_results = []
    errors = []
    checked_at = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for source in SOURCES:
            source_results = []

            for page_url in source["pages"]:
                try:
                    page = browser.new_page(
                        user_agent=(
                            "Mozilla/5.0 "
                            "ReoNaEventTracker/4.0"
                        )
                    )

                    print(f"\n正在開啟：{page_url}")

                    page.goto(
                        page_url,
                        wait_until="domcontentloaded",
                        timeout=60000
                    )

                    page.wait_for_timeout(5000)

                    frames = page.frames

                    print(
                        f"檢查頁面及 iframe：{len(frames)} 個"
                    )

                    for frame in frames:
                        try:
                            links = frame.locator(
                                "a[href]"
                            ).evaluate_all(
                                """els => els.map(a => ({
                                    title: (
                                        a.innerText ||
                                        a.getAttribute("aria-label") ||
                                        a.querySelector("img")?.alt ||
                                        ""
                                    ).trim(),
                                    href: a.href,
                                    context: (
                                        a.parentElement?.innerText ||
                                        a.innerText ||
                                        ""
                                    ).trim()
                                }))"""
                            )

                            print(
                                f"Frame：{frame.url}"
                            )
                            print(
                                f"找到連結：{len(links)} 筆"
                            )

                            for link in links:
                                url = urljoin(
                                    frame.url or page_url,
                                    link["href"]
                                )
                                url, _ = urldefrag(url)

                                parsed = urlparse(url)

                                if (
                                    parsed.netloc
                                    != source["domain"]
                                ):
                                    continue

                                title = (
                                    link["title"]
                                    or link["context"][:80]
                                    or "未命名公告"
                                )

                                if source["name"] == "Sony Music":
                                    is_article = bool(
                                        SONY_ARTICLE_PATTERN.fullmatch(
                                            parsed.path
                                        )
                                    )
                                else:
                                    # 官方網站文章網址格式尚待確認，
                                    # 暫時不收集一般介紹及特設網站。
                                    is_article = False

                                if not is_article:
                                    continue

                                date_match = DATE_PATTERN.search(
                                    link["context"]
                                )

                                source_results.append({
                                    "title": title,
                                    "url": url,
                                    "source": source["name"],
                                    "publicationDate": (
                                        date_match.group(0)
                                        if date_match
                                        else None
                                    ),
                                })

                                print(
                                    f"公告候選：{title} | {url}"
                                )

                        except Exception as error:
                            print(
                                f"Frame 讀取問題：{error}"
                            )

                    page.close()

                except Exception as error:
                    errors.append(
                        f"{page_url}: {error}"
                    )
                    print(f"頁面讀取失敗：{error}")

            print(
                f'{source["name"]}: '
                f'找到 {len(source_results)} 筆公告候選'
            )

            all_results.extend(source_results)
# 測試讀取第一篇公告的完整內文
    if unique:
        test_url = list(unique.values())[0]["url"]

        print("\n===== 公告內文測試 =====")
        print(f"網址：{test_url}")

        test_page = browser.new_page()
        test_page.goto(
            test_url,
            wait_until="domcontentloaded",
            timeout=60000
        )
        test_page.wait_for_timeout(3000)

        article_text = test_page.locator("body").inner_text()

        print(article_text[:3000])

            test_page.close()
        browser.close()

    unique = {
        item["url"]: item
        for item in all_results
    }
    output = {
        "checkedAt": checked_at,
        "announcements": list(unique.values()),
        "errors": errors,
        "note": "瀏覽器擷取公告候選，尚未人工確認。",
    }

    Path("site").mkdir(exist_ok=True)

    Path("site/discovered.json").write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"\n完成：共整理 {len(unique)} 筆公告候選。"
    )

    if errors:
        print(f"另有 {len(errors)} 個頁面讀取錯誤。")


if __name__ == "__main__":
    main()
