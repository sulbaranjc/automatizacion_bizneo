from playwright.sync_api import sync_playwright, expect
from datetime import datetime, timedelta
import argparse

# =========================
# CONFIGURACIÓN
# =========================

URL = "https://ilerna.bizneohr.com/time-attendance/my-logs/18043648"

HORARIOS = {

    "lunes": [
        ("08:30", "09:25", "Python DAW2"),
        ("12:40", "13:35", "BBDD DAW1"),
        ("13:35", "14:30", "BBDD DAW1"),
        ("15:55", "16:50", "Acceso Datos"),
        ("16:50", "17:45", "Acceso Datos"),
        ("18:15", "19:10", "Prog. MultiM"),
        ("19:10", "20:05", "Prog. MultiM"),
        ("20:05", "21:00", "Prog. MultiM"),
    ],

    "martes": [
        ("08:30", "09:25", "BBDD DAW1"),
        ("09:25", "10:20", "BBDD DAW1"),
        ("10:20", "11:15", "Guardia"),
        ("11:45", "12:40", "FCT"),
        ("12:40", "13:35", "Python DAW2"),
        ("13:35", "14:30", "Python DAW2"),
    ],

    "miercoles": [
        ("15:00", "15:55", "Prog. MultiM"),
        ("15:55", "16:50", "Guardia"),
        ("16:50", "17:45", "Entornos DD"),
        ("18:15", "19:10", "Entornos DD"),
        ("19:10", "20:05", "CEO"),
        ("20:05", "21:00", "CEO"),
    ],

    "jueves": [
        ("12:40", "13:35", "BBDD DAW1"),
        ("13:35", "14:30", "BBDD DAW1"),
        ("15:00", "15:55", "Leng. de Marca"),
        ("15:55", "16:50", "Leng. de Marca"),
        ("16:50", "17:45", "Leng. de Marca"),
        ("18:15", "19:10", "Acceso Datos"),
        ("19:10", "20:05", "Acceso Datos"),
        ("20:05", "21:00", "Acceso Datos"),
    ],

    "viernes": [
        ("11:45", "12:40", "Despliegues"),
        ("12:40", "13:35", "Despliegues"),
        ("13:35", "14:30", "Despliegues"),
        ("18:15", "19:10", "Python DAM2"),
        ("19:10", "20:05", "Python DAM2"),
        ("20:05", "21:00", "Python DAM2"),
    ],
}

# =========================
# UTILIDADES
# =========================

def dia_semana(fecha: datetime) -> str:
    dias = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    return dias[fecha.weekday()]

# =========================
# SCRIPT PRINCIPAL
# =========================

# Configurar argumentos de línea de comandos
parser = argparse.ArgumentParser(description='Cargar horario en Bizneo para una fecha específica')
parser.add_argument(
    '--fecha',
    type=str,
    default=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    help='Fecha a procesar en formato AAAA-MM-DD (por defecto: día anterior)'
)
args = parser.parse_args()

FECHA = args.fecha
fecha_actual = datetime.strptime(FECHA, "%Y-%m-%d")
dia = dia_semana(fecha_actual)

if dia not in HORARIOS:
    print(f"⚠️  No hay horario configurado para {dia}")
    exit(1)

tramos = HORARIOS[dia]

print(f"Cargando {dia} {FECHA}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(permissions=[], geolocation=None)
    page = context.new_page()

    page.goto(URL)
    page.wait_for_selector("tr[data-bulk-element]")

    fila = page.locator(f'tr[data-bulk-element="{FECHA}"]')
    expect(fila).to_be_visible()
    fila.click()

    form = page.locator(f'tr#form-{FECHA} form')
    expect(form).to_be_visible()

    for i, (entrada, salida, comentario) in enumerate(tramos):

        if i > 0:
            form.locator('button[name="add"]').click()
            expect(
                form.locator('input[name$="[start_at]"]')
            ).to_have_count(i + 1)
            page.wait_for_timeout(300)

        start = form.locator('input[name$="[start_at]"]').nth(i)
        end = form.locator('input[name$="[end_at]"]').nth(i)
        comm = form.locator('input[name$="[comment]"]').nth(i)

        # 🔑 Sobrescritura REAL
        start.click()
        start.press("Control+A")
        start.type(entrada)
        start.blur()

        end.click()
        end.press("Control+A")
        end.type(salida)
        end.blur()

        comm.click()
        comm.fill(comentario)
        comm.blur()

        page.wait_for_timeout(1000)

    # Forzar validación final
    page.locator("body").click()
    page.wait_for_timeout(800)

    page.get_by_role("button", name="Guardar").click()
    page.wait_for_timeout(3000)

    browser.close()
# Para ejecutar:
# python bizneo_cargar_dia_por_fecha.py                    # Procesa el día anterior
# python bizneo_cargar_dia_por_fecha.py --fecha 2026-01-16  # Procesa una fecha específica
# jsulbaran@ilerna.com