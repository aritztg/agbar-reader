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

It runs headless by default. Set `AGBAR_HEADLESS=0` to watch the browser work.

It prints the resulting URL and `login: OK` or `login: FAILED`, and writes `after-login.png`
to the current directory. Exit code is 0 on success, 1 if it is still sitting on the form.

## What it does not do yet

Nothing beyond the login: no bills, no meter readings, no consumption data.
