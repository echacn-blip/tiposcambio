"""Monedas que sigue TiposCambio (código ISO, nombre, país/región, símbolo, banderas como texto)."""
CURRENCIES = [
    ("USD", "Dólar estadounidense", "Estados Unidos", "US$"),
    ("EUR", "Euro", "Zona euro", "€"),
    ("MXN", "Peso mexicano", "México", "MX$"),
    ("ARS", "Peso argentino", "Argentina", "AR$"),
    ("COP", "Peso colombiano", "Colombia", "COL$"),
    ("CLP", "Peso chileno", "Chile", "CLP$"),
    ("PEN", "Sol peruano", "Perú", "S/"),
    ("BRL", "Real brasileño", "Brasil", "R$"),
    ("UYU", "Peso uruguayo", "Uruguay", "$U"),
    ("BOB", "Boliviano", "Bolivia", "Bs"),
    ("PYG", "Guaraní", "Paraguay", "₲"),
    ("VES", "Bolívar", "Venezuela", "Bs.D"),
    ("DOP", "Peso dominicano", "República Dominicana", "RD$"),
    ("GTQ", "Quetzal", "Guatemala", "Q"),
    ("CRC", "Colón costarricense", "Costa Rica", "₡"),
    ("HNL", "Lempira", "Honduras", "L"),
    ("NIO", "Córdoba", "Nicaragua", "C$"),
    ("GBP", "Libra esterlina", "Reino Unido", "£"),
    ("JPY", "Yen japonés", "Japón", "¥"),
    ("CHF", "Franco suizo", "Suiza", "CHF"),
    ("CAD", "Dólar canadiense", "Canadá", "CA$"),
    ("AUD", "Dólar australiano", "Australia", "A$"),
    ("CNY", "Yuan chino", "China", "CN¥"),
    ("KRW", "Won surcoreano", "Corea del Sur", "₩"),
    ("INR", "Rupia india", "India", "₹"),
]
CODES = [c[0] for c in CURRENCIES]
LATAM = {"MXN","ARS","COP","CLP","PEN","BRL","UYU","BOB","PYG","VES","DOP","GTQ","CRC","HNL","NIO"}
# Monedas publicadas por el BCE (Frankfurter). Las demás usan currency-api (fawazahmed0).
ECB = {"USD","EUR","MXN","BRL","GBP","JPY","CHF","CAD","AUD","CNY","KRW","INR"}
BASES = ["USD","EUR","MXN","ARS","COP","CLP","PEN","BRL","UYU","GBP"]
# Pares destacados: (base, cotizada, slug de página, título corto)
PAIRS = [
    ("USD","MXN","dolar-peso-mexicano","Dólar a peso mexicano"),
    ("USD","ARS","dolar-peso-argentino","Dólar a peso argentino"),
    ("USD","COP","dolar-peso-colombiano","Dólar a peso colombiano"),
    ("USD","CLP","dolar-peso-chileno","Dólar a peso chileno"),
    ("USD","PEN","dolar-sol-peruano","Dólar a sol peruano"),
    ("USD","BRL","dolar-real-brasileno","Dólar a real brasileño"),
    ("EUR","USD","euro-dolar","Euro a dólar"),
    ("USD","UYU","dolar-peso-uruguayo","Dólar a peso uruguayo"),
    ("EUR","MXN","euro-peso-mexicano","Euro a peso mexicano"),
]
