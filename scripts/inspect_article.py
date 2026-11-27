
from playwright.sync_api import sync_playwright
import json

URLS = [
    "https://www.sonymusic.co.jp/artist/ReoNa/info/588829",
    "https://www.sonymusic.co.jp/artist/ReoNa/live/587352",
]

JS_INSPECT = r"""
() => {
    const root = document.querySelector(
        "div.a-content.a-content--info.content-loaded"
    ) || document.querySelector("div.a-content");

    if (!root) {
        return { found: false };
    }

    function describe(el, depth = 0) {
        if (depth > 5) return null;

        return {
            tag: el.tagName,
            id: el.id || "",
            className: typeof el.className === "string"
                ? el.className
                : "",
            textLength: (el.innerText || "").length,
            textPreview: (el.innerText || "")
                .replace(/\s+/g, " ")
                .slice(0, 180),
            children: Array.from(el.children)
                .map(child => describe(child, depth + 1))
                .filter(Boolean)
        };
    }

    const anchors = Array.from(root.querySelectorAll("a"))
        .map(a => ({
            text: (a.textContent || "").trim(),
            href: a.href
        }))
        .filter(a => a.text || a.href);

    return {
        found: true,
        root: describe(root),
        anchors: anchors.slice(0, 80)
    };
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    for url in URLS:
        print("\n" + "=" * 80)
        print("網址：", url)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            result = page.evaluate(JS_INSPECT)

            print(json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            ))

        except Exception as e:
            print("檢查失敗：", str(e))

    browser.close()
