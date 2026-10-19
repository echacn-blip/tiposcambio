#!/usr/bin/env python3
"""TiposCambio – genera el sitio estático en site/ desde data/*.json + config.json. Solo librería estándar.
Configuración (config.json o variables de entorno):
  SITE_URL            URL pública, p. ej. https://echacn-blip.github.io/tiposcambio
  BASE_PATH           subruta de GitHub Pages, p. ej. /tiposcambio/ (solo 404.html; el resto usa enlaces relativos)
  NEWSLETTER_USERNAME usuario de Buttondown. Vacío = modo demo (los formularios no envían nada)."""
import json, os, shutil, html, pathlib, datetime, re, sys, math
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from currencies import CURRENCIES, CODES, BASES, PAIRS, LATAM
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT, ASSETS = ROOT/"data", ROOT/"site", ROOT/"assets"
CFG = json.loads((ROOT/"config.json").read_text()) if (ROOT/"config.json").exists() else {}
def cfg(k, d=""): return os.environ.get(k, CFG.get(k, d))
SITE_URL = cfg("SITE_URL", "https://USUARIO.github.io/tiposcambio").rstrip("/")
BASE_PATH = "/" + cfg("BASE_PATH", "/").strip("/") + "/" if cfg("BASE_PATH", "/").strip("/") else "/"
NL_USER = cfg("NEWSLETTER_USERNAME", "").strip()
NAME = "TiposCambio"
TAGLINE = "El dólar y las monedas de Latinoamérica, hoy"

latest = json.loads((DATA/"latest.json").read_text())
hist = json.loads((DATA/"history.json").read_text())
arg = json.loads((DATA/"argentina.json").read_text()) if (DATA/"argentina.json").exists() else {"items": []}
news = json.loads((DATA/"news.json").read_text()) if (DATA/"news.json").exists() else {"items": []}
news["items"] = [n for n in news["items"] if n["source"].lower() not in ("facebook", "youtube", "tiktok", "instagram")]
e = lambda s: html.escape(str(s if s is not None else ""), quote=True)
CUR = {c[0]: c for c in CURRENCIES}
MESES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
def fecha(iso): y,m,d = iso[:10].split("-"); return f"{int(d)} {MESES[int(m)-1]} {y}"
def fecha_corta(iso): y,m,d = iso[:10].split("-"); return f"{int(d)} {MESES[int(m)-1]}"
R = latest["rates"]; CA = hist["currency_api"]; PS = hist["pairs"]
UPD = datetime.datetime.fromtimestamp(latest["updated_unix"], datetime.timezone.utc)
UPD_TXT = f"{fecha(UPD.date().isoformat())}, {UPD:%H:%M} UTC"
UPD_DATE = fecha(UPD.date().isoformat())
D1, D0 = CA["dates"][-1], CA["dates"][-2]
pages = []

def fmt(v, dec=None):
    """Número con formato es-419 (1,234.56)."""
    if v is None: return "—"
    if dec is None: dec = 2 if v >= 100 else (4 if v >= 1 else max(4, 3 - math.floor(math.log10(v))))
    return f"{v:,.{dec}f}"
def rate(b, q): return R[q] / R[b]
def series(b, q, n=None):
    xs = [(d, CA["rates"][q][i] / CA["rates"][b][i]) for i, d in enumerate(CA["dates"]) if CA["rates"][q][i] and CA["rates"][b][i]]
    return xs[-n:] if n else xs
def change(b, q):
    i1, i0 = CA["dates"].index(D1), CA["dates"].index(D0)
    a = CA["rates"][q][i0] / CA["rates"][b][i0]; z = CA["rates"][q][i1] / CA["rates"][b][i1]
    return (z / a - 1) * 100
def chg_html(p):
    cls = "flat" if abs(p) < 0.005 else ("up" if p > 0 else "dn"); ar = "→" if cls == "flat" else ("▲" if p > 0 else "▼")
    return f'<span class="chg {cls}">{ar} {abs(p):.2f}%</span>'
def spark(vals, w=110, h=30):
    lo, hi = min(vals), max(vals); rg = (hi - lo) or 1
    pts = " ".join(f"{i*(w/(len(vals)-1)):.1f},{h-2-(v-lo)/rg*(h-4):.1f}" for i, v in enumerate(vals))
    col = "var(--up)" if vals[-1] >= vals[0] else "var(--dn)"
    return f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true"><polyline fill="none" stroke="{col}" stroke-width="1.6" points="{pts}"/></svg>'
