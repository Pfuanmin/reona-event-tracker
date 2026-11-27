
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

from playwright.sync_api import sync_playwright


# =====================================
# 官方網站來源
# =====================================

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


# Sony Music 正式公告網址格式
SONY_ARTICLE_PATTERN = re.compile(
    r"^/artist/ReoNa/(?:info|live)/\d+/?$"
)

# 公告日期格式
DATE_PATTERN = re.compile(
    r"20\d{2}[./年-]\d{1,2}[./月-]\d{1,2}日?"
)


def collect_announcements(browser):

    all_results = []
    errors = []

    # =====================================
    # 掃描官方網站
    # =====================================

    for source in SOURCES:

        source_results = []

        for page_url in source["pages"]:

            page = None

            try:

                page = browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 "
                        "ReoNaEventTracker/5.0"
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

                        print(f"Frame：{frame.url}")
                        print(f"找到連結：{len(links)} 筆")

                        for link in links:

                            url = urljoin(
                                frame.url or page_url,
                                link["href"]
                            )

                            url, _ = urldefrag(url)

                            parsed = urlparse(url)

                            if parsed.netloc != source["domain"]:
                                continue

                            title = (
                                link["title"]
                                or link["context"][:80]
                                or "未命名公告"
                            )

                            # Sony Music 公告網址判斷
                            if source["name"] == "Sony Music":

                                is_article = bool(
                                    SONY_ARTICLE_PATTERN.fullmatch(
                                        parsed.path
                                    )
                                )

                            else:

                                # 官方網站文章網址格式
                                # 尚待確認，暫時不收集
                                is_article = False

                            if not is_article:
                                continue

                            date_match = DATE_PATTERN.search(
                                link["context"]
                            )

                            result = {
                                "title": title,
                                "url": url,
                                "source": source["name"],
                                "publicationDate": (
                                    date_match.group(0)
                                    if date_match
                                    else None
                                ),
                            }

                            source_results.append(result)

                            print(
                                f"公告候選：{title} | {url}"
                            )

                    except Exception as error:

                        message = (
                            f"Frame 讀取問題 "
                            f"{page_url}: {error}"
                        )

                        errors.append(message)
                        print(message)

            except Exception as error:

                message = f"{page_url}: {error}"

                errors.append(message)
                print(f"頁面讀取失敗：{error}")

            finally:

                if page is not None:
                    page.close()

        print(
            f'{source["name"]}: '
            f'找到 {len(source_results)} 筆公告候選'
        )

        all_results.extend(source_results)

    # =====================================
    # 排除重複公告
    # =====================================

    unique = {
        item["url"]: item
        for item in all_results
    }

    print(
        f"\n去除重複後：{len(unique)} 筆公告"
    )

    return list(unique.values()), errors


def fetch_article_content(browser, announcements, errors):

    # =====================================
    # 逐篇讀取公告完整內文
    # =====================================

    print("\n===== 開始讀取公告內文 =====")

    for index, item in enumerate(announcements, start=1):

        page = None

        print(
            f"\n[{index}/{len(announcements)}] "
            f'正在讀取：{item["title"]}'
        )

        try:

            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 "
                    "ReoNaEventTracker/5.0"
                )
            )

            page.goto(
                item["url"],
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(3000)

            # 先讀取完整頁面文字
            article_text = page.locator(
                "body"
            ).inner_text()

            article_text = article_text.strip()

            if not article_text:

                raise Exception("公告內文為空")

            # 保存完整內文
            item["content"] = article_text

            item["contentStatus"] = "success"

            item["contentFetchedAt"] = (
                datetime.now(timezone.utc).isoformat()
            )

            print(
                f"讀取成功：{len(article_text)} 個字元"
            )

        except Exception as error:

            item["content"] = ""

            item["contentStatus"] = "failed"

            item["contentError"] = str(error)

            message = (
                f'公告內文讀取失敗：{item["url"]} '
                f'錯誤：{error}'
            )

            errors.append(message)

            print(message)

        finally:

            if page is not None:
                page.close()


def main():

    checked_at = datetime.now(timezone.utc).isoformat()

    # =====================================
    # 開啟瀏覽器
    # =====================================

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        # 掃描公告
        announcements, errors = collect_announcements(
            browser
        )

        # 讀取所有公告內文
        fetch_article_content(
            browser,
            announcements,
            errors
        )

        browser.close()

    # =====================================
    # 統計結果
    # =====================================

    success_count = sum(
        1
        for item in announcements
        if item.get("contentStatus") == "success"
    )

    failed_count = sum(
        1
        for item in announcements
        if item.get("contentStatus") == "failed"
    )

    # =====================================
    # 整理輸出資料
    # =====================================

    output = {
        "checkedAt": checked_at,

        "announcements": announcements,

        "statistics": {
            "total": len(announcements),
            "contentSuccess": success_count,
            "contentFailed": failed_count,
        },

        "errors": errors,

        "note": (
            "已擷取官方公告內文，"
            "尚未進行活動分類及日期辨識。"
        ),
    }

    # =====================================
    # 儲存 discovered.json
    # =====================================

    Path("site").mkdir(exist_ok=True)

    Path("site/discovered.json").write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # =====================================
    # 執行結果
    # =====================================

    print("\n===== 執行結果 =====")

    print(
        f"公告總數：{len(announcements)}"
    )

    print(
        f"內文讀取成功：{success_count}"
    )

    print(
        f"內文讀取失敗：{failed_count}"
    )

    print(
        f"錯誤數量：{len(errors)}"
    )

    print(
        "已更新：site/discovered.json"
    )


if __name__ == "__main__":
    main()
