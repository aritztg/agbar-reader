"""Log in to the Aigües de Barcelona customer area with CloakBrowser.

`login()` is the reusable part: it drives the browser and hands back a token.
`main()` wraps it in a command line tool.
"""

import base64
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime

from cloakbrowser import launch_persistent_context
from dotenv import load_dotenv

URL = "https://www.aiguesdebarcelona.cat/es/area-clientes"
TOKEN_PATH = "ofex-login-api/auth/getToken"
CAPTCHA_PATH = "recaptcha/api2/payload"
PROFILE = os.path.expanduser(os.getenv("AGBAR_PROFILE", "~/.cache/agbar-reader/profile"))


@dataclass
class Token:
    """An access token and the epoch second it stops being valid."""

    value: str
    expires: float


class LoginError(Exception):
    """The login did not produce a token."""


class MaxSessionsReached(LoginError):
    """Too many logins in a row; the account has to sit idle for a while."""


class RecaptchaChallenge(LoginError):
    """Google put an image challenge in front of the login."""


def token_expiry(token):
    """Return the `exp` claim of a JWT, or an hour from now if it has none."""
    try:
        claims = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
        return float(claims["exp"])
    except (IndexError, ValueError, KeyError, TypeError):
        return time.time() + 3600


def read_token(context, body):
    """Take the token from the login response, or from the stored cookie."""
    value = body.get("access_token")
    if not value:
        cookie = next((c for c in context.cookies() if c["name"] == "ofexTokenJwt"), None)
        if not cookie:
            return None
        value = cookie["value"]
    return Token(value, token_expiry(value))


def login(nif, password, profile=PROFILE, headless=True, dismiss_cookies=False):
    """Drive the browser through the login and return a Token.

    A saved profile keeps the reCAPTCHA cookie between runs. Google scores a
    browser with no history much worse than one it has seen before, and a fresh
    profile every time is what got us the image grid.
    """
    os.makedirs(profile, exist_ok=True)
    browser = launch_persistent_context(
        profile, headless=headless, humanize=True, locale="es-ES", timezone="Europe/Madrid"
    )
    page = browser.pages[0] if browser.pages else browser.new_page()

    # The widget loads on every visit, but it only fetches api2/payload when it
    # decides to put an image grid in front of you.
    saw_captcha = False

    def note_captcha(request):
        nonlocal saw_captcha
        if CAPTCHA_PATH in request.url:
            saw_captcha = True

    page.on("request", note_captcha)

    try:
        page.goto(URL, wait_until="domcontentloaded")

        # Off by default: waiting for Cookiebot to show up costs up to 15 seconds and
        # the form is usually reachable anyway. Turn it on if the overlay gets in the
        # way and you see a "covered by <DIV>" error.
        if dismiss_cookies:
            try:
                page.click("#CybotCookiebotDialogBodyButtonDecline", timeout=15000)
                page.locator("#CybotCookiebotDialog").wait_for(state="hidden", timeout=10000)
            except Exception:
                pass

        # The profile may still hold a live session, in which case the app never
        # shows the form. The route tells that apart from a page that failed to load.
        try:
            page.wait_for_selector("#individual-password", timeout=20000)
        except Exception:
            if "#/login" in page.url:
                raise LoginError("the form never rendered")
            token = read_token(browser, {})
            if not token:
                raise LoginError("the session looked alive but carried no token")
            return token

        # Typed rather than filled. fill() sets the value through a CDP command,
        # which is one of the things reCAPTCHA watches for; press_sequentially
        # sends real key events instead.
        page.locator("#individual-user-id").press_sequentially(nif, delay=80)
        page.locator("#individual-password").press_sequentially(password, delay=80)
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

        if error == "MAX_SESSIONS_REACHED_ERROR":
            raise MaxSessionsReached(error)
        if error:
            raise LoginError(error)
        if saw_captcha:
            raise RecaptchaChallenge("reCAPTCHA challenge")

        # networkidle never fires here because the chat widget keeps polling. The
        # password field disappearing is what actually tells us we got in.
        try:
            page.wait_for_selector("#individual-password", state="hidden", timeout=30000)
        except Exception:
            pass

        if page.locator("#individual-password").is_visible():
            raise LoginError("still on the form")

        # getToken hands back the same JWT that the site stores in ofexTokenJwt,
        # without the httpOnly wrapper. That is what an API client needs.
        result = read_token(browser, body)
        if not result:
            raise LoginError("the login succeeded but handed back no token")
        return result
    finally:
        browser.close()


def main() -> int:
    # Pass the path explicitly. A bare load_dotenv() starts looking next to the
    # installed module, which under uvx is somewhere in site-packages.
    load_dotenv(".env")
    nif = os.getenv("AGBAR_NIF")
    password = os.getenv("AGBAR_PASSWORD")
    if not (nif and password):
        sys.exit("Set AGBAR_NIF and AGBAR_PASSWORD in the environment or in a .env file")

    try:
        token = login(
            nif,
            password,
            headless=os.getenv("AGBAR_HEADLESS", "1") != "0",
            dismiss_cookies=os.getenv("AGBAR_DISMISS_COOKIES", "0") != "0",
        )
    except MaxSessionsReached as err:
        print(f"login: FAILED ({err})")
        print("You have logged in too many times in a row. Wait a while and retry.")
        return 1
    except RecaptchaChallenge as err:
        print(f"login: FAILED ({err})")
        print("Google is asking for an image challenge, so the login never got sent.")
        print("Rerun with AGBAR_HEADLESS=0 and solve it by hand, or wait it out.")
        return 1
    except LoginError as err:
        print(f"login: FAILED ({err})")
        return 1

    print("login: OK")
    print(f"token: {token.value}")
    print(f"expires: {datetime.fromtimestamp(token.expires):%Y-%m-%d %H:%M:%S}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
