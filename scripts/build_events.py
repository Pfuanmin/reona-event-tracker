
import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


# =====================================
# 檔案位置
# =====================================

DISCOVERED_FILE = Path("site/discovered.json")
EVENTS_FILE = Path("site/events.json")
OUTPUT_FILE = Path("site/suggested_events.json")


# =====================================
# 活動分類
# =====================================

CATEGORIES = [
    "演唱會及 Live",
    "粉絲俱樂部活動",
    "公開活動及合作演出",
    "電視、廣播及網路節目",
    "音樂作品及發售",
    "周邊商品及特典",
    "線上直播及配信",
]


# =====================================
# 日期格式
# =====================================

DATE_PATTERNS = [
    re.compile(
        r"(?P<year>20\d{2})\s*[./年-]\s*"
        r"(?P<month>\d{1,2})\s*[./月-]\s*"
        r"(?P<day>\d{1,2})\s*日?"
    ),
    re.compile(
        r"(?P<month>\d{1,2})月\s*"
        r"(?P<day>\d{1,2})日"
    ),
]


# =====================================
# 分類關鍵字
# =====================================

CATEGORY_KEYWORDS = [
    (
        "演唱會及 Live",
        [
            "ワンマン",
            "TOUR",
            "ツアー",
            "ライブ",
            "公演",
            "CONCERT",
            "LIVE",
        ],
    ),
    (
        "粉絲俱樂部活動",
        [
            "ふあんくらぶ",
            "ファンクラブ",
            "FC限定",
            "会員限定",
            "FCイベント",
        ],
    ),
    (
        "公開活動及合作演出",
        [
            "リリースイベント",
            "振替日程",
            "イベント出演",
            "ゲスト出演",
            "出演決定",
            "公開収録",
        ],
    ),
    (
        "電視、廣播及網路節目",
        [
            "テレビ",
            "ラジオ",
            "番組出演",
            "放送",
            "メディア出演",
        ],
    ),
    (
        "線上直播及配信",
        [
            "YouTube Premiere",
            "プレミア公開",
            "生配信",
            "ライブ配信",
            "配信番組",
            "配信決定",
        ],
    ),
    (
        "周邊商品及特典",
        [
            "グッズ",
            "Tシャツ",
            "購入特典",
            "予約特典",
            "会場限定特典",
            "特典",
        ],
    ),
    (
        "音樂作品及發售",
        [
            "アルバム",
            "シングル",
            "先行配信",
            "配信リリース",
            "楽曲配信",
            "発売決定",
            "リリース決定",
            "発売",
            "リリース",
            "収録曲",
        ],
    ),
]


# =====================================
# 讀取 JSON
# =====================================

def read_json(path, default):
    if not path.exists():
        print(f"找不到檔案：{path}")
        return default

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception as error:
        raise RuntimeError(
            f"JSON 讀取失敗：{path}：{error}"
        )


# =====================================
# 清理網址
# =====================================

def normalize_url(value):
    if not value:
        return ""

    value = str(value).strip()

    match = re.fullmatch(
        r"\[(.*?)\]\((https?://.*?)\)",
        value
    )

    if match:
        value = match.group(2)

    return value.strip()


# =====================================
# 建立公告日期參考年份
# =====================================

def get_reference_year(item):
    value = item.get("publicationDate") or ""

    match = re.search(r"20\d{2}", str(value))

    if match:
        return int(match.group())

    value = item.get("articleMeta") or ""

    match = re.search(r"20\d{2}", str(value))

    if match:
        return int(match.group())

    return None


# =====================================
# 日期辨識
# =====================================

def extract_dates(text, reference_year=None):

    results = []
    seen = set()

    if not text:
        return results

    for pattern in DATE_PATTERNS:

        for match in pattern.finditer(text):

            year_text = match.groupdict().get("year")

            month = int(match.group("month"))
            day = int(match.group("day"))

            if year_text:
                year = int(year_text)
                inferred = False
            else:
                year = reference_year
                inferred = True

            if year is None:
                continue

            try:
                date_value = datetime(
                    year,
                    month,
                    day
                ).date().isoformat()

            except ValueError:
                continue

            if date_value in seen:
                continue

            seen.add(date_value)

            start = max(0, match.start() - 45)
            end = min(len(text), match.end() + 45)

            results.append({
                "date": date_value,
                "originalText": match.group(0),
                "yearInferred": inferred,
                "context": text[start:end].replace(
                    "\n", " "
                ),
            })

    results.sort(
        key=lambda item: item["date"]
    )

    return results


