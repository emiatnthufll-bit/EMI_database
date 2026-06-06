import requests
import json

try:
    r = requests.get('http://localhost:8000/facets')
    data = r.json()
    for key, items in data.items():
        print(f"--- {key} ---")
        for item in items:
            print(f"{item['id']}: {item['cnt']}")
except Exception as e:
    print(e)
