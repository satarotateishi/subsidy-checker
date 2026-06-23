"""
補助金・助成金 新着チェッカー
対象：国（ミラサポplus, J-Net21）＋ 宮城県・東京
通知：Gmail
"""

import os
import json
import hashlib
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup

# ── 設定 ──────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
NOTIFY_TO          = os.environ["NOTIFY_TO"]

STATE_FILE = "seen_items.json"  # 既読管理ファイル（重複送信防止）

TARGETS = [
    {
        "name": "ミラサポplus（補助金・助成金）",
        "url": "https://mirasapo-plus.go.jp/subsidy/",
        "item_selector": "article, .subsidy-item, .list-item, li",
        "link_selector": "a",
    },
    {
        "name": "J-Net21（補助金・助成金カテゴリ）",
        "url": "https://j-net21.smrj.go.jp/snavi/articles?category%5B%5D=2",
        "item_selector": ".article-list li, .list-item, li, article",
        "link_selector": "a",
    },
    {
        "name": "J-Net21（支援情報ヘッドライン）",
        "url": "https://j-net21.smrj.go.jp/snavi2/",
        "item_selector": ".headline-list li, .news-list li, li",
        "link_selector": "a",
    },
    {
        "name": "気仙沼市 産業振興・助成金",
        "url": "https://www.kesennuma.miyagi.jp/sec/s072/",
        "item_selector": ".news li, .topics li, li",
        "link_selector": "a",
    },
    {
        "name": "仙台市 産業振興・助成金",
        "url": "https://www.city.sendai.jp/keizai-sogyo/index.html",
        "item_selector": ".news li, .topics li, li",
        "link_selector": "a",
    },
    {
        "name": "東京都中小企業振興公社（助成金）",
        "url": "https://www.tokyo-kosha.or.jp/support/josei/index.html",
        "item_selector": ".news-list li, .topics-list li, li",
        "link_selector": "a",
    },
]

KEYWORDS = [
    "補助金", "助成金", "公募", "募集開始", "申請受付",
    "支援金", "給付金", "補填", "IT導入", "省エネ", "事業再構築",
    "小規模事業者", "サービス業", "小売", "製造", "スタートアップ",
    "創業", "起業", "新規事業", "事業化", "実証",
    "販路開拓", "DX", "デジタル化", "イノベーション",
    "成長", "第二創業", "社会課題", "地域課題"
]
# ─────────────────────────────────────────────────────


def load_seen() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen(seen: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def item_id(text: str) -> str:
    return hashlib.md5(text.strip().encode()).hexdigest()


def fetch_items(target: dict) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SubsidyBot/1.0)"}
    try:
        res = requests.get(target["url"], headers=headers, timeout=15)
        res.raise_for_status()
        res.encoding = res.apparent_encoding
    except Exception as e:
        print(f"[WARN] {target['name']} 取得失敗: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    items = []
    for el in soup.select(target["item_selector"])[:40]:
        text = el.get_text(" ", strip=True)
        if len(text) < 8:
            continue
        link_tag = el.select_one(target["link_selector"])
        href = ""
        if link_tag and link_tag.get("href"):
            href = requests.compat.urljoin(target["url"], link_tag["href"])
        items.append({"text": text, "url": href, "source": target["name"]})
    return items


def is_relevant(text: str) -> bool:
    return any(kw in text for kw in KEYWORDS)


def summarize_with_claude(new_items: list[dict]) -> str:
    """Claude APIで新着情報を要約・整理（公募開始日・締切を抽出）"""
    items_text = "\n".join(
        f"- [{i['source']}] {i['text']}　{i['url']}" for i in new_items
    )
    prompt = f"""あなたは補助金・助成金の専門アドバイザーです。
以下は「amu株式会社」（宮城県仙台市・サービス業＆小売）向けに収集した新着補助金・助成金情報です。

{items_text}

以下の形式で各情報を整理してください。情報が読み取れない項目は「不明」と記載してください。

---
【重要度：高/中/低】
■ 補助金・助成金名：
■ 公募開始日：
■ 申請締切：
■ 概要：（2〜3行）
■ URL：
---

複数ある場合は重要度が高いものを上に並べてください。
最後に「申請期限が近いもの（1ヶ月以内）」があれば⚠️マークで警告してください。
日本語で、実務担当者がすぐ行動できるよう端的にまとめてください。"""

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    print(f"[DEBUG] Status code: {response.status_code}")
    response.raise_for_status()
    return response.json()["content"][0]["text"]


def send_email(subject: str, body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = NOTIFY_TO
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, NOTIFY_TO, msg.as_string())

    print(f"[INFO] メール送信完了 → {NOTIFY_TO}")


def main():
    print(f"=== 補助金チェック開始: {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    seen = load_seen()
    all_new = []

    for target in TARGETS:
        print(f"[CHECK] {target['name']}")
        items = fetch_items(target)
        for item in items:
            uid = item_id(item["text"])
            # 既読（seen）に入っているものはスキップ → 2回以上送らない
            if uid not in seen and is_relevant(item["text"]):
                seen[uid] = {
                    "text": item["text"][:80],
                    "found_at": datetime.now().isoformat(),
                    "notified": True  # 通知済みフラグ
                }
                all_new.append(item)

    save_seen(seen)
    print(f"[INFO] 新着件数: {len(all_new)}")

    if all_new:
        summary = summarize_with_claude(all_new)
        subject = f"【補助金新着】{len(all_new)}件の新着情報 ({datetime.now().strftime('%Y/%m/%d')})"
        body = f"{summary}\n\n---\n自動チェック日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        send_email(subject, body)
    else:
        print("[INFO] 新着なし。メール送信スキップ。")

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