# =====================================
# 分類建議
# =====================================

def suggest_category(title, content):

    text = (
        str(title or "")
        + "\n"
        + str(content or "")
    ).upper()

    for category, keywords in CATEGORY_KEYWORDS:

        for keyword in keywords:

            if keyword.upper() in text:
                return category

    return "未分類"


# =====================================
# 建立穩定 ID
# =====================================

def create_id(url):

    value = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:12]

    return "suggest-" + value


# =====================================
# 比對現有活動
# =====================================

def find_existing_matches(url, events):

    matches = []

    target = normalize_url(url)

    if not target:
        return matches

    for event in events:

        existing_url = normalize_url(
            event.get("url")
        )

        if existing_url == target:
            matches.append(
                event.get("id", "")
            )

    return matches


# =====================================
# 分析單篇公告
# =====================================

def analyze_announcement(item, events):

    title = (
        item.get("articleTitle")
        or item.get("title")
        or "未命名公告"
    )

    content = item.get("content") or ""

    url = normalize_url(
        item.get("url")
    )

    combined_text = (
        str(title)
        + "\n"
        + str(content)
    )

    reference_year = get_reference_year(item)

    dates = extract_dates(
        combined_text,
        reference_year
    )

    category = suggest_category(
        title,
        content
    )

    existing_matches = find_existing_matches(
        url,
        events
    )

    return {
        "id": create_id(url or title),
        "title": title,
        "categorySuggestion": category,
        "dateCandidates": dates,
        "publicationDate": item.get(
            "publicationDate"
        ),
        "sourceTitle": item.get("title"),
        "sourceUrl": url,
        "source": item.get("source"),
        "contentStatus": item.get(
            "contentStatus"
        ),
        "existingEventMatches": existing_matches,
        "reviewStatus": "待人工確認",
        "contentPreview": content[:500],
        "links": item.get("links", []),
    }


# =====================================
# 主程式
# =====================================

def main():

    print("===== ReoNa 活動資料分析 =====")

    discovered = read_json(
        DISCOVERED_FILE,
        {}
    )

    events = read_json(
        EVENTS_FILE,
        []
    )

    announcements = discovered.get(
        "announcements",
        []
    )

    if not isinstance(announcements, list):
        raise RuntimeError(
            "discovered.json 的 announcements 格式錯誤"
        )

    if not isinstance(events, list):
        raise RuntimeError(
            "events.json 必須是 JSON 陣列"
        )

    print(
        f"公告數量：{len(announcements)}"
    )

    print(
        f"現有活動數量：{len(events)}"
    )

    candidates = []

    seen_urls = set()

    for item in announcements:

        if not isinstance(item, dict):
            continue

        url = normalize_url(
            item.get("url")
        )

        if url and url in seen_urls:
            continue

        if url:
            seen_urls.add(url)

        candidate = analyze_announcement(
            item,
            events
        )

        candidates.append(candidate)

        print(
            "\n公告："
            + candidate["title"]
        )

        print(
            "分類建議："
            + candidate["categorySuggestion"]
        )

        print(
            "日期候選："
            + str(
                len(candidate["dateCandidates"])
            )
        )

    # =================================
    # 統計
    # =================================

    category_statistics = {}

    for item in candidates:

        category = item["categorySuggestion"]

        category_statistics[category] = (
            category_statistics.get(category, 0) + 1
        )

    output = {
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),

        "sourceFile": str(DISCOVERED_FILE),

        "existingEventCount": len(events),

        "announcementCount": len(announcements),

        "candidateCount": len(candidates),

        "categoryStatistics": category_statistics,

        "candidates": candidates,

        "note": (
            "本檔案僅供活動候選資料分析及人工確認。"
            "日期可能包含公告日期、預約期限及其他日期，"
            "不可直接視為活動日期。"
            "本程式不會修改 events.json。"
        ),
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("\n===== 分析完成 =====")

    print(
        f"公告總數：{len(announcements)}"
    )

    print(
        f"候選資料：{len(candidates)}"
    )

    print(
        f"分類統計：{category_statistics}"
    )

    print(
        f"已產生：{OUTPUT_FILE}"
    )

    print(
        "原有 events.json 未作任何修改。"
    )


if __name__ == "__main__":
    main()
