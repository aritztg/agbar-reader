"""Proof of concept: log in to the Aigües de Barcelona customer area with CloakBrowser."""

import os
import sys

from cloakbrowser import launch
from dotenv import load_dotenv

URL = "https://www.aiguesdebarcelona.cat/es/area-clientes"
TOKEN_PATH = "ofex-login-api/auth/getToken"


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

    # The widget loads on every visit, but it only fetches api2/payload when it
    # decides to put an image grid in front of you.
    saw_captcha = False

    def note_captcha(request):
        nonlocal saw_captcha
        if "recaptcha/api2/payload" in request.url:
            saw_captcha = True

    page.on("request", note_captcha)

    try:
        page.goto(URL, wait_until="domcontentloaded")

        # Off by default: waiting for Cookiebot to show up costs up to 15 seconds and
        # the form is usually reachable anyway. Turn it on if the overlay gets in the
        # way and you see a "covered by <DIV>" error.
        if os.getenv("AGBAR_DISMISS_COOKIES", "0") != "0":
            try:
                page.click("#CybotCookiebotDialogBodyButtonDecline", timeout=15000)
                page.locator("#CybotCookiebotDialog").wait_for(state="hidden", timeout=10000)
            except Exception:
                pass

        page.fill("#individual-user-id", nif)
        page.fill("#individual-password", password)
        # The page has three "Entrar" buttons. Two of them belong to the hidden
        # "Empresas" tab, which is what .business marks. The site reports the real
        # verdict in the getToken response, not in the page, so read it there.
        try:
            with page.expect_response(lambda r: TOKEN_PATH in r.url, timeout=30000) as token:
                page.click(".box-button-login:not(.business) button.btn-primary")
            body = token.value.json()
        except Exception:
            body = {}
        error = None if body.get("result") else (body.get("errorCode") or body.get("errorMessage"))

        if not (error or saw_captcha):
            # networkidle never fires here because the chat widget keeps polling. The
            # password field disappearing is what actually tells us we got in.
            try:
                page.wait_for_selector("#individual-password", state="hidden", timeout=30000)
            except Exception:
                pass

        page.screenshot(path="after-login.png", full_page=True)
        print(f"url: {page.url}")

        if error:
            print(f"login: FAILED ({error})")
            if error == "MAX_SESSIONS_REACHED_ERROR":
                print("You have logged in too many times in a row. Wait a while and retry.")
            return 1

        if saw_captcha:
            print("login: FAILED (reCAPTCHA challenge)")
            print("Google is asking for an image challenge, so the login never got sent.")
            print("Rerun with AGBAR_HEADLESS=0 and solve it by hand, or wait it out.")
            return 1

        logged_in = not page.locator("#individual-password").is_visible()
        print("login: OK" if logged_in else "login: FAILED (still on the form)")
        return 0 if logged_in else 1
    finally:
        browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
