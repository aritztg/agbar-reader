"""An HTTP front for the Aigües de Barcelona login.

Home Assistant OS runs its core on Alpine, where the stealth browser cannot run
at all: the Chromium build is linked against glibc and Playwright ships no musl
wheel. So the browser lives in this add-on instead, and the integration asks it
for a token over the internal network.
"""

import json
import logging
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer

from agbar_reader import login
from agbar_reader import LoginError
from agbar_reader import MaxSessionsReached
from agbar_reader import RecaptchaChallenge

PORT = int(os.getenv("AGBAR_PORT", "8099"))
# /data is the only directory an add-on keeps across restarts and updates. The
# profile has to live there: a browser with no history scores badly with
# reCAPTCHA, and a fresh one every time is what earns an image grid.
PROFILE = os.getenv("AGBAR_PROFILE", "/data/profile")

# Headed, on the virtual display the base image sets up. CloakBrowser is plain
# that aggressive sites detect headless even through its patches.
HEADLESS = os.getenv("AGBAR_HEADLESS", "0") != "0"

# One browser and one profile, so one login at a time. Two at once would fight
# over the same directory.
LOCK = threading.Lock()

# A token already issued is worth handing out again. Logging in a second time
# for the same account only opens another session that nobody closes.
CACHE = {}
CACHE_MARGIN = 300

MAX_BODY = 4096

_LOGGER = logging.getLogger("agbar-token")


def cached(nif):
    """Return a token issued earlier that is still comfortably valid."""
    token = CACHE.get(nif)
    if token and time.time() + CACHE_MARGIN < token.expires:
        return token
    return None


def issue(nif, password):
    """Return a token for this account, logging in only when needed."""
    with LOCK:
        # Checked again inside the lock: a request that queued behind a login
        # for the same account can use what that login just produced.
        token = cached(nif)
        if token:
            _LOGGER.info("Reusing the token issued earlier, valid until %s", token.expires)
            return token

        _LOGGER.info("Logging in")
        token = login(nif, password, profile=PROFILE, headless=HEADLESS)
        CACHE[nif] = token
        _LOGGER.info("Got a token valid until %s", token.expires)
        return token


class Handler(BaseHTTPRequestHandler):
    server_version = "agbar-token"

    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/health"):
            self.reply(200, {"status": "ok"})
            return
        self.reply(404, {"error": "unknown path"})

    def do_POST(self):
        if self.path.rstrip("/") != "/token":
            self.reply(404, {"error": "unknown path"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self.reply(413, {"error": "body too large"})
            return

        try:
            request = json.loads(self.rfile.read(length) or b"{}")
            nif = request["nif"]
            password = request["password"]
        except (ValueError, KeyError, TypeError):
            self.reply(400, {"error": "send a JSON body with nif and password"})
            return

        try:
            token = issue(nif, password)
        except MaxSessionsReached as err:
            # The block follows the account, not this machine, and only clears
            # by waiting. The caller is expected to back off for hours.
            _LOGGER.warning("Account has too many open sessions: %s", err)
            self.reply(429, {"error": str(err)})
        except RecaptchaChallenge as err:
            _LOGGER.warning("Stopped by a reCAPTCHA challenge: %s", err)
            self.reply(503, {"error": str(err)})
        except LoginError as err:
            _LOGGER.warning("Login failed: %s", err)
            self.reply(502, {"error": str(err)})
        except Exception as err:  # noqa: BLE001 - the browser can fail in many ways
            _LOGGER.exception("The browser did not produce a token")
            self.reply(500, {"error": str(err)})
        else:
            self.reply(200, {"token": token.value, "expires": token.expires})

    def log_message(self, fmt, *args):
        # The default writes to stderr and never reaches the add-on log.
        _LOGGER.info("%s %s", self.address_string(), fmt % args)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    os.makedirs(PROFILE, exist_ok=True)
    # Printed so the URL to put in Home Assistant can be copied from the log
    # rather than guessed: the host name depends on how the add-on was added.
    _LOGGER.info("Listening on http://%s:%s", socket.gethostname(), PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
