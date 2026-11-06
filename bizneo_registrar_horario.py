"""
Registra en Bizneo las horas trabajadas leyendo el horario esperado de cada día.

Por cada día laborable del rango:
  1. Lee los tramos esperados desde la propia fila de "Mis fichajes" (columna "Esperado").
  2. Crea UN tramo por turno, elige ese turno en el desplegable del tramo
     (así Bizneo no marca "Sobra tiempo") y escribe la hora de inicio y fin.
  3. Guarda y comprueba que el Balance del día queda en 00:00 y sin aviso "Sobra tiempo".

Por defecto SOLO SIMULA (no escribe nada). Usa --aplicar para guardar de verdad.
Nunca elimina registros: los días con horas pero sin horario esperado solo se avisan.

Ejemplos:
  biz-registrar --desde 2026-10-01 --hasta 2026-10-31            # simulación
  biz-registrar --desde 2026-10-01 --hasta 2026-10-31 --aplicar  # escribe
  biz-registrar --fecha 2026-11-06 --aplicar
"""
import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

BASE = "https://ilerna.bizneohr.com"
EMPLEADO = "18043648"
SESSION_FILE = Path(__file__).parent / "session.json"

TRAMO_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")
# Etiquetas del desplegable: "13:35 a 14:30", "8:30 a 21h", "08:30 - 14:30" o "20:05-21:00"
ETIQUETA_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(?:a|-)\s*(\d{1,2})(?::(\d{2}))?")


def hhmm(h, m):
    return f"{int(h):02d}:{int(m or 0):02d}"


def parse_tramos(texto):
    """'08:30-14:30 20:05-21:00' -> [('08:30','14:30'), ('20:05','21:00')]"""
    return [(hhmm(a, b), hhmm(c, d)) for a, b, c, d in TRAMO_RE.findall(texto)]


def clave_etiqueta(texto):
    m = ETIQUETA_RE.search(texto)
    return (hhmm(m.group(1), m.group(2)), hhmm(m.group(3), m.group(4))) if m else None


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fecha", help="un solo día (YYYY-MM-DD)")
    ap.add_argument("--desde", help="primer día del rango (YYYY-MM-DD)")
    ap.add_argument("--hasta", help="último día del rango (por defecto: ayer)")
    ap.add_argument("--aplicar", action="store_true", help="guardar de verdad (sin esto solo simula)")
    a = ap.parse_args()
    ayer = date.today() - timedelta(days=1)
    if a.fecha:
        a.desde = a.hasta = a.fecha
    desde = datetime.strptime(a.desde, "%Y-%m-%d").date() if a.desde else ayer
    hasta = datetime.strptime(a.hasta, "%Y-%m-%d").date() if a.hasta else ayer
    return desde, hasta, a.aplicar


def asegurar_sesion(p):
    """Abre el navegador con la sesión guardada; si caducó, espera al login manual."""
    browser = p.chromium.launch(headless=False)
    opts = {"storage_state": str(SESSION_FILE)} if SESSION_FILE.exists() else {}
    ctx = browser.new_context(**opts)
    page = ctx.new_page()
    page.goto(f"{BASE}/time-attendance/my-logs/{EMPLEADO}")
    try:
        page.wait_for_selector("tr[data-bulk-element]", timeout=6000)
    except PWTimeout:
        print("Sesión caducada: inicia sesión con Google en la ventana (hasta 3 minutos)...")
        page.wait_for_selector("tr[data-bulk-element]", timeout=180_000)
    ctx.storage_state(path=str(SESSION_FILE))
    return browser, page


def ir_a_mes(page, d):
    page.goto(f"{BASE}/time-attendance/my-logs/{EMPLEADO}?month={d.month}&year={d.year}")
    page.wait_for_selector("tr[data-bulk-element]")


def leer_fila(page, fecha):
    """Devuelve los datos de la fila del día leyendo sus celdas."""
    return page.locator(f'tr[data-bulk-element="{fecha}"]').evaluate(
        """r => {
            const t = e => e ? e.innerText.replace(/\\s+/g, ' ').trim() : '';
            const c = [...r.children];
            return {horario: t(c[2]), esperado: t(c[3]), registrado: t(c[4]),
                    total: t(c[5]), balance: t(c[6]),
                    sobra: !!r.querySelector('.huge-stop-watch-stroke-rounded')};
        }"""
    )


def escribir_hora(form, campo, i, valor):
    """Escribe 'HH:MM' en las dos cajas numéricas (hora y minutos) del tramo i.

    campo es "start" o "end". El input de texto con name="...[start_at]" es solo un
    respaldo oculto que el widget rellena: escribir ahí no sirve en los tramos nuevos.
    """
    cajas = form.locator(f"div.{campo}").nth(i).locator('.timepicker input[type="number"]')
    for caja, v in zip((cajas.nth(0), cajas.nth(1)), valor.split(":")):
        caja.click()
        caja.press("Control+A")
        caja.type(v)
        caja.press("Tab")


