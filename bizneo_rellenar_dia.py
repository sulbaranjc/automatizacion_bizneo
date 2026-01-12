from playwright.sync_api import sync_playwright, expect

URL = "https://ilerna.bizneohr.com/time-attendance/my-logs/18043648"

FECHA = "2026-01-08"

# Tramo 1
TRAMO_1_ENTRADA = "13:35"
TRAMO_1_SALIDA = "14:30"
TRAMO_1_COMENTARIO = "BBDD DAW1"

# Tramo 2
TRAMO_2_ENTRADA = "15:00"
TRAMO_2_SALIDA = "17:45"
TRAMO_2_COMENTARIO = "Leng. de Marca"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # 1. Abrir Bizneo (login manual)
    page.goto(URL)

    # 2. Esperar tabla
    page.wait_for_selector("tr[data-bulk-element]")

    # 3. Abrir día
    fila_dia = page.locator(f'tr[data-bulk-element="{FECHA}"]')
    expect(fila_dia).to_be_visible()
    fila_dia.click()

    # 4. Esperar form del día
    form = page.locator(f'tr#form-{FECHA} form')
    expect(form).to_be_visible()

    # ===== TRAMO 1 =====
    entrada_1 = form.locator('input[name$="[start_at]"]').nth(0)
    salida_1 = form.locator('input[name$="[end_at]"]').nth(0)
    comentario_1 = form.locator('input[name$="[comment]"]').nth(0)

    entrada_1.fill(TRAMO_1_ENTRADA)
    entrada_1.press("Tab")

    salida_1.fill(TRAMO_1_SALIDA)
    salida_1.press("Tab")

    comentario_1.fill(TRAMO_1_COMENTARIO)
    comentario_1.press("Tab")

    # ===== AÑADIR TRAMO =====
    boton_add = form.locator('button[name="add"]')
    boton_add.click()

    # Esperar a que aparezca el segundo tramo
    expect(form.locator('input[name$="[start_at]"]')).to_have_count(2)

    # ===== TRAMO 2 =====
    entrada_2 = form.locator('input[name$="[start_at]"]').nth(1)
    salida_2 = form.locator('input[name$="[end_at]"]').nth(1)
    comentario_2 = form.locator('input[name$="[comment]"]').nth(1)

    entrada_2.fill(TRAMO_2_ENTRADA)
    entrada_2.press("Tab")

    salida_2.fill(TRAMO_2_SALIDA)
    salida_2.press("Tab")

    comentario_2.fill(TRAMO_2_COMENTARIO)
    comentario_2.press("Tab")

    # ===== GUARDAR =====
    page.get_by_role("button", name="Guardar").click()

    page.wait_for_timeout(4000)
    browser.close()
