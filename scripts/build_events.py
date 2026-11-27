
import json
import re
import hashlib
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


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
    "未分類",
]


# =====================================
# 標題分類規則
# =====================================

TITLE_RULES = [
    (
        "粉絲俱樂部活動",
        [
            r"ふあんくらぶ",
            r"ファンクラブ",
            r"FC限定",
            r"会員限定",
            r"FCイベント",
        ],
    ),
    (
        "公開活動及合作演出",
        [
            r"リリースイベント",
            r"振替日程",
            r"イベント出演",
            r"ゲスト出演",
            r"公開収録",
            r"イベント開催",
        ],
    ),
    (
        "電視、廣播及網路節目",
        [
            r"テレビ出演",
            r"ラジオ出演",
            r"番組出演",
            r"放送決定",
            r"メディア出演",
        ],
    ),
    (
        "演唱會及 Live",
        [
            r"CONCERT",
            r"コンサート",
            r"ワンマン",
            r"TOUR",
            r"ツアー",
            r"ライブ開催",
            r"公演情報",
            r"公演決定",
        ],
    ),
    (
        "線上直播及配信",
        [
            r"リリックビデオ",
            r"Lyric Video",
            r"プレミア公開",
            r"YouTube Premiere",
            r"生配信",
            r"ライブ配信",
            r"配信番組",
        ],
    ),
    (
        "音樂作品及發售",
        [
            r"ベストアルバム",
            r"アルバム",
            r"シングル",
            r"楽曲配信",
            r"先行配信",
            r"配信リリース",
            r"Pre-add",
            r"Pre-save",
            r"発売決定",
            r"リリース決定",
            r"発売",
        ],
    ),
    (
        "周邊商品及特典",
        [
            r"オフィシャルグッズ",
            r"グッズ販売",
            r"グッズ",
            r"CD購入特典",
            r"購入特典",
            r"予約特典",
            r"会場予約特典",
            r"会場限定特典",
            r"特典決定",
        ],
    ),
]


# =====================================
# 正文備用分類規則
# =====================================

CONTENT_RULES = [
    (
        "粉絲俱樂部活動",
        [
            r"ファンクラブ限定",
            r"FC限定イベント",
            r"会員限定イベント",
        ],
    ),
    (
        "公開活動及合作演出",
        [
            r"リリースイベント",
            r"ゲスト出演",
            r"イベント出演",
        ],
    ),
    (
        "電視、廣播及網路節目",
        [
            r"テレビ出演",
            r"ラジオ出演",
            r"番組出演",
        ],
    ),
    (
        "演唱會及 Live",
        [
            r"コンサートツアー",
            r"ワンマンライブ",
            r"全国ツアー",
            r"公演日程",
        ],
    ),
    (
        "線上直播及配信",
        [
            r"プレミア公開",
            r"生配信",
            r"ライブ配信",
        ],
    ),
    (
        "音樂作品及發售",
        [
            r"ベストアルバム",
            r"シングル発売",
            r"先行配信",
            r"配信リリース",
        ],
    ),
    (
        "周邊商品及特典",
        [
            r"オフィシャルグッズ",
            r"購入特典",
            r"予約特典",
            r"会場販売",
            r"特典付き",
        ],
    ),
]


# =====================================
# 日期格式
# 一次處理完整日期及沒有年份的日期
# 避免 YYYY年MM月DD日 被重複抓取
# =====================================

DATE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:(?P<year>20\d{2})\s*[./年-]\s*)?"
    r"(?P<month>\d{1,2})"
    r"\s*[./月-]\s*"
    r"(?P<day>\d{1,2})"
    r"\s*日?"
    r"(?!\d)"
)


# =====================================
# 日期用途判斷
# =====================================

