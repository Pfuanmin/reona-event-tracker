
import json
import re
import html
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


# 只接受單篇 INFO 公告
SONY_ARTICLE_PATTERN = re.compile(
    r"^/artist/ReoNa/info/\d+/?$"
)

DATE_PATTERN = re.compile(
    r"20\d{2}[./年-]\d{1,2}[./月-]\d{1,2}日?"
)


# =====================================
# 清理網址
# =====================================

def clean_url(value):
    if not value:
        return ""

    value = html.unescape(str(value)).strip()

    # 處理 Markdown 格式：[網址](網址)
    match = re.fullmatch(
        r"\[.*?\]\((https?://.*?)\)",
        value
    )

    if match:
        value = match.group(1)

    return value.strip()


# =====================================
# 搜尋官方公告
# =====================================

def collect_announcements(browser):

    all_results = []
    errors = []

    for source in SOURCES:

        source_results = []

        for page_url in source["pages"]:

            page = None

            try:
                page = browser.new_page()

                print(f"\n正在開啟：{page_url}")

                page.goto(
                    page_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                page.wait_for_timeout(5000)

                print(
                    f"檢查頁面及 iframe：{len(page.frames)} 個"
                )

                for frame in page.frames:

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

                                href: a.getAttribute("href"),

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

                            raw_href = clean_url(link["href"])

                            if not raw_href:
                                continue

                            url = urljoin(
                                frame.url or page_url,
                                raw_href
                            )

                            url, _ = urldefrag(url)

                            parsed = urlparse(url)

                            if parsed.netloc != source["domain"]:
                                continue

                            if source["name"] == "Sony Music":
                                is_article = bool(
                                    SONY_ARTICLE_PATTERN.fullmatch(
                                        parsed.path
                                    )
                                )
                            else:
                                is_article = False

                            if not is_article:
                                continue

                            date_match = DATE_PATTERN.search(
                                link["context"]
                            )

                            source_results.append({
                                "title": (
                                    link["title"]
                                    or "未命名公告"
                                ),
                                "url": url,
                                "source": source["name"],
                                "publicationDate": (
                                    date_match.group(0)
                                    if date_match
                                    else None
                                ),
                            })

                    except Exception as error:

                        message = (
                            f"Frame 讀取問題：{page_url}: {error}"
                        )

                        errors.append(message)
                        print(message)

            except Exception as error:

                message = f"{page_url}: {error}"

                errors.append(message)
                print(message)

            finally:
                if page is not None:
                    page.close()

        print(
            f'{source["name"]}: '
            f'找到 {len(source_results)} 筆公告候選'
        )

        all_results.extend(source_results)

    # 依網址去重
    unique = {
        item["url"]: item
        for item in all_results
    }

    results = list(unique.values())

    print(
        f"\n去除重複後：{len(results)} 筆公告"
    )

    return results, errors


# =====================================
# 擷取公告正文及超連結
# =====================================

def fetch_article_content(browser, announcements, errors):

    print("\n===== 開始讀取公告正文 =====")

    for index, item in enumerate(announcements, start=1):

        page = None

        print(
            f'\n[{index}/{len(announcements)}] '
            f'正在讀取：{item["url"]}'
        )

        try:
            page = browser.new_page()

            page.goto(
                item["url"],
                wait_until="domcontentloaded",
                timeout=60000
            )

            # 等待真正的公告正文載入
            content = page.locator(
                ".p-infoContent"
            ).first

            content.wait_for(
                state="visible",
                timeout=30000
            )

            page.wait_for_timeout(2000)

            # 正式公告標題
            heading = page.locator(
                "h1.p-infoHeader__title"
            ).first

            if heading.count() > 0:
                item["articleTitle"] = (
                    heading.inner_text().strip()
                )
            else:
                item["articleTitle"] = item["title"]

            # 正式公告日期資訊
            meta = page.locator(
                ".p-infoHeader__meta"
            ).first

            if meta.count() > 0:
                item["articleMeta"] = (
                    meta.inner_text().strip()
                )

                date_match = DATE_PATTERN.search(
                    item["articleMeta"]
                )

                if date_match:
                    item["publicationDate"] = (
                        date_match.group(0)
                    )

            # 只擷取真正的公告正文
            article_text = content.inner_text().strip()

            if not article_text:
                raise Exception("公告正文內容為空")

            item["content"] = article_text

            # 獨立擷取正文內的超連結
            raw_links = content.locator(
                "a[href]"
            ).evaluate_all(
                """els => els.map(a => ({
                    text: (
                        a.innerText ||
                        a.getAttribute("aria-label") ||
                        a.querySelector("img")?.alt ||
                        ""
                    ).trim(),
                    href: a.getAttribute("href")
                }))"""
            )

            article_links = []
            seen_urls = set()

            for link in raw_links:

                raw_href = clean_url(link["href"])

                if not raw_href:
                    continue

                link_url = urljoin(
                    item["url"],
                    raw_href
                )

                link_url, _ = urldefrag(link_url)

                parsed_link = urlparse(link_url)

                if parsed_link.scheme not in ("http", "https"):
                    continue

                if link_url in seen_urls:
                    continue

                seen_urls.add(link_url)

                article_links.append({
                    "text": link["text"],
                    "url": link_url,
                })

            item["links"] = article_links

            item["contentStatus"] = "success"

            item["contentFetchedAt"] = (
                datetime.now(timezone.utc).isoformat()
            )

            item.pop("contentError", None)

            print(
                f"正文擷取成功：{len(article_text)} 個字元"
            )

            print(
                f'正式標題：{item["articleTitle"]}'
            )

            print(
                f"超連結數量：{len(article_links)}"
            )

            print(
                f"正文預覽：{article_text[:250]}"
            )

        except Exception as error:

            item["content"] = ""
            item["links"] = []
            item["contentStatus"] = "failed"
            item["contentError"] = str(error)

            message = (
                f'公告正文讀取失敗：{item["url"]} '
                f'錯誤：{error}'
            )

            errors.append(message)
            print(message)

        finally:
            if page is not None:
                page.close()


# =====================================
# 主程式
# =====================================

def main():

    checked_at = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        announcements, errors = collect_announcements(
            browser
        )

        fetch_article_content(
            browser,
            announcements,
            errors
        )

        browser.close()

    # =====================================
    # 統計
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
            "已使用 Sony Music 正式公告標題、日期及正文容器，"
            "並獨立擷取公告內超連結；尚未進行活動分類及日期辨識。"
        ),
    }

    # =====================================
    # 儲存 JSON
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

    print("\n===== 執行結果 =====")

    print(f"公告總數：{len(announcements)}")
    print(f"正文讀取成功：{success_count}")
    print(f"正文讀取失敗：{failed_count}")
    print(f"錯誤數量：{len(errors)}")

    print("已更新：site/discovered.json")


if __name__ == "__main__":
    main()
