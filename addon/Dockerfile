# Debian on purpose. The stealth Chromium is linked against glibc, which is why
# it cannot run inside the Home Assistant core container, and why this add-on
# exists at all. Pinned to bookworm because trixie renamed libasound2.
FROM python:3.12-slim-bookworm

# Chromium's runtime libraries and enough fonts to render a login form. Taken
# from the CloakBrowser image, minus xvfb and openbox: this runs headless, so
# there is no virtual display to set up.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      fonts-liberation \
      fonts-noto-color-emoji \
      libasound2 \
      libatk-bridge2.0-0 \
      libatk1.0-0 \
      libatspi2.0-0 \
      libcairo-gobject2 \
      libcairo2 \
      libcups2 \
      libdbus-1-3 \
      libdrm2 \
      libfontconfig1 \
      libgbm1 \
      libgdk-pixbuf-2.0-0 \
      libglib2.0-0 \
      libgtk-3-0 \
      libnspr4 \
      libnss3 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libx11-6 \
      libx11-xcb1 \
      libxcb1 \
      libxcomposite1 \
      libxdamage1 \
      libxext6 \
      libxfixes3 \
      libxkbcommon0 \
      libxrandr2 \
      libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Installed from git rather than copied in: an add-on builds with its own
# directory as the context, so the module one level up is out of reach.
RUN pip install --no-cache-dir "agbar-reader @ git+https://github.com/aritztg/agbar-reader@main"

# Baked into the image. Left to the first request, this 350 MB download would
# turn that request into a several minute wait and time the caller out.
RUN cloakbrowser install

COPY server.py /usr/src/server.py

EXPOSE 8099
CMD ["python", "/usr/src/server.py"]
