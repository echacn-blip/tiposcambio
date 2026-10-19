# TiposCambio

Sitio en español con los tipos de cambio del día para Latinoamérica: dólar frente al peso mexicano, argentino, colombiano, chileno y uruguayo, sol peruano y real brasileño, además del euro. Incluye noticias del mercado cambiario, una página de metodología y un boletín.

## Cómo funciona

- `scripts/refresh.py` descarga las cotizaciones y noticias y las guarda en `data/`.
- `scripts/build.py` genera el sitio estático en `site/`.
- La configuración (URL del sitio y boletín) está en `config.json`.

```bash
python3 scripts/refresh.py
python3 scripts/build.py
```

El sitio se publica con GitHub Pages desde la rama `gh-pages`.
