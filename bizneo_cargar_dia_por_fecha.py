from playwright.sync_api import sync_playwright, expect
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# =========================
# CONFIGURACIÓN
# =========================

URL = "https://ilerna.bizneohr.com/time-attendance/my-logs/18043648"
SESSION_FILE = Path(__file__).parent / "session.json"

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
# ARGUMENTOS
# =========================

parser = argparse.ArgumentParser(description="Cargar horario en Bizneo para una fecha específica")
parser.add_argument(
    "--fecha",
    type=str,
    default=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    help="Fecha a procesar en formato YYYY-MM-DD (por defecto: día anterior)",
)
args = parser.parse_args()

FECHA = args.fecha
fecha_actual = datetime.strptime(FECHA, "%Y-%m-%d")
dia = dia_semana(fecha_actual)

if dia not in HORARIOS:
    print(f"⚠️  No hay horario configurado para {dia} ({FECHA})")
    exit(1)

tramos = HORARIOS[dia]
print(f"📅 Cargando {dia} {FECHA} ({len(tramos)} tramos)")

# =========================
# SCRIPT PRINCIPAL
# =========================

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    ctx_opts = {"permissions": [], "geolocation": None}
    if SESSION_FILE.exists():
        ctx_opts["storage_state"] = str(SESSION_FILE)
        print("🔑 Sesión guardada encontrada, intentando reutilizarla...")

    context = browser.new_context(**ctx_opts)
    page = context.new_page()

    page.goto(URL)

    # Comprobar si la sesión sigue activa (timeout corto intencionado)
    try:
        page.wait_for_selector("tr[data-bulk-element]", timeout=6_000)
        print("✅ Sesión activa.")
    except Exception:
        print("🔐 Sesión expirada o no encontrada.")
        print("   Inicia sesión con Google en el navegador. Tienes 3 minutos...")
        # Esperar a que el usuario complete el login y llegue a la página de asistencia
        page.wait_for_selector("tr[data-bulk-element]", timeout=180_000)
        context.storage_state(path=str(SESSION_FILE))
        print(f"💾 Sesión guardada en {SESSION_FILE}")

    # Localizar y expandir la fila del día
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
        end   = form.locator('input[name$="[end_at]"]').nth(i)
        comm  = form.locator('input[name$="[comment]"]').nth(i)

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

        page.wait_for_timeout(1_000)

    # Forzar validación y guardar
    page.locator("body").click()
    page.wait_for_timeout(800)

    page.get_by_role("button", name="Guardar").click()
    page.wait_for_timeout(3_000)

    browser.close()
    print(f"✅ {dia} {FECHA} cargado correctamente.")
