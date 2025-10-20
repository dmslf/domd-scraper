import requests
import pandas as pd

url_investments = "https://www.domd.pl/iapi/search/search?city=krakow&type=mk&language=pl-pl"

r = requests.get(url_investments)
r.raise_for_status()
data = r.json()

investments = data.get("investments", [])
print(f"Znaleziono {len(investments)} inwestycji w Krakowie")
