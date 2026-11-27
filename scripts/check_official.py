
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


def main():

    all_results = []
    errors = []

    checked_at = datetime.now(timezone.utc).isoformat()

    # =====================================
    # 開啟瀏覽器
    # =====================================

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        # =====================================
        # 逐一掃描官方網站
        # =====================================

        for source in SOURCES:

            source_results = []

            for page_url in source["pages"]:

                page = None

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

                    # =====================================
                    # 掃描頁面及 iframe 的連結
                    # =====================================

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

                                # 只接受指定官方網域
                                if parsed.netloc != source["domain"]:
                                    continue

                                title = (
                                    link["title"]
                                    or link["context"][:80]
                                    or "未命名公告"
                                )

                                # Sony Music 使用正式公告網址格式
                                if source["name"] == "Sony Music":

                                    is_article = bool(
                                        SONY_ARTICLE_PATTERN.fullmatch(
                                            parsed.path
                                        )
                                    )

                                else:

                                    # 官方網站文章網址格式尚待確認
                                    # 暫時不收集一般介紹及特設網站
                                    is_article = False

                                if not is_article:
                                    continue

                                # 擷取發布日期
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

                            print(
                                f"Frame 讀取問題：{error}"
                            )

                    print(
                        f"完成頁面掃描：{page_url}"
                    )

                except Exception as error:

                    errors.append(
                        f"{page_url}: {error}"
                    )

                    print(
                        f"頁面讀取失敗：{error}"
                    )

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

        # =====================================
        # 測試讀取第一篇公告完整內文
        # =====================================

        if unique:

            test_url = list(unique.values())[0]["url"]

            print("\n===== 公告內文測試 =====")

            print(f"網址：{test_url}")

            test_page = None

            try:

                test_page = browser.new_page()

                test_page.goto(
                    test_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                test_page.wait_for_timeout(3000)

                article_text = test_page.locator(
                    "body"
                ).inner_text()

                print("\n===== 擷取到的公告內容 =====")

                print(article_text[:3000])

                print("\n===== 公告內文測試完成 =====")

            except Exception as error:

                errors.append(
                    f"公告內文測試失敗：{error}"
                )

                print(
                    f"公告內文測試失敗：{error}"
                )

            finally:

                if test_page is not None:
                    test_page.close()

        else:

            print("\n沒有找到公告，略過內文測試。")

        # =====================================
        # 關閉瀏覽器
        # =====================================

        browser.close()

    # =====================================
    # 整理輸出資料
    # =====================================

    output = {
        "checkedAt": checked_at,
        "announcements": list(unique.values()),
        "errors": errors,
        "note": "瀏覽器擷取公告候選，尚未人工確認。",
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

    print("\n===== 執行結果 =====")

    print(
        f"完成：共整理 {len(unique)} 筆公告候選。"
    )

    print(
        f"錯誤數量：{len(errors)}"
    )

    print(
        "已更新：site/discovered.json"
    )


if __name__ == "__main__":
    main()
