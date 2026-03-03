import requests, re, os
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

PAGINAS = [
    {"nombre": "Sandwiches Calientes", "url": "https://www.sandwichesmonreal.com.ar/calientes.html", "tipo": "tabla"},
    {"nombre": "Triples Especiales", "url": "https://www.sandwichesmonreal.com.ar/triplesespeciales.html", "tipo": "regex"}
]
DOLAR_URL = "https://api.comparadolar.ar/usd"
CSV = "monreal_precios.csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def obtener_dolar():
    try:
        bn = next((x for x in requests.get(DOLAR_URL, timeout=10).json()
                   if x.get("slug") == "banco-nacion"), None)
        return float(bn["ask"]) if bn else 1.0
    except Exception:
        return 1.0

def limpiar_precio(s):
    try:
        return float(re.sub(r"[^\d]", "", str(s)))
    except Exception:
        return None

def scrape_pagina(url, tipo):
    productos = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        if tipo == "tabla":
            for fila in soup.find_all("tr"):
                celdas = fila.find_all(["td", "th"])
                if len(celdas) >= 2:
                    n = celdas[0].get_text(strip=True)
                    p = limpiar_precio(celdas[1].get_text(strip=True))
                    if p and p > 100:
                        productos.append({"nombre": n, "precio_ars": p})
        elif tipo == "regex":
            texto = soup.get_text()
            for m in re.finditer(r"(\d+)\s*/\s*\$?([\d\s\.]+)", texto):
                p = limpiar_precio(m.group(2))
                if p and p > 1000:
                    productos.append({"nombre": m.group(1) + " unidades", "precio_ars": p})
    except Exception as e:
        print("  Error " + url + ": " + str(e))
    return productos

def main():
    print("MONREALBOT iniciando...")
    dolar = obtener_dolar()
    print("Dolar BN: " + str(dolar))
    hoy = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for pag in PAGINAS:
        prods = scrape_pagina(pag["url"], pag["tipo"])
        print("  " + pag["nombre"] + ": " + str(len(prods)) + " productos")
        for p in prods:
            rows.append({
                "Fecha": hoy, "Categoria": pag["nombre"],
                "Producto": p["nombre"], "Precio_ARS": p["precio_ars"],
                "Precio_USD": round(p["precio_ars"] / dolar, 2), "Dolar_ARS": dolar
            })
    if not rows:
        print("Sin productos."); return
    df = pd.DataFrame(rows)
    if os.path.exists(CSV):
        dh = pd.read_csv(CSV)
        dh["Fecha"] = pd.to_datetime(dh["Fecha"]).dt.strftime("%Y-%m-%d")
        dh = dh[dh["Fecha"] != hoy]
        df = pd.concat([dh, df], ignore_index=True)
    df.to_csv(CSV, index=False)
    print("OK: " + str(len(rows)) + " productos para " + hoy)

if __name__ == "__main__":
    main()
