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

# === Lista miast ===
cities = ["krakow", "wroclaw", "warszawa", "trojmiasto"]

# === Lista na wszystkie mieszkania ===
all_flats = []

# === Data dzisiejsza ===
today_str = date.today().isoformat()  # np. '2025-10-17'
output_file = f"mieszkania_dom_{today_str}.csv"

# === Pobieranie mieszkań ===
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
        url_flats = f"https://www.domd.pl/iapi/search/search?resultsFor={inv_id}&&city={city}&language=pl-pl&type=mk&viewType=tiles&filters=null"

        r2 = requests.get(url_flats)
        r2.raise_for_status()
        flats_data = r2.json()["investments"][0]["flats"]
        flats_data = [f for f in flats_data if f.get("id") != "search_help_box"]

        for f in flats_data:
            row = {
                "city": city,
                "investment": inv_name,
                "flat": f.get("flat"),
                "building": f.get("building"),
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

        print(f"  {inv_name} – pobrano {len(flats_data)} mieszkań")
        time.sleep(0.2)  # lekkie opóźnienie

# === Zapis do CSV ===
df_today = pd.DataFrame(all_flats)
df_today.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"✅ Zapisano {len(df_today)} mieszkań do pliku {output_file}")

# === Porównanie z poprzednim dniem ===
# Szukamy ostatniego pliku CSV w folderze
folder = Path(".")
csv_files = sorted(folder.glob("mieszkania_dom_*.csv"))
if len(csv_files) >= 2:
    last_file = csv_files[-2]  # poprzedni dzień
    df_prev = pd.read_csv(last_file)
    
    # Sprawdzenie, które mieszkania zniknęły (sprzedane)
    sold = df_prev[~df_prev['link'].isin(df_today['link'])]
    print(f"🏠 Liczba mieszkań sprzedanych od ostatniego pobrania: {len(sold)}")
    if len(sold) > 0:
        print(sold[['city', 'investment', 'flat', 'link']])
else:
    print("Brak poprzedniego pliku do porównania – to pierwsze pobranie.")
