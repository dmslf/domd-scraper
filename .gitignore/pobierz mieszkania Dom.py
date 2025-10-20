import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import time
from pathlib import Path
from datetime import date

# === Funkcje pomocnicze ===
def clean_html(text):
    if not text:
        return None
    return BeautifulSoup(text, "html.parser").get_text().strip()

def to_number(txt):
    if not txt:
        return None
    txt = re.sub(r"[^\d,]", "", txt).replace(",", ".")
    try:
        return float(txt)
    except:
        return None

def extract_handover_per_building(url):
    """
    Zwraca słownik { 'Budynek A': '3 kw. 2027', 'Budynek B': '4 kw. 2028' } 
    lub {'Inwestycja': '3 kw. 2027'} jeśli jeden termin.
    """
    result = {}
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return result
        soup = BeautifulSoup(r.text, "html.parser")

        # 1️⃣ Szukamy wszystkich paragrafów i divów z tekstem "termin", "oddanie" lub "zakończenie"
        candidates = []
        for tag in soup.find_all(["p", "div", "li", "span"]):
            text = tag.get_text(" ", strip=True)
            if re.search(r"(termin|oddanie|zakończenie)", text, re.IGNORECASE):
                candidates.append(text)

        # 2️⃣ Parsujemy znalezione linie
        for text in candidates:
            # Budynek A + kwartał
            m = re.findall(
                r"(Budynek\s+[A-ZĄĆĘŁŃÓŚŹŻ])[^.,;:]*?([1-4IV]+\s*kw\.?\s*\d{4})",
                text,
                re.IGNORECASE,
            )
            for b, d in m:
                result[b] = d.strip()

            # Ogólny termin bez budynku
            if not m:
                q = re.search(r"([1-4IV]+\s*kw\.?\s*\d{4})", text, re.IGNORECASE)
                if q:
                    result["Inwestycja"] = q.group(1).strip()

        # 3️⃣ Jeśli nadal nic, sprawdź sam tekst strony
        if not result:
            text = soup.get_text(" ", strip=True)
            q = re.search(r"([1-4IV]+\s*kw\.?\s*\d{4})", text, re.IGNORECASE)
            if q:
                result["Inwestycja"] = q.group(1).strip()

        return result
    except Exception as e:
        print(f"Błąd w extract_handover_per_building: {e}")
        return result


# === Lista miast ===
cities = ["krakow", "wroclaw", "warszawa", "trojmiasto"]

# === Data dzisiejsza ===
today_str = date.today().isoformat()
output_file = f"mieszkania_dom_{today_str}.csv"

all_flats = []

for city in cities:
    print(f"=== Pobieram inwestycje dla miasta: {city} ===")
    url_investments = f"https://www.domd.pl/iapi/search/search?city={city}&type=mk&language=pl-pl"
    r = requests.get(url_investments)
    r.raise_for_status()
    data = r.json()
    investments = data.get("investments", [])
    print(f"Znaleziono {len(investments)} inwestycji w {city}")

    for inv in investments:
        inv_id = inv["id"]
        inv_name = inv.get("name")
        inv_link = inv.get("more", {}).get("href")
        full_url = f"https://www.domd.pl{inv_link}" if inv_link else None

        # 🔹 Pobierz terminy odbioru per budynek
        handover_dict = extract_handover_per_building(full_url) if full_url else {}

        # 🔹 Pobierz mieszkania
        url_flats = f"https://www.domd.pl/iapi/search/search?resultsFor={inv_id}&&city={city}&language=pl-pl&type=mk&viewType=tiles&filters=null"
        r2 = requests.get(url_flats)
        r2.raise_for_status()
        flats_data = r2.json()["investments"][0]["flats"]
        flats_data = [f for f in flats_data if f.get("id") != "search_help_box"]

        for f in flats_data:
            building = f.get("building")
            row = {
                "city": city,
                "investment": inv_name,
                "building": building,
                "handover_date": handover_dict.get(f"Budynek {building}", handover_dict.get("Inwestycja")),
                "flat": f.get("flat"),
                "area_m2": to_number(f.get("area")),
                "rooms": clean_html(f.get("rooms")),
                "floor": clean_html(f.get("floor")),
                "logy": f.get("logy"),
                "price_new_zlm2": to_number(f.get("price", {}).get("new")),
                "price_old_zlm2": to_number(f.get("price", {}).get("old")),
                "promo": f.get("price", {}).get("isPromo"),
                "link": f.get("more", {}).get("href"),
                "img": f.get("picture", {}).get("img"),
                "date_scraped": today_str
            }
            if row["area_m2"] and row["price_new_zlm2"]:
                row["total_price_zl"] = row["area_m2"] * row["price_new_zlm2"]
            else:
                row["total_price_zl"] = None
            all_flats.append(row)

        print(f"  {inv_name} – {len(flats_data)} mieszkań, terminy: {handover_dict}")
        time.sleep(0.5)

# === Zapis do CSV ===
df_today = pd.DataFrame(all_flats)
df_today.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"\n✅ Zapisano {len(df_today)} mieszkań do pliku {output_file}")

# === Porównanie z poprzednim dniem ===
folder = Path(".")
csv_files = sorted(folder.glob("mieszkania_dom_*.csv"))
if len(csv_files) >= 2:
    last_file = csv_files[-2]
    df_prev = pd.read_csv(last_file)
    sold = df_prev[~df_prev['link'].isin(df_today['link'])]
    print(f"🏠 Liczba mieszkań sprzedanych od ostatniego pobrania: {len(sold)}")
    if len(sold) > 0:
        print(sold[['city', 'investment', 'flat', 'link']])
else:
    print("Brak poprzedniego pliku do porównania – to pierwsze pobranie.")
