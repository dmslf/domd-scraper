import pandas as pd
from datetime import date, timedelta
import glob
import os

def unique_key(row):
    """Tworzymy unikalny identyfikator mieszkania"""
    return f"{row['city']}|{row['investment']}|{row['building']}|{row['flat']}"

# === Ustal zakres dat ===
today = date.today()
start_date = today - timedelta(days=6)
start_str = start_date.isoformat()
end_str = today.isoformat()

# === Znajdź wszystkie pliki z ostatnich 7 dni ===
files = sorted(glob.glob("mieszkania_dom_*.csv"))
files_in_range = [f for f in files if start_str <= f[-14:-4] <= end_str]

if not files_in_range:
    print("❌ Brak plików CSV w zadanym zakresie.")
    exit(0)

print(f"Analizuję pliki: {files_in_range}")

# === Wczytaj wszystkie dane i nadaj klucz ===
all_data = {}
for f in files_in_range:
    df = pd.read_csv(f)
    df["key"] = df.apply(unique_key, axis=1)
    all_data[f] = df

# === Zbiór kluczy z każdego dnia ===
day_keys = {f: set(df["key"]) for f, df in all_data.items()}

# === Ustalamy pierwsze i ostatnie pliki w tygodniu ===
first_file = files_in_range[0]
last_file = files_in_range[-1]

# Wszystkie klucze, które pojawiły się kiedykolwiek w tygodniu
all_keys = set().union(*day_keys.values())

# Klucze, które są w ostatnim dniu (czyli nadal dostępne)
active_last = day_keys[last_file]

# Klucze, które pojawiły się w którymś dniu, ale nie ma ich w ostatnim → SPRZEDANE
sold_keys = [k for k in all_keys if k not in active_last]

# Klucze, które pojawiły się w tygodniu, ale nie było ich w pierwszym dniu → NOWE
active_first = day_keys[first_file]
new_keys = [k for k in all_keys if k not in active_first and k in active_last]

# === Tworzymy CSV z pełnymi danymi ===
def export_subset(keys, name):
    rows = []
    for f, df in all_data.items():
        subset = df[df["key"].isin(keys)]
        rows.append(subset)
    if rows:
        df_out = pd.concat(rows).drop_duplicates("key")
        output_name = f"mieszkania_dom_{name}_{start_str}_to_{end_str}.csv"
        df_out.to_csv(output_name, index=False, encoding="utf-8-sig")
        print(f"✅ Zapisano {len(df_out)} rekordów do {output_name}")
        return df_out
    else:
        print(f"⚠️ Brak danych do zapisania dla {name}")
        return pd.DataFrame()


export_subset(new_keys, "nowe")
export_subset(sold_keys, "sprzedane")

print("\n✅ Analiza zakończona pomyślnie.")

# === Eksport plików szczegółowych ===
df_new = export_subset(new_keys, "nowe")
df_sold = export_subset(sold_keys, "sprzedane")

# === Tworzymy podsumowanie per inwestycja ===
if not all_data:
    print("⚠️ Brak danych do podsumowania tygodniowego.")
    exit(0)

# liczba nowych i sprzedanych per inwestycja
new_counts = df_new.groupby("investment").size().rename("liczba_dodanych") if not df_new.empty else pd.Series(dtype=int)
sold_counts = df_sold.groupby("investment").size().rename("liczba_zdjetych") if not df_sold.empty else pd.Series(dtype=int)

# liczba dostępnych na początku i końcu tygodnia
first_counts = all_data[first_file].groupby("investment").size().rename(f"dostepnych_{start_str}")
last_counts = all_data[last_file].groupby("investment").size().rename(f"dostepnych_{end_str}")

# scal wszystko
summary = pd.concat([sold_counts, new_counts, first_counts, last_counts], axis=1).fillna(0).astype(int)

# Dodaj kolumnę miasto — bierzemy pierwsze miasto występujące dla danej inwestycji
combined_df = pd.concat(all_data.values(), ignore_index=True)
city_map = combined_df.dropna(subset=["investment", "city"]).drop_duplicates("investment")[["investment", "city"]]
city_map = dict(zip(city_map["investment"], city_map["city"]))
summary["miasto"] = summary.index.map(city_map)

# uporządkuj kolumny: inwestycja, miasto, liczby
summary.reset_index(inplace=True)
summary.rename(columns={"investment": "inwestycja"}, inplace=True)
cols = ["inwestycja", "miasto", "liczba_zdjetych", "liczba_dodanych", f"dostepnych_{start_str}", f"dostepnych_{end_str}"]
summary = summary[cols]

# zapis
output_summary = f"mieszkania_dom_podsumowanie_{start_str}_to_{end_str}.csv"
summary.to_csv(output_summary, index=False, encoding="utf-8-sig")

print(f"✅ Zapisano podsumowanie tygodniowe: {output_summary}")
print("\n✅ Analiza zakończona pomyślnie.")


# 1. Ile mieszkań pojawiło się i zniknęło w trakcie tygodnia (czyli nie ma ich na początku ani końcu)
transient = [
    k for k in all_keys
    if k not in active_first and k not in active_last
]
print(f"Liczba mieszkań, które pojawiły się i zniknęły w środku tygodnia: {len(transient)}")
