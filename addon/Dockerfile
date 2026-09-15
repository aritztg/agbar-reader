# The image CloakBrowser publishes, pinned to the version this depends on. It
# carries the patched Chromium, every library and font they ask for, and the
# entrypoint that brings up Xvfb so the browser can run headed.
#
# Theirs rather than one assembled here. An earlier version of this file built
# the environment from scratch and trimmed it to 1.12 GB; the login failed just
# as often, so the trimming bought nothing and only added ways to be wrong.
FROM cloakhq/cloakbrowser:0.5.10

# The fonts Microsoft lets anyone have. The installer fetches them from
# Microsoft rather than redistributing them, which is why Debian keeps it in
# contrib and why running it here is fine. The proprietary set that CloakBrowser
# really wants (Segoe UI, Calibri, Marlett) cannot be shipped by anyone, theirs
# included, so that warning on startup stays whatever we do.
RUN echo "deb http://deb.debian.org/debian bookworm contrib" >> /etc/apt/sources.list \
 && echo ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true \
    | debconf-set-selections \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ttf-mscorefonts-installer \
 && rm -rf /var/lib/apt/lists/*

# From a source archive rather than git+, because the base image ships no git.
RUN pip install --no-cache-dir "https://github.com/aritztg/agbar-reader/archive/refs/heads/main.tar.gz"

COPY server.py /usr/src/server.py

EXPOSE 8099
CMD ["python", "/usr/src/server.py"]