def chart_svg(dates, vals, W=800, H=300):
    """Gráfico estático (sin JS). app.js lo reemplaza por la versión interactiva."""
    L, Rr, T, B = 8, 64, 12, 26; lo, hi = min(vals), max(vals); pad = (hi - lo) * .08 or hi * .01; lo -= pad; hi += pad
    X = lambda i: L + i * (W - L - Rr) / max(1, len(vals) - 1); Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    line = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    grid = "".join(f'<line x1="{L}" x2="{W-Rr}" y1="{Y(lo+(hi-lo)*k/4):.1f}" y2="{Y(lo+(hi-lo)*k/4):.1f}"/>' for k in range(5))
    yl = "".join(f'<text x="{W-Rr+8}" y="{Y(lo+(hi-lo)*k/4)+4:.1f}">{fmt(lo+(hi-lo)*k/4)}</text>' for k in range(5))
    xl = "".join(f'<text x="{X(i):.1f}" y="{H-6}" text-anchor="{a}">{fecha_corta(dates[i])}</text>' for i, a in ((0, "start"), (len(vals)//2, "middle"), (len(vals)-1, "end")))
    return (f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="Gráfico de 30 días">'
            f'<defs><linearGradient id="g0" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#45d0ff" stop-opacity=".28"/><stop offset="1" stop-color="#45d0ff" stop-opacity="0"/></linearGradient></defs>'
            f'<g class="grid">{grid}</g><polygon fill="url(#g0)" points="{X(0):.1f},{H-B} {line} {X(len(vals)-1):.1f},{H-B}"/>'
            f'<polyline fill="none" stroke="#45d0ff" stroke-width="2" points="{line}"/><g class="axis">{yl}{xl}</g></svg>')

def nl_form(r, variant="hero", tag="web"):
    if NL_USER:
        attrs = f'action="https://buttondown.com/api/emails/embed-subscribe/{e(NL_USER)}" method="post"'
        hidden = f'<input type="hidden" name="embed" value="1"><input type="hidden" name="tag" value="{e(tag)}">'; demo = ""
    else:
        attrs = f'action="#" method="post" data-placeholder data-thanks="{r}gracias/index.html"'; hidden = ""
        demo = '<div class="demo-note">Modo demo: el formulario aún no está conectado (falta NEWSLETTER_USERNAME). No se guarda ningún correo.</div>'
    uid = f"em-{variant}"
    return (f'<form class="nl-form" {attrs}>{hidden}<label class="sr" for="{uid}">Tu correo</label>'
            f'<div class="capture"><input id="{uid}" type="email" name="email" required placeholder="tu@correo.com" autocomplete="email">'
            f'<button class="btn pri" type="submit">Únete gratis →</button></div>'
            f'<div class="capture-note"><span>1 correo por semana</span><span>Sin spam</span><span>Te das de baja con un clic</span></div>{demo}</form>')

def cur_options(sel, codes=CODES):
    return "".join(f'<option value="{c}"{" selected" if c==sel else ""}>{c} · {e(CUR[c][1])}</option>' for c in codes)
def sponsor_slot(r, where):
    return (f'<aside class="sponsor" aria-label="Espacio publicitario"><span><b>Patrocinio</b>Espacio disponible · {e(where)}</span>'
            f'<a class="btn sec sm" href="{r}anunciate/index.html">Anúnciate aquí</a></aside>')
DISCLAIMER = ("Tipos de cambio <b>informativos y de referencia</b> (promedio de mercado publicado por cada fuente, actualizado una vez al día). "
              "No sirven para operar: los bancos, casas de cambio, apps y tarjetas aplican su propio precio de compra y venta, comisiones e impuestos. "
              "En la tabla, ARS y VES son el tipo oficial; los dólares blue, MEP, CCL, cripto y tarjeta de Argentina están en su propio bloque (DolarAPI).")
def disc(r): return f'<p class="disc"><span>{DISCLAIMER} <a href="{r}metodologia/index.html">Cómo calculamos</a>.</span></p>'

def status_line():
    return (f'<span class="status snap" data-status><i></i><span data-status-txt>Actualizado {e(UPD_TXT)} · {e(latest["source_name"])}</span></span>')

def converter(r, b="USD", q="MXN", amount=1000, uid="cv"):
    v = amount * rate(b, q)
    return f"""<div class="conv" id="conversor" data-conv data-from="{b}" data-to="{q}">
<div class="conv-head"><h2>Conversor de divisas</h2>{status_line()}</div>
<form class="conv-grid" onsubmit="return false">
<label class="amt" for="{uid}-a">Monto<input id="{uid}-a" type="number" inputmode="decimal" min="0" step="any" value="{amount}" data-amount></label>
<label for="{uid}-f">De<select id="{uid}-f" data-from-sel>{cur_options(b)}</select></label>
<button class="swap" type="button" data-swap aria-label="Intercambiar monedas" title="Intercambiar">⇄</button>
<label for="{uid}-t">A<select id="{uid}-t" data-to-sel>{cur_options(q)}</select></label>
</form>
<div class="conv-out" aria-live="polite"><div class="from" data-out-from>{fmt(amount,0)} {b} =</div>
<div class="to" data-out-to><b>{fmt(v)}</b> {q}</div>
<div class="inv" data-out-inv>1 {b} = {fmt(rate(b,q))} {q} · 1 {q} = {fmt(rate(q,b))} {b}</div></div>
<div class="conv-foot"><span>Tipo de cambio medio de referencia. Tu banco te cobrará otro precio.</span></div></div>"""

def table_rows(b="USD"):
    out = []
    pairs_slug = {(pb, pq): s for pb, pq, s, _ in PAIRS}
    for c in CODES:
        code, name, country, sym = CUR[c]
        if c == b: continue
        v = rate(b, c); sp = [x[1] for x in series(b, c, 8)]
        slug = pairs_slug.get((b, c)) or pairs_slug.get((c, b))
        link = f'<a class="pairlink" href="{slug}/index.html">Ver {b}/{c} →</a>' if slug else ""
        out.append(f'<tr data-code="{c}" data-name="{e(name)}" data-rate="{v}" data-chg="{change(b,c):.4f}">'
                   f'<td class="c-cur"><div class="ccell"><span class="mono-badge">{c}</span><div><span class="cname">{e(name)}</span><span class="ccountry">{e(country)}</span></div></div></td>'
                   f'<td class="c-rate num">{fmt(v)}</td><td class="c-inv inv">{fmt(1/v)}</td>'
                   f'<td class="c-chg">{chg_html(change(b,c))}</td><td class="c-spark">{spark(sp)}</td><td class="c-link">{link}</td></tr>')
    return "".join(out)

def chart_block(pairkeys, sel, r, title_id="h-hist", heading=True):
    p = PS[sel]; b, q = sel.split("-")
    tabs = "".join(f'<button class="tab" type="button" role="tab" data-pair="{k}" aria-selected="{"true" if k==sel else "false"}">{k.replace("-","/")}</button>' for k in pairkeys)
    vals = p["values"]; ch30 = (vals[-1] / vals[0] - 1) * 100
    head = f'<div class="sh"><div><h2 id="{title_id}">Histórico de 30 días</h2><p>Cierres diarios reales. Pasa el cursor (o el dedo) por el gráfico para ver cada día.</p></div></div>' if heading else ""
    return f"""{head}<div class="chart-card" data-chart data-sel="{sel}">
<div class="tabs" role="tablist" aria-label="Par de monedas">{tabs if len(pairkeys)>1 else ""}</div>
<div class="chart-top"><div><div class="lbl" data-c-title>1 {b} en {q} · {e(CUR[b][1])} → {e(CUR[q][1])}</div><div class="now" data-c-now>{fmt(vals[-1])}</div></div>
<div class="tabs" role="group" aria-label="Rango"><button class="tab" type="button" data-range="7" aria-selected="false">7 días</button><button class="tab" type="button" data-range="30" aria-selected="true">30 días</button></div></div>
<div class="chart" data-c-svg>{chart_svg(p["dates"], vals)}<div class="tip"></div></div>
<div class="stats"><div class="stat"><span>Mínimo</span><b data-c-min>{fmt(min(vals))}</b></div><div class="stat"><span>Máximo</span><b data-c-max>{fmt(max(vals))}</b></div>
<div class="stat"><span>Promedio</span><b data-c-avg>{fmt(sum(vals)/len(vals))}</b></div><div class="stat"><span>Variación</span><b data-c-chg class="{"up" if ch30>=0 else "dn"}">{"+" if ch30>=0 else ""}{ch30:.2f}%</b></div></div>
<p class="fine" data-c-src>Fuente: <a href="{e(p["source_url"])}" rel="nofollow noopener" target="_blank">{e(p["source"])}</a> · {fecha(p["dates"][0])} → {fecha(p["dates"][-1])}{" · solo días hábiles" if "Frankfurter" in p["source"] else ""}</p></div>"""

def ar_block(r, heading=True):
    if not arg["items"]: return ""
    def hm(iso):
        t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")); return f"{fecha_corta(iso)} {t:%H:%M} UTC"
    cards = "".join(f'<div class="pcard" data-ar="{e(x["casa"])}"><span class="pp"><span>Dólar {e(x["nombre"])}</span></span>'
                    f'<span class="rate" data-ar-v>AR$ {fmt(x["venta"],2)}</span><span class="nm">Venta · compra <span data-ar-c>AR$ {fmt(x["compra"],2)}</span></span>'
                    f'<span class="nm dim xs mono" data-ar-t>{hm(x["actualizado"])}</span></div>' for x in arg["items"])
    off = next((x for x in arg["items"] if x["casa"] == "oficial"), None); blue = next((x for x in arg["items"] if x["casa"] == "blue"), None)
    gap = f' La brecha entre el blue y el oficial (venta) es de <b data-ar-gap>{(blue["venta"]/off["venta"]-1)*100:.1f}%</b>.' if off and blue else ""
    head = f'<div class="sh"><div><h2 id="h-ar">Dólar en Argentina: oficial, blue, MEP, CCL y más</h2><p>Precios de compra y venta en pesos argentinos.{gap}</p></div><span class="status snap" data-ar-status><i></i><span>Copia del {fecha(arg["fetched_utc"])}</span></span></div>' if heading else ""
    return (f'<section id="argentina" aria-labelledby="h-ar">{head}<div class="pcards" data-ar-block>{cards}</div>'
            f'<p class="fine">Fuente: <a href="https://dolarapi.com" rel="nofollow noopener" target="_blank">DolarAPI</a> (agrega cotizaciones publicadas de cada mercado). Cada tarjeta muestra la hora de su última actualización. Informativo: no es una oferta de compra ni venta.</p></section>')

def news_list(items, n):
    li = "".join(f'<li><a href="{e(x["link"])}" rel="nofollow noopener" target="_blank">{e(x["title"])}</a>'
                 f'<div class="meta"><b>{e(x["source"])}</b><time datetime="{e(x["date"])}">{fecha(x["date"])}</time></div></li>' for x in items[:n])
    return f'<ul class="news">{li}</ul>' if li else '<p class="dim">No hay titulares recientes en este momento.</p>'

# datos para app.js (todo real, redondeado a 6 cifras significativas)
def sig(v): return float(f"{v:.6g}") if v else None
TC = {"cur": [list(c) for c in CURRENCIES], "bases": BASES,
      "latest": {k: latest[k] for k in ("source", "source_name", "updated_unix", "next_update_unix")} | {"rates": {k: sig(v) for k, v in R.items()}},
      "hist": {"dates": CA["dates"], "rates": {k: [sig(x) for x in v] for k, v in CA["rates"].items()}},
      "pairs": PS, "ar": arg, "slugs": {f"{b}-{q}": s for b, q, s, _ in PAIRS}}

def layout(path, title, desc, body, kw="", active="", sticky=True):
    depth = path.count("/"); r = "../"*depth
    canon = re.sub(r"index\.html$", "", f"{SITE_URL}/{path}")
    nav = [("index.html#tabla","Tabla"),("index.html#conversor","Conversor"),("index.html#historico","Histórico"),("noticias/index.html","Noticias"),("metodologia/index.html","Metodología")]
    navh = "".join(f'<a href="{r}{h}"{" class=on aria-current=page" if h==active else ""}>{t}</a>' for h,t in nav)
    sticky_html = (f'<div class="sticky-cta" role="complementary" aria-label="Suscripción"><span class="txt">📬 <b>El resumen del dólar, cada lunes.</b> <span class="dim">Gratis.</span></span>'
                   f'<a class="btn pri sm" href="{r}suscribete/index.html">Únete</a><button class="x" type="button" aria-label="Cerrar">×</button></div>') if sticky else ""
    keywords = kw or "tipo de cambio, dólar hoy, precio del dólar, conversor de divisas, peso mexicano, peso argentino, peso colombiano, peso chileno, sol peruano, real, euro"
    pair_links = "".join(f'<li><a href="{r}{s}/index.html">{e(t)}</a></li>' for _, _, s, t in PAIRS[:6])
    doc = f"""<!doctype html><html lang="es-419"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><meta name="keywords" content="{e(keywords)}">
<link rel="canonical" href="{e(canon)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{NAME}"><meta property="og:locale" content="es_419">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canon)}"><meta property="og:image" content="{SITE_URL}/assets/og.png">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#08090b"><meta name="color-scheme" content="dark">
<link rel="preload" href="{r}assets/fonts/inter-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="icon" href="{r}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{r}assets/style.css">
</head><body>
<a class="skip" href="#main">Saltar al contenido</a>
<header class="top"><div class="wrap">
<a class="logo" href="{r}index.html" aria-label="{NAME}, inicio"><span class="mark">FX</span><span>Tipos<b>Cambio</b></span></a>
<nav class="main" aria-label="Principal">{navh}</nav>
<button class="btn sec sm menu-btn" type="button" aria-expanded="false" aria-label="Menú">☰</button>
<a class="btn pri sm" href="{r}suscribete/index.html">Únete a la lista</a>
</div></header>
<main id="main" class="wrap">{body}</main>
<footer><div class="wrap"><div class="fgrid">
<div><a class="logo" href="{r}index.html"><span class="mark">FX</span><span>Tipos<b>Cambio</b></span></a>
<p>{TAGLINE}. Tipos de cambio de referencia de fuentes públicas, con fecha y fuente. Información, no asesoría financiera.</p></div>
<div><h4>Pares populares</h4><ul>{pair_links}</ul></div>
<div><h4>Sitio</h4><ul><li><a href="{r}noticias/index.html">Noticias</a></li><li><a href="{r}metodologia/index.html">Metodología y fuentes</a></li><li><a href="{r}suscribete/index.html">Newsletter</a></li><li><a href="{r}anunciate/index.html">Anúnciate</a></li><li><a href="{r}data/latest.json">Datos abiertos (JSON)</a></li></ul></div>
<div><h4>El resumen del dólar, cada lunes</h4>{nl_form(r, "footer", "footer")}</div>
</div>
<div class="fbottom"><span>Datos: {e(latest["source_name"])} · currency-api · Frankfurter (BCE) · DolarAPI · Actualizado {e(UPD_TXT)}</span><span>Sin cookies de rastreo ni analíticas</span></div>
</div></footer>
{sticky_html}
<script>window.TC={json.dumps(TC, ensure_ascii=False, separators=(",",":"))};window.TC_ROOT="{r}";</script><script src="{r}assets/app.js" defer></script>
</body></html>"""
    p = OUT/path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(doc); pages.append(path)

if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir()
FEATURED = ["USD-MXN","USD-ARS","USD-COP","USD-CLP","USD-PEN","USD-BRL","EUR-USD","USD-UYU"]

def pcard(k, r=""):
    b, q = k.split("-"); slug = TC["slugs"][k]; pv = PS[k]["values"]
    return (f'<a class="pcard" href="{r}{slug}/index.html" data-pcard="{k}"><span class="pp"><span>{b}/{q}</span><span data-pc-chg>{chg_html(change(b,q))}</span></span>'
            f'<span class="rate" data-pc-rate>{fmt(rate(b,q))}</span><span class="nm">{e(CUR[b][1])} → {e(CUR[q][1])}</span>{spark(pv, 200, 38)}</a>')

# ---------- HOME ----------
home = f"""
<section class="hero fx" data-cta-trigger>
<div><div class="eyebrow"><i></i>Actualizado {e(UPD_DATE)} · {len(CODES)} monedas</div>
<h1>¿A cuánto está el dólar <span class="hl">hoy</span> en tu país?</h1>
<p class="lead">Tipos de cambio de referencia del dólar, el euro y {len(LATAM)} monedas latinoamericanas, con conversor, histórico de 30 días y las noticias que mueven el precio. Datos de fuentes públicas, con fecha y fuente.</p>
{nl_form("", "hero", "hero")}
</div>
{converter("")}
</section>
<div class="trust" aria-label="Resumen">
<span><b>{len(CODES)}</b>monedas</span><span class="sep"></span><span><b>{len(BASES)}</b>monedas base</span><span class="sep"></span><span><b>30</b>días de histórico</span><span class="sep"></span>
<span><b>4</b>fuentes de datos públicas</span><span class="sep"></span><span>Sin rastreo</span>
</div>
<section aria-labelledby="h-pares"><div class="sh"><div><h2 id="h-pares">Los pares más consultados</h2><p>Variación diaria entre los cierres del {fecha(D0)} y el {fecha(D1)} · línea: últimos 30 días.</p></div></div>
<div class="pcards">{"".join(pcard(k) for k in FEATURED)}</div></section>

{ar_block("")}
<section id="tabla" aria-labelledby="h-tabla">
<div class="sh"><div><h2 id="h-tabla">Tabla de tipos de cambio</h2><p>Cuánto vale 1 unidad de la moneda base en cada moneda. Haz clic en las columnas para ordenar.</p></div>{status_line()}</div>
<div class="controls">
<span class="cur-wrap"><label for="base">Moneda base</label><select id="base" data-base>{cur_options("USD", BASES)}</select></span>
<span class="search"><label class="sr" for="q">Buscar</label><input id="q" type="search" placeholder="Busca moneda o país…" data-q></span>
<span class="count" data-count>{len(CODES)-1} monedas</span></div>
<div class="tablewrap"><table id="rates"><thead><tr>
<th scope="col" data-sort="name">Moneda</th><th scope="col" class="r" data-sort="rate">1 <span data-base-lbl>USD</span> =</th><th scope="col" class="r">1 unidad = <span data-base-lbl>USD</span></th>
<th scope="col" class="c-chg" data-sort="chg">Var. diaria</th><th scope="col" class="r">7 días</th><th scope="col"><span class="sr">Detalle</span></th></tr></thead>
<tbody>{table_rows("USD")}</tbody></table></div>
<p class="fine">Tipo de cambio: <a href="{e(latest["source_url"])}" rel="nofollow noopener" target="_blank">{e(latest["source_name"])}</a> (respaldo: currency-api). Variación diaria y línea de 7 días: <a href="https://github.com/fawazahmed0/exchange-api" rel="nofollow noopener" target="_blank">currency-api</a>, cierres diarios.</p>
{disc("")}
{sponsor_slot("", "debajo de la tabla de tipos de cambio")}
</section>

<section id="historico" aria-labelledby="h-hist">{chart_block(FEATURED[:7], "USD-MXN", "")}</section>

<section class="cta-band" aria-labelledby="h-cta">
<div><h2 id="h-cta">El resumen del dólar en tu correo, cada lunes.</h2>
<p>Un correo corto con cómo cerró la semana tu moneda, los movimientos grandes y por qué pasaron.</p>
<ul><li>MXN, ARS, COP, CLP, PEN, BRL y UYU frente al dólar y el euro</li><li>Gráficos de la semana y titulares clave</li><li>Gratis y sin spam</li></ul></div>
<div>{nl_form("", "band", "band")}</div></section>

<section id="noticias" aria-labelledby="h-news"><div class="sh"><div><h2 id="h-news">Noticias de divisas y economía</h2><p>Titulares reales de medios de la región, vía Google News, Ámbito, Infobae e iProfesional. Enlazan a la nota original.</p></div>
<a class="btn sec sm" href="noticias/index.html">Ver todas →</a></div>{news_list(news["items"], 8)}</section>
"""
layout("index.html", f"Tipo de cambio hoy: dólar, euro y monedas de Latinoamérica | {NAME}",
       f"Dólar hoy en México, Argentina, Colombia, Chile, Perú, Brasil y Uruguay. Tabla de {len(CODES)} monedas, conversor de divisas, histórico de 30 días y noticias. Datos de referencia con fecha y fuente.", home, active="")

# ---------- PARES ----------
for b, q, slug, title in PAIRS:
    k = f"{b}-{q}"; v = rate(b, q); pv = PS[k]["values"]
    amts = [1, 5, 10, 20, 50, 100, 500, 1000]
    mag = 10 ** max(0, math.floor(math.log10(v))) if v >= 1 else 1
    ramts = [x * mag for x in (1, 5, 10, 50, 100, 500, 1000, 5000)]
    qt = lambda xs, f, t: "".join(f'<tr><td>{fmt(x,0)} {f}</td><td data-q="{x}" data-qf="{f}" data-qt="{t}">{fmt(x*rate(f,t))} {t}</td></tr>' for x in xs)
    note = ""
    if "ARS" in (b, q): note = '<p class="note">ARS: el conversor y el gráfico usan el tipo de cambio <b>oficial</b> de referencia. El blue, MEP, CCL, cripto y tarjeta están más abajo, en su propio bloque.</p>'
    others = "".join(pcard(x, "../") for x in FEATURED if x != k)[:0]
    rel = [x for x in FEATURED if x != k][:4]
    country = CUR[q][2] if b in ("USD","EUR") else CUR[b][2]
    body = f"""<div class="crumbs"><a href="../index.html">Inicio</a> / {b}/{q}</div>
<section class="hero fx" style="padding-top:28px" data-cta-trigger>
<div><div class="eyebrow"><i></i>Actualizado {e(UPD_DATE)}</div>
<h1>{e(title)} <span class="hl">hoy</span></h1>
<p class="lead">1 {e(CUR[b][1].lower() if b!="USD" else "dólar estadounidense")} ({b}) equivale a <b class="mono" data-pair-now="{k}">{fmt(v)}</b> {q} según el tipo de cambio medio de referencia. Abajo: conversor, histórico de 30 días y tabla rápida.</p>
<div class="stats" style="max-width:560px;grid-template-columns:repeat(3,1fr)"><div class="stat"><span>1 {b} =</span><b>{fmt(v)} {q}</b></div><div class="stat"><span>1 {q} =</span><b>{fmt(1/v)} {b}</b></div><div class="stat"><span>Var. diaria</span><b>{chg_html(change(b,q))}</b></div></div>
{note}
</div>
{converter("../", b, q, 100 if b!="USD" or v<100 else 100)}
</section>
{ar_block("../") if "ARS" in (b, q) else ""}
<section id="historico">{chart_block([k], k, "../")}</section>
<section class="grid g2" style="align-items:start">
<div class="card"><h3>{b} → {q}</h3><table class="qtable"><tbody>{qt(amts, b, q)}</tbody></table></div>
<div class="card"><h3>{q} → {b}</h3><table class="qtable"><tbody>{qt(ramts, q, b)}</tbody></table></div></section>
{disc("../")}
<section class="faq" style="margin-top:32px"><h2 style="margin-bottom:14px">Preguntas frecuentes</h2>
<details open><summary>¿A cuánto está el {e(title.split(" a ")[0].lower())} hoy en {e(country)}?</summary><p>Con datos del {e(UPD_TXT)}, 1 {b} = {fmt(v)} {q} (tipo de cambio medio de referencia de {e(latest["source_name"])}). La cifra se actualiza una vez al día.</p></details>
<details><summary>¿Por qué mi banco o casa de cambio me da otro precio?</summary><p>Este es un precio medio de mercado. Bancos, casas de cambio, apps y tarjetas cobran un margen entre compra y venta, comisiones e impuestos, así que siempre verás otra cifra al operar.</p></details>
<details><summary>¿De dónde salen los datos del gráfico?</summary><p>De {e(PS[k]["source"])}: un valor por día{", solo días hábiles" if "Frankfurter" in PS[k]["source"] else ""}. Más detalles en <a href="../metodologia/index.html">Metodología</a>.</p></details></section>
<section style="margin-top:40px"><div class="sh"><div><h2>Otros pares</h2></div></div><div class="pcards">{"".join(pcard(x, "../") for x in rel)}</div></section>
<section class="cta-band"><div><h2>¿Sigues el {b}/{q}?</h2><p>Cada lunes te mandamos cómo cerró la semana, con gráfico y titulares.</p></div><div>{nl_form("../", "pair", slug)}</div></section>"""
    layout(f"{slug}/index.html", f"{title} hoy: {fmt(v)} {q} por {b} ({UPD_DATE}) | {NAME}",
           f"{title} hoy: 1 {b} = {fmt(v)} {q}. Conversor {b}/{q}, histórico de 30 días, tabla rápida y variación diaria. Tipo de cambio de referencia con fecha y fuente.",
           body, kw=f"{title.lower()}, {b} {q}, {b}/{q}, tipo de cambio {CUR[q][1].lower()}, precio del {CUR[b][1].lower()} hoy, convertir {b} a {q}")

# ---------- NOTICIAS ----------
body = f"""<div class="page-hero"><span class="eyebrow"><i></i>Actualizado {fecha(news.get("generated_utc", D1))}</span><h1>Noticias de divisas y economía</h1>
<p class="lead">Titulares de los últimos 7 días sobre el dólar, el peso y las monedas de la región. Los recopilamos de Google News (búsquedas en español por país) y de los RSS de Economía de Ámbito, Infobae e iProfesional, y enlazamos a la nota original. No escribimos ni resumimos las notas.</p></div>
<section>{news_list(news["items"], 30)}</section>{sponsor_slot("../", "noticias")}
<section class="cta-band"><div><h2>Lo importante de la semana, en un correo.</h2><p>Sin ruido: cómo se movió tu moneda y por qué.</p></div><div>{nl_form("../", "news", "noticias")}</div></section>"""
layout("noticias/index.html", f"Noticias del dólar, divisas y economía en Latinoamérica | {NAME}",
       "Titulares recientes sobre el dólar, el peso mexicano, argentino, colombiano y chileno, el sol y el real, de medios de la región.", body, active="noticias/index.html")

# ---------- METODOLOGÍA ----------
pairsrc = "".join(f'<li><b>{k.replace("-","/")}</b>: {e(v["source"])}</li>' for k, v in PS.items())
body = f"""<div class="page-hero"><span class="eyebrow"><i></i>Transparencia</span><h1>Metodología y fuentes</h1>
<p class="lead">Qué datos mostramos, de dónde salen y cada cuánto se actualizan.</p></div>
<section class="grid g2" style="align-items:start">
<div class="card"><h3>Tipo de cambio del día</h3><p><a href="https://www.exchangerate-api.com/docs/free" rel="nofollow noopener" target="_blank">ExchangeRate-API (open.er-api.com)</a>, acceso abierto sin clave. Cubre las {len(CODES)} monedas, incluidas todas las latinoamericanas. Se actualiza una vez al día; mostramos la hora exacta que publica la fuente. Si falla, usamos <a href="https://github.com/fawazahmed0/exchange-api" rel="nofollow noopener" target="_blank">currency-api</a> y, si todo falla, la última copia guardada en el sitio.</p>
<p class="small dim">Última actualización de la fuente: {e(UPD_TXT)}.</p></div>
<div class="card"><h3>Variación diaria y líneas de 7 días</h3><p>Cierres diarios de <a href="https://github.com/fawazahmed0/exchange-api" rel="nofollow noopener" target="_blank">currency-api (fawazahmed0)</a>, que publica un archivo por fecha. Calculamos la variación entre los dos últimos cierres disponibles ({fecha(D0)} y {fecha(D1)}).</p></div>
<div class="card"><h3>Histórico de 30 días</h3><p>Para pares entre monedas que publica el Banco Central Europeo usamos <a href="https://frankfurter.dev" rel="nofollow noopener" target="_blank">Frankfurter</a> (días hábiles). El BCE no publica ARS, COP, CLP, PEN ni UYU, así que para esos usamos los cierres diarios de currency-api.</p><ul class="small mut">{pairsrc}</ul></div>
<div class="card"><h3>Dólar en Argentina</h3><p><a href="https://dolarapi.com" rel="nofollow noopener" target="_blank">DolarAPI</a> (código abierto, MIT): compra y venta del dólar oficial, blue, MEP, contado con liquidación, mayorista, cripto y tarjeta, cada uno con su hora de actualización. Se consulta en vivo desde tu navegador; si falla, mostramos la última copia guardada.</p></div>
<div class="card"><h3>Noticias</h3><p>Titulares de Google News RSS (búsquedas en español para México, Argentina, Colombia, Chile, Perú y la región) y de los RSS de Economía de Ámbito, Infobae e iProfesional. Mostramos título, medio, fecha y enlace a la nota original.</p></div></section>
{disc("../")}
<div class="card" style="margin-top:14px"><h3>Lo que no hacemos</h3><ul class="mut"><li>No mostramos precios de compra/venta de bancos ni casas de cambio.</li><li>No inventamos ni estimamos datos: si una fuente no publica un valor, no lo mostramos.</li><li>No usamos cookies de rastreo ni analíticas. Solo guardamos en tu navegador la última moneda que elegiste.</li></ul></div>"""
layout("metodologia/index.html", f"Metodología y fuentes de datos | {NAME}", "De dónde salen los tipos de cambio, el histórico y las noticias de TiposCambio, y cada cuánto se actualizan.", body, active="metodologia/index.html")

# ---------- ANÚNCIATE ----------
body = f"""<div class="page-hero"><span class="eyebrow"><i></i>Patrocinios</span><h1>Anúnciate en {NAME}</h1><p class="lead">Llega a personas de Latinoamérica justo cuando revisan el dólar o van a cambiar dinero: remesas, cuentas en dólares, tarjetas y apps de pago.</p></div>
<section class="grid g3"><div class="card"><span class="badge acc">Web</span><h3 style="margin-top:10px">Debajo de la tabla</h3><p class="small">Un espacio marcado como “Patrocinado” en la portada.</p></div>
<div class="card"><span class="badge acc">Newsletter</span><h3 style="margin-top:10px">Mención semanal</h3><p class="small">Un bloque patrocinado en el resumen del lunes.</p></div>
<div class="card"><span class="badge acc">Pares</span><h3 style="margin-top:10px">Páginas de cada par</h3><p class="small">Dólar a peso mexicano, argentino, colombiano y más.</p></div></section>
<p class="note">Todo anuncio va marcado como patrocinado y nunca cambia los datos. Publicaremos tarifas cuando tengamos datos reales de audiencia.</p>
<section class="card"><h2>Escríbenos</h2><form class="form" data-placeholder action="#" method="post" style="margin-top:14px">
<label>Empresa<input type="text" name="empresa" required></label><label>Correo<input type="email" name="email" required></label><label>¿Qué te interesa?<textarea name="msg" rows="4"></textarea></label>
<button class="btn pri" type="submit">Enviar</button><span class="todo">Pendiente: este formulario aún no envía nada.</span><span class="form-msg"></span></form></section>"""
layout("anunciate/index.html", f"Anúnciate en {NAME}", "Espacios de patrocinio, siempre marcados, en TiposCambio y su newsletter semanal sobre el dólar en Latinoamérica.", body)

# ---------- SUSCRIBETE / GRACIAS / CONFIRMADO ----------
body = f"""<section class="hero" style="grid-template-columns:1.1fr .9fr">
<div><span class="eyebrow"><i></i>Newsletter semanal · gratis</span>
<h1>El resumen del <span class="hl">dólar</span>, cada lunes.</h1>
<p class="lead">Cómo cerró la semana el dólar frente a tu moneda, los movimientos más grandes de la región y los titulares que los explican. En 3 minutos de lectura.</p>
{nl_form("../", "suscribete", "suscribete")}
<p class="dim xs" style="margin-top:14px">Te enviaremos un correo para confirmar la suscripción (doble opt-in). Solo usamos tu correo para mandarte el newsletter.</p></div>
<div class="card"><h3>Qué recibes cada semana</h3>
<ol class="steps"><li><div><b>Cierre semanal de tu moneda</b><div class="dim small">MXN, ARS, COP, CLP, PEN, BRL y UYU frente al dólar y el euro.</div></div></li>
<li><div><b>Los movimientos grandes</b><div class="dim small">Qué moneda subió o bajó más, con gráfico de 30 días.</div></div></li>
<li><div><b>Titulares que importan</b><div class="dim small">Lo que movió el precio, con enlace a la nota original.</div></div></li></ol></div></section>"""
layout("suscribete/index.html", f"Suscríbete: el resumen del dólar cada lunes | {NAME}", "Un correo por semana con cómo cerró el dólar frente al peso mexicano, argentino, colombiano, chileno, el sol y el real. Gratis.", body, sticky=False)
body = """<div class="page-hero center" style="max-width:640px"><div class="big-emoji" aria-hidden="true">📬</div>
<h1>Revisa tu correo para confirmar</h1><p class="lead center">Te acabamos de enviar un correo. Tu suscripción se activa cuando haces clic en el enlace de confirmación.</p>
<p class="demo-note" id="demo-flag" hidden>Modo demo: el formulario no está conectado, así que no se envió ningún correo.</p>
<ol class="steps" style="text-align:left"><li><div><b>Abre el correo de confirmación</b><div class="dim small">Llega en 1–2 minutos.</div></div></li>
<li><div><b>Haz clic en “Confirmar”</b><div class="dim small">Sin ese clic no te llegará nada (doble opt-in).</div></div></li>
<li><div><b>¿No llegó?</b><div class="dim small">Revisa spam y la pestaña Promociones, y agrega al remitente a tus contactos.</div></div></li></ol>
<a class="btn sec" href="../index.html">Volver a los tipos de cambio</a></div>
<script>if(/[?&]demo=1/.test(location.search))document.getElementById("demo-flag").hidden=false;</script>"""
layout("gracias/index.html", f"Revisa tu correo para confirmar | {NAME}", "Confirma tu suscripción al newsletter de TiposCambio desde el correo que te enviamos.", body, sticky=False)
body = f"""<div class="page-hero center" style="max-width:680px"><div class="big-emoji" aria-hidden="true">✅</div>
<h1>¡Listo, ya estás dentro!</h1><p class="lead center">Confirmaste tu suscripción. El próximo lunes te llega el resumen del dólar.</p>
<div class="grid g3" style="text-align:left;margin-top:24px">
<a class="hcard" href="../index.html#tabla"><span class="lbl">Ahora</span><h3>Tabla de monedas</h3><span class="dim small">{len(CODES)} monedas en tu base.</span></a>
<a class="hcard" href="../index.html#conversor"><span class="lbl">Rápido</span><h3>Conversor</h3><span class="dim small">Convierte cualquier monto.</span></a>
<a class="hcard" href="../noticias/index.html"><span class="lbl">Contexto</span><h3>Noticias</h3><span class="dim small">Lo que mueve el precio.</span></a></div></div>"""
layout("confirmado/index.html", f"Suscripción confirmada | {NAME}", "Tu suscripción al newsletter de TiposCambio está confirmada.", body, sticky=False)

# ---------- 404 ----------
p404 = (OUT/"index.html").read_text()
nf = '<div class="page-hero center"><div class="big-emoji">🔍</div><h1>Esta página no existe</h1><p class="lead center">Puede que el enlace esté mal o que la página se haya movido.</p><a class="btn pri" href="index.html">Ir a los tipos de cambio</a></div>'
p404 = re.sub(r'<main id="main" class="wrap">.*</main>', lambda m: f'<main id="main" class="wrap">{nf}</main>', p404, flags=re.S)
p404 = p404.replace('<head><meta charset="utf-8">', f'<head><meta charset="utf-8"><base href="{BASE_PATH}"><meta name="robots" content="noindex">', 1)
p404 = p404.replace('window.TC_ROOT="";', f'window.TC_ROOT="{BASE_PATH}";')
(OUT/"404.html").write_text(p404)

# ---------- assets, datos, sitemap ----------
shutil.copytree(ASSETS, OUT/"assets")
(OUT/"data").mkdir()
for f in ("latest.json", "history.json", "news.json", "argentina.json"):
    if (DATA/f).exists(): shutil.copy(DATA/f, OUT/"data"/f)
(OUT/".nojekyll").write_text("")
today = datetime.date.today().isoformat()
sm = "".join(f"<url><loc>{SITE_URL}/{re.sub(r'index[.]html$','',p)}</loc><lastmod>{today}</lastmod></url>" for p in pages)
(OUT/"sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
(OUT/"robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
print(f"Sitio generado en {OUT} — {len(pages)} páginas · datos {UPD_TXT} · newsletter: {'Buttondown/'+NL_USER if NL_USER else 'MODO DEMO'}")
