
from playwright.sync_api import sync_playwright

URL = (
    "https://www.sonymusic.co.jp/"
    "artist/ReoNa/info/588829"
)


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(3000)

        print("\n===== 頁面標題 =====")
        print(page.title())

        print("\n===== H1 及父層結構 =====")

        result = page.locator("h1").evaluate_all(
            """elements => elements.map(h1 => {

                let current = h1;
                let output = [];

                for (let i = 0; i < 8 && current; i++) {

                    output.push({
                        level: i,
                        tag: current.tagName,
                        id: current.id,
                        className: (
                            typeof current.className === "string"
                            ? current.className
                            : ""
                        ),
                        textLength: (
                            current.innerText || ""
                        ).length,
                        childCount: current.children.length,
                        textPreview: (
                            current.innerText || ""
                        ).slice(0, 180)
                    });

                    current = current.parentElement;
                }

                return output;
            })"""
        )

        for index, item in enumerate(result):

            print(f"\nH1 #{index + 1}")

            for parent in item:

                print(
                    f'\n層級：{parent["level"]}'
                )

                print(
                    f'標籤：{parent["tag"]}'
                )

                print(
                    f'ID：{parent["id"]}'
                )

                print(
                    f'Class：{parent["className"]}'
                )

                print(
                    f'文字長度：{parent["textLength"]}'
                )

                print(
                    f'子元素數量：{parent["childCount"]}'
                )

                print(
                    f'文字預覽：{parent["textPreview"]}'
                )

        browser.close()


if __name__ == "__main__":
    main()