DATE_ROLE_RULES = [
    (
        "報名或預約期間",
        [
            "受付期間",
            "応募期間",
            "予約期間",
            "対象期間",
            "申込期間",
            "エントリー",
            "応募締切",
            "受付開始",
            "受付終了",
            "締切",
        ],
    ),
    (
        "影片或節目公開日",
        [
            "リリックビデオ",
            "プレミア公開",
            "YouTube Premiere",
            "公開日時",
            "公開日",
            "公開",
            "放送日",
            "放送",
        ],
    ),
    (
        "特典或販售日期",
        [
            "販売期間",
            "販売開始",
            "販売時間",
            "購入特典",
            "予約特典",
            "会場販売",
            "特典",
            "グッズ販売",
        ],
    ),
    (
        "音樂作品發售日",
        [
            "発売日",
            "発売",
            "リリース日",
            "リリース",
            "配信スタート",
            "配信開始",
            "先行配信",
            "Pre-add",
            "Pre-save",
        ],
    ),
    (
        "活動日期",
        [
            "開催日",
            "開催日時",
            "公演日",
            "公演日時",
            "出演日",
            "イベント開催",
            "振替日程",
            "OPEN",
            "START",
            "開催",
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
# 清理文字
# =====================================

def normalize_text(value):

    if not value:
        return ""

    return unicodedata.normalize(
        "NFKC",
        str(value)
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
# 取得公告參考年份
# =====================================

def get_reference_year(item):

    values = [
        item.get("articleMeta"),
        item.get("publicationDate"),
        item.get("articleTitle"),
        item.get("title"),
    ]

    for value in values:

        match = re.search(
            r"20\d{2}",
            normalize_text(value)
        )

        if match:
            return int(match.group())

    return None


# =====================================
# 從日期附近尋找明確年份
# =====================================

def find_nearby_year(text, position, reference_year):

    start = max(0, position - 100)
    end = min(len(text), position + 100)

    context = text[start:end]

    matches = list(
        re.finditer(r"20\d{2}", context)
    )

    if matches:

        nearest = min(
            matches,
            key=lambda match: abs(
                (start + match.start()) - position
            )
        )

        return int(nearest.group()), False

    if reference_year is not None:
        return reference_year, True

    return None, True


# =====================================
# 日期用途判斷
# =====================================

def identify_date_role(context):

    text = normalize_text(context)

    for role, keywords in DATE_ROLE_RULES:

        for keyword in keywords:

            if keyword in text:
                return role

    return "用途待確認"


# =====================================
# 日期辨識
# =====================================

def extract_dates(text, reference_year=None):

    results = []
    seen = set()

    if not text:
        return results

    normalized = normalize_text(text)

    for match in DATE_PATTERN.finditer(normalized):

        year_text = match.group("year")

        month = int(match.group("month"))
        day = int(match.group("day"))

        if year_text:

            year = int(year_text)
            inferred = False

        else:

            year, inferred = find_nearby_year(
                normalized,
                match.start(),
                reference_year
            )

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

        start = max(
            0,
            match.start() - 100
        )

        end = min(
            len(normalized),
            match.end() + 100
        )

        context = normalized[start:end].replace(
            "\n",
            " "
        )

        role = identify_date_role(context)

        # 相同日期、相同用途只保留一筆
        key = (
            date_value,
            role
        )

        if key in seen:
            continue

        seen.add(key)

        results.append({
            "date": date_value,
            "originalText": match.group(0),
            "yearInferred": inferred,
            "role": role,
            "context": context,
        })

    results.sort(
        key=lambda item: (
            item["date"],
            item["role"]
        )
    )

    return results


# =====================================
# 分類規則比對
# =====================================

def match_rules(text, rules):

    text = normalize_text(text)

    for category, patterns in rules:

        for pattern in patterns:

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE
            ):
                return category

    return "未分類"


# =====================================
# 分類建議
# =====================================

def suggest_category(title, content):

    normalized_title = normalize_text(title)

    # 先判斷明確的周邊及特典公告
    explicit_merch_patterns = [
        r"オフィシャルグッズ",
        r"グッズ販売",
        r"会場予約特典",
        r"会場限定特典",
        r"CD購入特典",
        r"購入特典",
        r"予約特典",
    ]

    for pattern in explicit_merch_patterns:

        if re.search(
            pattern,
            normalized_title,
            flags=re.IGNORECASE
        ):
            return "周邊商品及特典", "標題判斷"

    # T-shirt 等附加特典不應蓋過音樂作品發售
    category = match_rules(
        normalized_title,
        TITLE_RULES
    )

    if category != "未分類":
        return category, "標題判斷"

    category = match_rules(
        content,
        CONTENT_RULES
    )

    if category != "未分類":
        return category, "正文判斷"

    return "未分類", "無法判斷"


# =====================================
# 建立穩定 ID
# =====================================

def create_id(value):

    value = str(value or "unknown")

    result = hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:12]

    return "suggest-" + result


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

    reference_year = get_reference_year(item)

    full_text = (
        str(title)
        + "\n"
        + str(content)
    )

    dates = extract_dates(
        full_text,
        reference_year
    )

    category, category_basis = suggest_category(
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
        "categoryBasis": category_basis,
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

    print(f"公告數量：{len(announcements)}")
    print(f"現有活動數量：{len(events)}")

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

        print("\n公告：" + candidate["title"])

        print(
            "分類建議："
            + candidate["categorySuggestion"]
            + "（"
            + candidate["categoryBasis"]
            + "）"
        )

        print(
            "日期候選："
            + str(len(candidate["dateCandidates"]))
        )

        for date_item in candidate["dateCandidates"]:

            inferred_mark = (
                "（推定年份）"
                if date_item["yearInferred"]
                else ""
            )

            print(
                "  "
                + date_item["date"]
                + " | "
                + date_item["role"]
                + inferred_mark
            )

    # =================================
    # 分類統計
    # =================================

    category_statistics = {}

    for item in candidates:

        category = item["categorySuggestion"]

        category_statistics[category] = (
            category_statistics.get(category, 0) + 1
        )

    # =================================
    # 日期用途統計
    # =================================

    date_role_statistics = {}

    for item in candidates:

        for date_item in item["dateCandidates"]:

            role = date_item["role"]

            date_role_statistics[role] = (
                date_role_statistics.get(role, 0) + 1
            )

    # =================================
    # 年份推定統計
    # =================================

    inferred_count = sum(
        1
        for item in candidates
        for date_item in item["dateCandidates"]
        if date_item["yearInferred"]
    )

    explicit_count = sum(
        1
        for item in candidates
        for date_item in item["dateCandidates"]
        if not date_item["yearInferred"]
    )

    # =================================
    # 輸出資料
    # =================================

    output = {
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),

        "sourceFile": str(DISCOVERED_FILE),

        "existingEventCount": len(events),

        "announcementCount": len(announcements),

        "candidateCount": len(candidates),

        "categoryStatistics": category_statistics,

        "dateRoleStatistics": date_role_statistics,

        "dateYearStatistics": {
            "explicitYear": explicit_count,
            "inferredYear": inferred_count,
        },

        "candidates": candidates,

        "note": (
            "本檔案僅供活動候選資料分析及人工確認。"
            "完整日期優先使用公告明確標示的年份。"
            "未標示年份的日期優先尋找附近明確年份，"
            "再使用公告參考年份推定。"
            "相同日期及用途的紀錄只保留一筆。"
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

    print(f"公告總數：{len(announcements)}")
    print(f"候選資料：{len(candidates)}")

    print(
        f"分類統計：{category_statistics}"
    )

    print(
        f"日期用途統計：{date_role_statistics}"
    )

    print(
        "年份統計："
        f"明確年份 {explicit_count} 筆，"
        f"推定年份 {inferred_count} 筆"
    )

    print(
        f"已產生：{OUTPUT_FILE}"
    )

    print(
        "原有 events.json 未作任何修改。"
    )


if __name__ == "__main__":
    main()
