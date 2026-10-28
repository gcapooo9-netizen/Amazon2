import time
import random
import html
import ssl
import json
import os
import re
import requests
import cloudscraper
from bs4 import BeautifulSoup

TOKEN = "8996279782:AAEJ-n3vP4K9bts15GC0_htKMceRC4yHj8E"
CHAT = "5124680786"
MIN_DROP_PERCENT = 20.0

CATEGORIES = [
    {
        "name": "عروض اليوم (Goldbox Deals)",
        "emoji": "⚡",
        "url": "https://www.amazon.eg/gp/goldbox/?ref_=navm_em_navm_deals_0_1_1_26&promotionsSearchLastSeenAsin=B0F5B7PLMF&promotionsSearchStartIndex=0&promotionsSearchPageSize=30"
    },
    {
        "name": "الأكثر مبيعاً - الجمال (Beauty)",
        "emoji": "💄",
        "url": "https://www.amazon.eg/gp/bestsellers/beauty/"
    },
    {
        "name": "قسم الأزياء المختار (Node 21832982031)",
        "emoji": "🛍️",
        "url": "https://www.amazon.eg/b?node=21832982031&ref_=AF_WIN_bub_w_cml_t_5&pf_rd_r=QCB6BEJAVNZAJWR86EGN&pf_rd_p=2d03f8ad-51b0-4d10-8fbc-c4d7b205fb81&pf_rd_m=A1ZVRGNO5AYLOV&pf_rd_s=mobile-hybrid-2&pf_rd_t=30901&pf_rd_i=18018102031"
    },
    {
        "name": "أزياء (فئة 100 إلى 290 ج.م - الأعلى تقييماً)",
        "emoji": "👕",
        "url": "https://www.amazon.eg/s?i=fashion&rh=n%3A18018165031%2Cn%3A21845147031%2Cn%3A21845181031%2Cn%3A21845407031%2Cp_36%3A10000-29000%2Cp_n_g-101015233022111%3A96332615031&s=review-rank&dc&ds=v1%3AxruoT5aHDeOyJnk7wEdBsyPgzBSNwswWnzVF44mDf78&pf_rd_i=18018165031&pf_rd_m=A1ZVRGNO5AYLOV&pf_rd_p=31e5a223-27e2-4623-89db-6a1fa1cd7fb9&pf_rd_r=NBE7RNNNMMRYJEHM0CNQ&pf_rd_s=mobile-hybrid-3&pf_rd_t=30901&qid=1778680864&rnid=21845181031&ref=AF_WIN_bub_w_cml_t_2"
    },
    {
        "name": "أزياء (فئة 56 إلى 215 ج.م - الأعلى تقييماً)",
        "emoji": "👗",
        "url": "https://www.amazon.eg/s?i=fashion&rh=n%3A18018165031%2Cn%3A21845147031%2Cn%3A21845181031%2Cn%3A21845419031%2Cp_36%3A5600-21500&s=review-rank&dc&pf_rd_i=18018165031&pf_rd_m=A1ZVRGNO5AYLOV&pf_rd_p=31e5a223-27e2-4623-89db-6a1fa1cd7fb9&pf_rd_r=NBE7RNNNMMRYJEHM0CNQ&pf_rd_s=mobile-hybrid-3&pf_rd_t=30901&qid=1778681250&rnid=21909190031&ref=AF_WIN_bub_w_cml_t_7"
    }
]

DB_FILE = "all_categories_prices.json"

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
}

AR = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")

if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            last_prices = json.load(f)
    except Exception:
        last_prices = {}
else:
    last_prices = {}

def save_prices():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(last_prices, f, ensure_ascii=False, indent=2)

def create_scraper():
    ctx = ssl.create_default_context()
    ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True},
        ssl_context=ctx
    )
    scraper.headers.update(H)
    return scraper

scraper = create_scraper()

def send(msg):
    u = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(u, json={"chat_id": CHAT, "text": msg, "parse_mode": "HTML"}, timeout=15)
        time.sleep(1.5)
    except Exception as e:
        print("Telegram error:", e)