def rellenar_dia(page, fecha, tramos):
    """Abre el día, deja un tramo por turno con su turno elegido y guarda."""
    page.locator(f'tr[data-bulk-element="{fecha}"]').click()
    form = page.locator(f"tr#form-{fecha} form")
    form.wait_for()
    starts = form.locator('input[name$="[start_at]"]')
    if starts.count() > len(tramos):
        raise RuntimeError(f"hay {starts.count()} tramos y solo {len(tramos)} turnos: revisar a mano")

    for i, (ini, fin) in enumerate(tramos):
        if i >= starts.count():
            form.locator('button[name="add"]').click()
            page.wait_for_function(
                "([sel, n]) => document.querySelectorAll(sel).length === n",
                arg=[f'tr#form-{fecha} input[name$="[start_at]"]', i + 1],
            )
        # Los registros antiguos sin turno asociado no muestran el desplegable (solo un hidden vacío).
        select = form.locator(f'select[name="logged_time[logged_hours][{i}][shift_id]"]')
        if select.count():
            opciones = select.evaluate("s => [...s.options].map(o => [o.value, o.textContent.trim()])")
            valor = next((v for v, txt in opciones if clave_etiqueta(txt) == (ini, fin)), None)
            if valor is None:
                raise RuntimeError(f"el turno {ini}-{fin} no está en el desplegable: {opciones}")
            select.select_option(value=valor)
            page.wait_for_timeout(1000)  # elegir turno reescribe las horas del tramo: esperar antes de teclear
        else:
            print(f"           (tramo {i + 1} sin desplegable de turno: solo se escriben las horas)")
        escribir_hora(form, "start", i, ini)
        escribir_hora(form, "end", i, fin)

    # Comprobación antes de guardar: el respaldo oculto debe tener lo que queríamos
    for i, (ini, fin) in enumerate(tramos):
        for campo, esperado in (("start", ini), ("end", fin)):
            real = form.locator(f'input[name="logged_time[logged_hours][{i}][{campo}_at]"]').input_value()
            if real[:5] != esperado:
                raise RuntimeError(f"tramo {i + 1}: {campo} quedó en {real!r}, se quería {esperado}")
    form.get_by_role("button", name="Guardar").click()
    page.wait_for_timeout(3000)  # el formulario no siempre desaparece: se verifica recargando el mes


def main():
    desde, hasta, aplicar = parse_args()
    modo = "APLICAR (escribe en Bizneo)" if aplicar else "SIMULACIÓN (no escribe nada)"
    print(f"Rango {desde} → {hasta} · {modo}\n")
    resumen = {"ok": [], "saltado": [], "revisar": [], "error": []}

    with sync_playwright() as p:
        browser, page = asegurar_sesion(p)
        mes_actual = None
        d = desde
        while d <= hasta:
            fecha = d.isoformat()
            if (d.year, d.month) != mes_actual:
                ir_a_mes(page, d)
                mes_actual = (d.year, d.month)
            d += timedelta(days=1)

            fila = leer_fila(page, fecha)
            tramos = parse_tramos(fila["esperado"])
            if not tramos:
                if fila["registrado"] or fila["total"] not in ("", "0:00"):
                    print(f"{fecha}  REVISAR  sin horario esperado pero hay horas ({fila['total']}); no se toca")
                    resumen["revisar"].append(fecha)
                continue

            esperado = " ".join(f"{a}-{b}" for a, b in tramos)
            ya_bien = fila["balance"] == "00:00" and not fila["sobra"] and fila["registrado"].startswith(tramos[0][0]) \
                and fila["registrado"].endswith(tramos[-1][1])
            if ya_bien:
                print(f"{fecha}  = ya correcto ({esperado})")
                resumen["saltado"].append(fecha)
                continue

            print(f"{fecha}  → {esperado}   (ahora: {fila['registrado'] or 'vacío'}, balance {fila['balance'] or '-'})")
            if not aplicar:
                continue
            try:
                rellenar_dia(page, fecha, tramos)
                ir_a_mes(page, date.fromisoformat(fecha))
                despues = leer_fila(page, fecha)
                if despues["balance"] == "00:00" and not despues["sobra"]:
                    print(f"           ✔ guardado: {despues['registrado']} · balance 00:00")
                    resumen["ok"].append(fecha)
                else:
                    print(f"           ⚠ guardado pero revisar: balance {despues['balance']!r}, sobra={despues['sobra']}")
                    resumen["error"].append(fecha)
            except Exception as e:
                print(f"           ✘ error: {e}")
                resumen["error"].append(fecha)
                ir_a_mes(page, date.fromisoformat(fecha))  # recarga: descarta el formulario a medias

        browser.close()

    print("\nResumen:", {k: len(v) for k, v in resumen.items()})
    for k in ("revisar", "error"):
        if resumen[k]:
            print(f"  {k}: {', '.join(resumen[k])}")
    return 1 if resumen["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
