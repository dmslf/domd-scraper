import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import time

# --- Funkcje pomocnicze ---
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

all_flats = []
cities = ["krakow", "wroclaw", "warszawa", "trojmiasto"]

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
            }
            if row["area_m2"] and row["price_new_zlm2"]:
                row["total_price_zl"] = row["area_m2"] * row["price_new_zlm2"]
            else:
                row["total_price_zl"] = None
            all_flats.append(row)

        print(f"  {inv_name} – pobrano {len(flats_data)} mieszkań")
        time.sleep(0.2)  # lekkie opóźnienie, żeby nie przeciążać serwera

# --- Zapis do CSV ---
df = pd.DataFrame(all_flats)
df.to_csv("wszystkie_mieszkania_4_miasta.csv", index=False, encoding="utf-8-sig")
print(f"✅ Zapisano {len(df)} mieszkań do pliku wszystkie_mieszkania_4_miasta.csv")
