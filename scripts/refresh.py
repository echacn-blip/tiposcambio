#!/usr/bin/env python3
"""TiposCambio – descarga datos reales y los guarda en data/. Solo librería estándar.
  data/latest.json   tipos de cambio del día (open.er-api.com; respaldo: currency-api de fawazahmed0)
  data/history.json  últimos ~31 días: currency-api (todas las monedas) + Frankfurter/BCE (monedas del BCE)
  data/argentina.json  cotizaciones del dólar en Argentina (oficial, blue, MEP, CCL, cripto, tarjeta) de DolarAPI
  data/news.json     titulares reales de Google News RSS (es-419) y Ámbito, sin inventar nada
Uso: python3 scripts/refresh.py [--no-news] [--no-history]"""
import json, sys, pathlib, datetime, urllib.request, urllib.parse, re, html, email.utils, concurrent.futures as cf
import xml.etree.ElementTree as ET
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from currencies import CODES, ECB, PAIRS
ROOT = pathlib.Path(__file__).resolve().parents[1]; DATA = ROOT/"data"; DATA.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (TiposCambio refresh; +https://github.com/echacn-blip/tiposcambio)"}
NOW = datetime.datetime.now(datetime.timezone.utc)

def get(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r: return r.read()
def getj(url): return json.loads(get(url))
def save(name, obj):
    (DATA/name).write_text(json.dumps(obj, ensure_ascii=False, indent=1)); print(f"  ✓ data/{name}")

def fawaz(date="latest"):
    urls = [f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/usd.min.json",
            f"https://{date}.currency-api.pages.dev/v1/currencies/usd.min.json"]
    for u in urls:
        try:
            d = getj(u); return d["date"], {c: d["usd"][c.lower()] for c in CODES if c.lower() in d["usd"]}
        except Exception: continue
    return None, None

def latest():
    try:
        d = getj("https://open.er-api.com/v6/latest/USD"); assert d["result"] == "success"
        return {"source": "open.er-api.com", "source_name": "ExchangeRate-API (open access)", "source_url": "https://www.exchangerate-api.com/docs/free",
                "updated_unix": d["time_last_update_unix"], "next_update_unix": d["time_next_update_unix"], "base": "USD",
                "rates": {c: d["rates"][c] for c in CODES if c in d["rates"]}, "fetched_utc": NOW.isoformat(timespec="seconds")}
    except Exception as ex:
        print("  ! open.er-api.com falló:", ex, "→ respaldo currency-api")
        date, rates = fawaz()
        ts = int(datetime.datetime.fromisoformat(date).replace(tzinfo=datetime.timezone.utc).timestamp())
        return {"source": "currency-api", "source_name": "fawazahmed0/currency-api", "source_url": "https://github.com/fawazahmed0/exchange-api",
                "updated_unix": ts, "next_update_unix": None, "base": "USD", "rates": rates, "fetched_utc": NOW.isoformat(timespec="seconds")}

def history(days=31):
    end, _ = fawaz()
    end = datetime.date.fromisoformat(end) if end else NOW.date()
    dates = [(end - datetime.timedelta(days=i)).isoformat() for i in range(days-1, -1, -1)]
    with cf.ThreadPoolExecutor(8) as ex: res = list(ex.map(fawaz, dates))
    ok = [(d, r) for d, r in res if r]
    ca = {"source": "currency-api (fawazahmed0)", "source_url": "https://github.com/fawazahmed0/exchange-api", "base": "USD",
          "dates": [d for d, _ in ok], "rates": {c: [r.get(c) for _, r in ok] for c in CODES}}
    print(f"  currency-api: {len(ok)}/{len(dates)} días ({ca['dates'][0]} → {ca['dates'][-1]})")
    fr = None
    try:
        syms = ",".join(c for c in ECB if c != "USD")
        d = getj(f"https://api.frankfurter.dev/v1/{dates[0]}..{dates[-1]}?base=USD&symbols={syms}")
        fd = sorted(d["rates"])
        fr = {"source": "Frankfurter (Banco Central Europeo)", "source_url": "https://frankfurter.dev", "base": "USD",
              "dates": fd, "rates": {c: [d["rates"][x].get(c) for x in fd] for c in ECB if c != "USD"}}
        fr["rates"]["USD"] = [1.0]*len(fd)
        print(f"  Frankfurter: {len(fd)} días hábiles")
    except Exception as ex: print("  ! Frankfurter falló:", ex)
    pairs = {}
    for b, q, slug, _ in PAIRS:
        src = fr if (fr and b in ECB and q in ECB) else ca
        vals = [(dt, (src["rates"][q][i] / src["rates"][b][i]) if src["rates"][q][i] and src["rates"][b][i] else None) for i, dt in enumerate(src["dates"])]
        vals = [(dt, round(v, 6)) for dt, v in vals if v]
        pairs[f"{b}-{q}"] = {"source": src["source"], "source_url": src["source_url"], "dates": [x[0] for x in vals], "values": [x[1] for x in vals]}
    return {"generated_utc": NOW.isoformat(timespec="seconds"), "currency_api": ca, "frankfurter": fr, "pairs": pairs}

NEWS_FEEDS = [
    ("MX", "https://news.google.com/rss/search?q=%22tipo+de+cambio%22+peso+d%C3%B3lar+when:7d&hl=es-419&gl=MX&ceid=MX:es-419"),
    ("AR", "https://news.google.com/rss/search?q=d%C3%B3lar+cotizaci%C3%B3n+when:7d&hl=es-419&gl=AR&ceid=AR:es-419"),
    ("CO", "https://news.google.com/rss/search?q=%22precio+del+d%C3%B3lar%22+when:7d&hl=es-419&gl=CO&ceid=CO:es-419"),
    ("CL", "https://news.google.com/rss/search?q=d%C3%B3lar+peso+chileno+when:7d&hl=es-419&gl=CL&ceid=CL:es-419"),
    ("PE", "https://news.google.com/rss/search?q=tipo+de+cambio+d%C3%B3lar+sol+when:7d&hl=es-419&gl=PE&ceid=PE:es-419"),
    ("LATAM", "https://news.google.com/rss/search?q=divisas+monedas+latinoamericanas+when:7d&hl=es-419&gl=US&ceid=US:es-419"),
    ("AR", "https://www.ambito.com/rss/pages/economia.xml"),
    ("LATAM", "https://www.infobae.com/arc/outboundfeeds/rss/category/economia/"),
    ("AR", "https://www.iprofesional.com/rss/economia"),
]
FEED_NAMES = {"ambito.com": "Ámbito", "infobae.com": "Infobae", "iprofesional.com": "iProfesional"}
KW = re.compile(r"d[oó]lar|peso|tipo de cambio|divisa|moneda|cotiza|euro|real|sol peruano|banxico|bcra|tasa", re.I)
def news(per_feed=8, total=30):
    def one(item):
        cc, url = item
        try: root = ET.fromstring(get(url))
        except Exception as ex: print("  ! feed falló:", url[:70], ex); return []
        out = []
        for it in root.iter("item"):
            title = html.unescape((it.findtext("title") or "").strip()); link = (it.findtext("link") or "").strip()
            src_el = it.find("source"); src = (src_el.text if src_el is not None else "") or ""
            if "news.google.com" not in url:
                src = next(v for k, v in FEED_NAMES.items() if k in url)
            elif src and title.endswith(" - " + src): title = title[: -len(src) - 3].strip()
            try: dt = email.utils.parsedate_to_datetime(it.findtext("pubDate")).astimezone(datetime.timezone.utc)
            except Exception: continue
            if src.strip().lower() in ("facebook", "youtube", "tiktok", "instagram", "x"): continue
            if not title or not link or (NOW - dt).days > 7 or not KW.search(title): continue
            out.append({"title": title, "source": src.strip(), "date": dt.isoformat(timespec="seconds"), "link": link, "region": cc})
            if len(out) >= per_feed: break
        return out
    with cf.ThreadPoolExecutor(6) as ex: items = [x for r in ex.map(one, NEWS_FEEDS) for x in r]
    seen, uniq = set(), []
    for x in sorted(items, key=lambda x: x["date"], reverse=True):
        k = re.sub(r"\W+", "", x["title"].lower())[:60]
        if k in seen: continue
        seen.add(k); uniq.append(x)
    print(f"  noticias: {len(uniq[:total])} titulares")
    return {"generated_utc": NOW.isoformat(timespec="seconds"), "sources": ["Google News RSS (es-419)", "Ámbito (RSS Economía)", "Infobae (RSS Economía)", "iProfesional (RSS Economía)"], "items": uniq[:total]}

CASAS = {"oficial": "Oficial", "blue": "Blue", "bolsa": "MEP (bolsa)", "contadoconliqui": "CCL", "mayorista": "Mayorista", "cripto": "Cripto", "tarjeta": "Tarjeta"}
def argentina():
    d = getj("https://dolarapi.com/v1/dolares")
    return {"source": "DolarAPI", "source_url": "https://dolarapi.com", "fetched_utc": NOW.isoformat(timespec="seconds"),
            "items": [{"casa": x["casa"], "nombre": CASAS.get(x["casa"], x["nombre"]), "compra": x["compra"], "venta": x["venta"],
                       "actualizado": x["fechaActualizacion"]} for x in d if x.get("venta")]}

if __name__ == "__main__":
    print("Refrescando datos…")
    save("latest.json", latest())
    try: save("argentina.json", argentina())
    except Exception as ex: print("  ! DolarAPI falló:", ex, "→ se conserva data/argentina.json anterior")
    if "--no-history" not in sys.argv: save("history.json", history())
    if "--no-news" not in sys.argv:
        n = news()
        if n["items"]: save("news.json", n)
        else: print("  ! sin titulares; se conserva data/news.json anterior")
