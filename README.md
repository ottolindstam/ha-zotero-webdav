# Zotero WebDAV for Home Assistant OS

An experimental, MIT-licensed add-on (now called an **app** in Home Assistant)
providing private WebDAV attachment storage. Uses Debian-supported lighttpd,
bcrypt authentication, and only its own persistent `/data` volume.

Supports `aarch64` (ARM64 Raspberry Pi) and `amd64`. No host networking, devices,
Supervisor API, Home Assistant API, shared-folder mappings, or privileged mode.
Home Assistant OS and Matter Server are not modified. The server runs as UID/GID
10001 after a short root initialization step. The network port is disabled by
default. See [installation and Zotero setup](zotero_webdav/DOCS.md),
[security review](docs/SECURITY.md), and [validation record](docs/VALIDATION.md).

## Development

Requires Docker with BuildKit and Python 3. Builds install signed Debian packages;
no Python packages or credentials are needed.

```sh
docker build --build-arg BUILD_ARCH=amd64 -t zotero-webdav:test zotero_webdav
python3 -m unittest discover -s tests -v
```

Tests create isolated Docker volumes, publish random **loopback-only** test ports,
and remove their containers and volumes. Never point tests at production data.
For ARM64, use a native ARM64 machine or an emulator-capable Buildx builder:

```sh
docker buildx build --platform linux/arm64 --build-arg BUILD_ARCH=aarch64 \
  --load -t zotero-webdav:arm64 zotero_webdav
TEST_IMAGE=zotero-webdav:arm64 python3 -m unittest discover -s tests -v
```

GitHub Actions builds and tests natively on AMD64 and ARM64. Native ARM runners
must be available to your repository/account. Workflows do not publish images.
On cloud hosts with a session CA, pass it as a BuildKit `proxy_ca` secret; it is
not copied into image layers. Keep TLS and package signature verification on.

This repository is installable directly as a Home Assistant app repository once
pushed to GitHub; Supervisor builds the image locally. There is no prebuilt image
requirement. Base tags and Debian repositories receive maintenance updates;
rebuild without cache to refresh packages, rerun both architectures, and bump the
app version before distributing an update. See `docs/REFERENCES.md` for sources.
