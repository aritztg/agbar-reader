# agbar-reader

Proof of concept. Logs in to the [Aigües de Barcelona](https://www.aiguesdebarcelona.cat/es/area-clientes)
customer area with [CloakBrowser](https://pypi.org/project/cloakbrowser/), a stealth Chromium build,
and saves a screenshot of the page it lands on. No reCAPTCHA challenge so far.

## Run it (uvx, no clone needed)

Write the credentials, then run:

```
echo 'AGBAR_NIF=your-nif-or-nie' > .env
echo 'AGBAR_PASSWORD=your-password' >> .env

uvx --from git+https://github.com/aritztg/agbar-reader agbar-reader
```

Environment variables work too if you would rather not keep a `.env` around:

```
AGBAR_NIF=... AGBAR_PASSWORD=... uvx --from git+https://github.com/aritztg/agbar-reader agbar-reader
```

It prints the resulting URL and `login: OK` or `login: FAILED`, and writes `after-login.png`
to the current directory. Exit code is 0 on success, 1 if it is still sitting on the form.

## Options

`AGBAR_HEADLESS=0` shows the browser window instead of running headless.

`AGBAR_DISMISS_COOKIES=1` rejects the Cookiebot banner before filling the form. It is off by
default because waiting for the banner to appear costs up to 15 seconds on every run. Turn it
on if the login fails with a "covered by \<DIV>" error.

## Do not run this in a loop

Logging in every few minutes gets the account blocked for an indeterminate stretch. The site
answers the login call with `MAX_SESSIONS_REACHED_ERROR`, which the script reads off the
`ofex-login-api/auth/getToken` response and passes on:

```
login: FAILED (MAX_SESSIONS_REACHED_ERROR)
You have logged in too many times in a row. Wait a while and retry.
```

There is nothing to do about it other than wait.

## What it does not do yet

Nothing beyond the login: no bills, no meter readings, no consumption data.
