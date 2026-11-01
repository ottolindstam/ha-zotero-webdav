# syntax=docker/dockerfile:1
FROM debian:bookworm-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3
ARG BUILD_VERSION=0.1.0
ARG BUILD_ARCH
LABEL io.hass.type="app" io.hass.version="${BUILD_VERSION}" io.hass.arch="${BUILD_ARCH}" \
      org.opencontainers.image.source="https://github.com/ottolindstam/ha-zotero-webdav" \
      org.opencontainers.image.licenses="MIT"
# Optional session CA for cloud builders; never retained in image layers.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca; fi; \
    apt-get update && \
    apt-get install -y --no-install-recommends lighttpd lighttpd-mod-webdav apache2-utils python3 ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    install -d -m 0700 /run/zotero && \
    install -d -m 0755 /data /etc/zotero
COPY --chmod=0644 lighttpd.conf /etc/zotero/lighttpd.conf
COPY --chmod=0644 start.py /usr/local/bin/zotero-start
EXPOSE 8080
ENTRYPOINT ["python3", "/usr/local/bin/zotero-start"]
