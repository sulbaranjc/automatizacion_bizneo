from playwright.sync_api import sync_playwright, expect

URL = "https://ilerna.bizneohr.com/time-attendance/my-logs/18043648"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    # 1. Abrir Bizneo
    page.goto(URL)

    # 2. Esperar a que carguen los registros
    page.wait_for_selector("tr[data-bulk-element]")

    # 3. Localizar un día concreto (ejemplo: 8 de enero)
    dia = page.locator('tr[data-bulk-element="2026-01-08"]')
    expect(dia).to_be_visible()

    # 4. Desplegar el día (click en la flecha)
    dia.click()

    # Pausa visual para ver resultado
    page.wait_for_timeout(3000)

    browser.close()