def clean(text):
    x = text.translate(AR).replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", x)
    return float(m.group(0)) if m else None

def extract_asin(item):
    asin = item.get("data-asin")
    if asin and len(asin) == 10:
        return asin
    sub = item.select_one("[data-asin]")
    if sub and sub.get("data-asin") and len(sub.get("data-asin")) == 10:
        return sub.get("data-asin")
    for a in item.select("a[href]"):
        m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", a["href"])
        if m:
            return m.group(1)
    return None

def extract_product_name(item, asin):
    candidates = []
    img_tag = item.select_one("img[alt]")
    if img_tag and img_tag.get("alt"):
        alt_text = img_tag.get("alt").replace("إعلان ممول من", "").strip()
        if len(alt_text) > 5:
            candidates.append(alt_text)

    selectors = [
        "div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1",
        "div._cDEzb_p13n-sc-css-line-clamp-2_EWgCb",
        ".p13n-sc-truncate", "h2", ".a-size-base-plus",
        ".a-size-medium", "[data-testid='deal-card-title']"
    ]
    for selector in selectors:
        for tag in item.select(selector):
            text = tag.get_text(" ", strip=True)
            if text and text not in ["الأكثر مبيعاً", "اختيار أمازون"] and not text.startswith("#"):
                candidates.append(text)

    return max(candidates, key=len) if candidates else f"منتج أمازون ({asin})"

def extract_price(item):
    for selector in [".a-price-whole", "._cDEzb_p13n-sc-price_3mJ9Z", ".p13n-sc-price", ".a-color-price", ".a-price .a-offscreen", "[data-testid='deal-card-price']"]:
        for tag in item.select(selector):
            p = clean(tag.get_text())
            if p is not None and p > 0:
                return p
    return None

def check_category(cat):
    global scraper
    url = cat["url"].strip()
    print(f"Checking: {cat['name']}...")
    try:
        if not scraper.cookies:
            scraper.get("https://www.amazon.eg/", timeout=20)
            time.sleep(2)

        r = scraper.get(url, timeout=25)
        if r.status_code != 200:
            scraper = create_scraper()
            return

        s = BeautifulSoup(r.text, "html.parser")
        items = s.select("div.s-result-item[data-asin], div.zg-grid-general-faceout, div.p13n-sc-uncoverable-faceout, li.zg-item-immersion, div.octopus-pc-item-hue-shield, li.octopus-pc-item, div[data-testid='deal-card'], div[data-asin]")
        
        seen_asins = set()
        for item in items:
            asin = extract_asin(item)
            if not asin or asin in seen_asins:
                continue
            price = extract_price(item)
            if price is None:
                continue
            raw_name = extract_product_name(item, asin)
            if raw_name.startswith("منتج أمازون (") and len(item.select("img")) == 0:
                continue
                
            seen_asins.add(asin)
            old_price = last_prices.get(asin)
            
            if old_price is None:
                last_prices[asin] = price
            elif price != old_price:
                if price < old_price:
                    drop_amount = old_price - price
                    drop_percent = (drop_amount / old_price) * 100
                    if drop_percent >= MIN_DROP_PERCENT:
                        safe_name = html.escape(raw_name)
                        product_link = f"https://www.amazon.eg/dp/{asin}"
                        msg = (
                            f"🔥 <b>فرصة! هبوط سعر بنسبة {drop_percent:.1f}% {cat['emoji']}</b>\n"
                            f"📂 القسم: <b>{cat['name']}</b>\n\n"
                            f"🛒 <a href='{product_link}'>{safe_name}</a>\n"
                            f"📉 السعر السابق: <s>{old_price} ج.م</s>\n"
                            f"💰 السعر الآن: <b>{price} ج.م</b> (وفرت {drop_amount:.0f} ج.م)"
                        )
                        send(msg)
                last_prices[asin] = price
        save_prices()
    except Exception as e:
        print("Error:", e)

for category in CATEGORIES:
    check_category(category)
    time.sleep(random.randint(5, 10))
