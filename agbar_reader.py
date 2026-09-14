"""Proof of concept: log in to the Aigües de Barcelona customer area with CloakBrowser."""

import os
import sys

from cloakbrowser import launch
from dotenv import load_dotenv

URL = "https://www.aiguesdebarcelona.cat/es/area-clientes"


def main() -> int:
    # Pass the path explicitly. A bare load_dotenv() starts looking next to the
    # installed module, which under uvx is somewhere in site-packages.
    load_dotenv(".env")
    nif = os.getenv("AGBAR_NIF")
    password = os.getenv("AGBAR_PASSWORD")
    if not (nif and password):
        sys.exit("Set AGBAR_NIF and AGBAR_PASSWORD in the environment or in a .env file")

    headless = os.getenv("AGBAR_HEADLESS", "1") != "0"
    browser = launch(headless=headless, humanize=True, locale="es-ES", timezone="Europe/Madrid")
    page = browser.new_page()
    try:
        page.goto(URL, wait_until="domcontentloaded")

        # Cookiebot loads late and covers the form. Rejecting clears it. Once the
        # cookie is stored the banner stops appearing, so on later runs this just
        # times out.
        try:
            page.click("#CybotCookiebotDialogBodyButtonDecline", timeout=15000)
            page.locator("#CybotCookiebotDialog").wait_for(state="hidden", timeout=10000)
        except Exception:
            pass

        page.fill("#individual-user-id", nif)
        page.fill("#individual-password", password)
        # The page has three "Entrar" buttons. Two of them belong to the hidden
        # "Empresas" tab, which is what .business marks.
        page.click(".box-button-login:not(.business) button.btn-primary")

        # networkidle never fires here because the chat widget keeps polling. The
        # password field disappearing is what actually tells us we got in.
        try:
            page.wait_for_selector("#individual-password", state="hidden", timeout=30000)
        except Exception:
            pass
        page.screenshot(path="after-login.png", full_page=True)

        logged_in = not page.locator("#individual-password").is_visible()
        print(f"url: {page.url}")
        print("login: OK" if logged_in else "login: FAILED (still on the form)")
        return 0 if logged_in else 1
    finally:
        browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
