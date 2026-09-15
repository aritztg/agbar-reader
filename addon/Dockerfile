# Chromium and the Python packages are fetched here and copied over, so pip, its
# build tooling and binutils never reach the final image.
FROM python:3.12-slim-bookworm AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installed from a source archive rather than copied in: an add-on builds with
# its own directory as the context, so the module one level up is out of reach.
# An archive rather than git+, because this base image ships no git.
RUN pip install --no-cache-dir "https://github.com/aritztg/agbar-reader/archive/refs/heads/main.tar.gz"

# Chromium is baked in. Left to the first request, this download would turn it
# into a several minute wait and time the caller out.
#
# The three trims that follow have to happen here, in the same layer that puts
# the files there. Deleting them later only hides them: the bytes stay in the
# layer underneath. Together they take the browser from 656 MB to 320 MB, and
# the browser still starts, renders and reports WebGL afterwards.
#   locales      656 files, 177 MB of translated strings for a form nobody reads
#   chromedriver 26 MB that Playwright never calls
#   strip        the shipped binary carries its symbol table, 408 MB down to 252
RUN cloakbrowser install \
 && apt-get update && apt-get install -y --no-install-recommends binutils \
 && cd /root/.cloakbrowser/chromium-*/ \
 && find locales -type f ! -name "es.pak*" ! -name "en-US.pak*" -delete \
 && rm -f chromedriver \
 && strip --strip-all chrome


# Debian on purpose. The stealth Chromium is linked against glibc, which is why
# it cannot run inside the Home Assistant core container, and why this add-on
# exists at all. Pinned to bookworm because trixie renamed libasound2.
FROM python:3.12-slim-bookworm

# What headless Chromium actually loads, plus the fonts CloakBrowser asks for.
# GTK, the X11 client libraries, xvfb and openbox that the CloakBrowser image
# installs are all for running with a visible window, and libgtk-3-0 alone drags
# in a long tail. Node is not here either: Playwright bundles its own.
#
# The fonts are not decoration. Anti-bot systems render emoji and text to a
# hidden canvas and compare the pixels, and a machine with almost no fonts
# produces a hash that matches no real browser.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      fonts-freefont-ttf \
      fonts-ipafont-gothic \
      fonts-liberation \
      fonts-noto-color-emoji \
      fonts-tlwg-loma-otf \
      fonts-unifont \
      fonts-urw-base35 \
      fonts-wqy-zenhei \
      libasound2 \
      libatk-bridge2.0-0 \
      libatk1.0-0 \
      libatspi2.0-0 \
      libcairo2 \
      libcups2 \
      libdbus-1-3 \
      libdrm2 \
      libfontconfig1 \
      libgbm1 \
      libglib2.0-0 \
      libnspr4 \
      libnss3 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libx11-6 \
      libxcb1 \
      libxcomposite1 \
      libxdamage1 \
      libxext6 \
      libxfixes3 \
      libxkbcommon0 \
      libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.cloakbrowser /root/.cloakbrowser
ENV PATH="/opt/venv/bin:$PATH"

COPY server.py /usr/src/server.py

EXPOSE 8099
CMD ["python", "/usr/src/server.py"]
