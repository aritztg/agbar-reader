# Agbar token

Logs in to Aigües de Barcelona with a real browser and hands the resulting token
to Home Assistant over the local network.

The login is guarded by a reCAPTCHA that the API checks against Google server
side, so only a browser on the site's own domain can produce a token that works.
Home Assistant OS runs its core on Alpine, where that browser cannot run: the
Chromium build needs glibc and Playwright publishes no musl wheel. This add-on
is a Debian container, so it can.

## Install

Add `https://github.com/aritztg/agbar-reader` as an add-on repository, install
"Agbar token" and start it. It builds on the image CloakBrowser publishes and
comes out around 2.5 GB, so check you have the space and give it several
minutes. It needs `amd64` or `aarch64`: there is no 32 bit build of the browser.

Then point the Aigues de Barcelona integration at it. The add-on writes its own
address to the log when it starts:

```
Listening on http://agbar-token:8099
```

Copy that into the integration's "token service" field. If the name does not
resolve, use the IP address of your Home Assistant machine with port 8099, which
the add-on maps to the host.

Nothing appears in the sidebar. This has no interface of its own.

## The first login may need you

A browser profile Google has never seen gets an image grid instead of a token,
and the add-on answers `503 reCAPTCHA challenge`. This is not a misconfiguration
and there is no setting that avoids it: measured against a public detector, the
browser scores the same here as it does on a laptop where the same login works,
and what separates them is that the laptop's profile has passed a challenge on
this site before.

So the first login may have to be solved by hand, once. After that the profile
in `/data` carries what Google wants to see, and the add-on renews on its own
for as long as that directory survives.

## The endpoint

```
POST /token
{"nif": "12345678Z", "password": "..."}

200 {"token": "ey...", "expires": 1757930000}
429 {"error": "MAX_SESSIONS_REACHED_ERROR"}
503 {"error": "reCAPTCHA challenge"}
502 {"error": "..."}
```

`expires` is the epoch second the token stops working, about an hour out.
`GET /health` answers `{"status": "ok"}`.

A login takes 20 to 40 seconds, so give the call a generous timeout. A token
already issued is handed back as long as it has more than five minutes left, and
only one login runs at a time.

## Why the profile is kept

reCAPTCHA scores the browser, not the account. One with no history scores badly,
and a throwaway profile on every login is what earns an image challenge. The
profile lives in `/data`, the only directory an add-on keeps across restarts and
updates.

## Logging in too often

Every login opens a session that nobody closes, and once they pile up the site
answers `MAX_SESSIONS_REACHED_ERROR` and stops accepting logins for a while. The
block follows the account rather than the machine, so a different IP does not
help and only waiting does. This add-on does not pace anything on its own beyond
reusing tokens it already issued. The integration is what decides how often to
ask.

## Who can call it

Anything on your Home Assistant network can reach the endpoint, and credentials
travel in plain HTTP. Both stay inside the internal Docker network, but do not
map the port anywhere it can be reached from outside the machine.
