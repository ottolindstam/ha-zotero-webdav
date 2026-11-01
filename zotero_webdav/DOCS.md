# Installation and operation

## Before installing

1. In **Settings → System → Repairs → ⋮ → System information**, record the
   Raspberry Pi model, CPU architecture, Home Assistant OS and Supervisor versions.
   `ha info` / `ha os info` from an existing terminal is another read-only option.
   This release needs `aarch64` or `amd64`; a Pi running 32-bit HA OS is unsupported.
   Do not replace or reinstall HA OS to try this app.
2. Make a Home Assistant backup, download it off the Pi, and record Matter Server's
   running state. No changes to Matter, host networking, USB, or Bluetooth are needed.
3. Check actual free space in **Settings → System → Storage**. Allow at least the
   6 GB attachment corpus plus temporary uploads, container builds, and backups.
   A compressed backup of PDF/ZIP files can take roughly another 6 GB. The stated
   42 GB is an estimate, not a storage guarantee. Keep several GB free for HA and
   Matter; monitor usage during the initial sync. SD cards wear and fail.

## Install

1. Ensure this source is pushed to `https://github.com/ottolindstam/ha-zotero-webdav`.
2. Open **Settings → Apps** (called **Add-ons** on older releases), open its store,
   select **⋮ → Repositories**, and add that repository URL.
3. Refresh the store, select **Zotero WebDAV**, and install. Supervisor builds the
   image on the Pi. Keep Protection mode enabled. Leave automatic start disabled
   until acceptance tests pass.
4. Set a username matching `[A-Za-z0-9_.-]{1,64}` and a unique password of 16–72
   UTF-8 bytes. Newlines/NUL are rejected; bcrypt cannot safely accept >72 bytes.
   Default empty credentials deliberately prevent startup.
5. Configure the encrypted route below, then set
   `encrypted_transport_confirmed: true`. This is an operator acknowledgment;
   the app cannot verify an external proxy or VPN. A bare HTTP connection on an
   ordinary LAN does **not** qualify.

## Encrypted access (required)

Recommended: a TLS reverse proxy on the same HA OS host/container network. Leave
this app's `8080/tcp` host mapping disabled. A separately configured proxy connects
to the app's internal Docker DNS name on port 8080. Get the actual app identifier
from Supervisor/app information; internal names normally replace underscores
with hyphens (for example `<repository-prefix>-zotero-webdav`). Verify the actual
name from your proxy before use; the repository prefix is installation-specific.

For a separately installed Caddy proxy with valid certificates, this is the whole
site route (replace both placeholders):

```caddyfile
zotero.example.net {
    reverse_proxy http://<actual-app-dns-name>:8080
}
```

Use private/split DNS and firewall rules so only your LAN/VPN clients reach this
TLS site. Obtain certificates with DNS validation or an existing trusted internal
CA; trust the CA on every Zotero client. Never disable certificate validation.
Certificate storage belongs to the proxy; this app has no `/ssl` or other shared
mapping. Do not add another login page or browser-based SSO: Zotero needs the
WebDAV Basic authentication challenge. Preserve Authorization, request methods,
body, and URI; avoid stripping `/zotero/`. Allow upload bodies up to your largest
attachment and adequate timeouts. Disable proxy caching for this route.

A VPN is an alternative only when the entire client-to-endpoint route is
protected and HTTP cannot be reached from untrusted networks. Mapping port 8080
in HA's Network section can bind it to **all host interfaces**, not just a VPN.
You must enforce firewall/router access controls independently. A remote VPN
terminating at a router with an unencrypted LAN hop is not end-to-end protection;
use HTTPS in that case. This add-on does not install a VPN or change host rules.
No router port forwarding, UPnP, public tunnel, or public ingress is configured.

## Zotero

In Zotero desktop **Settings → Sync**:

1. Keep Zotero data sync configured with your Zotero account. This app stores
   personal-library attachment files only; it does not replace Zotero metadata sync.
2. Under File Syncing, choose **WebDAV** for My Library attachments.
3. Choose **HTTPS**, enter the proxy host/base path (for the example above,
   `zotero.example.net/`), and enter the app username and password.
   Zotero appends `zotero/` itself; do not append it twice. The app precreates it.
4. Click **Verify Server**, then sync a small disposable PDF. Verify it downloads
   on a second desktop client using the same account and WebDAV credentials.
5. Only after the acceptance checklist passes, sync the full library in batches.
   Avoid concurrent edits to the same attachment. WebDAV attachment sync for
   group libraries is not supported by Zotero; mobile support depends on the
   client, so verify it separately.

Files are stored under `/data/attachments/zotero` as Zotero-managed `.zip` and
`.prop` files, not a human-organized PDF directory. `/data/state` holds WebDAV
SQLite metadata; `/data/tmp` holds upload spill files. These survive app updates
and container recreation. Credentials in `/data/options.json` remain root-only;
a bcrypt cost-12 verifier is generated in `/run/zotero` at each startup.
All clients share one identity and namespace. Independent users/libraries are
not isolated; do not give these credentials to unrelated users.

## Backups and recovery

1. Pause sync on all Zotero clients. In HA's backup UI create a manual backup
   including **Zotero WebDAV** (full backup or select this app explicitly).
2. The manifest requests a **cold** backup: Supervisor stops this app for a
   consistent `/data` snapshot, including attachments and SQLite state. Confirm
   the backup completes and the app resumes. Verify this behavior on your HA OS
   version before relying on it.
3. Download the backup to a separate machine; keep any HA backup encryption key
   or emergency kit securely off-device. Backups may contain the plaintext app
   configuration password as well as private PDFs. Do not commit backup files.
4. Test restoring the app and its data on a spare/test HA OS system, verify a
   known attachment, then run Zotero Verify Server. Never test restore over the
   only copy of your library. Restart clients after checking data integrity.

Uninstalling the app can delete its private data. Back up before uninstalling;
restart and upgrade are not uninstall. WebDAV sync is not a backup: deletions can
propagate to every client. Keep independent Zotero library backups too.

## Troubleshooting

- Startup refused: verify username, password byte length, encrypted transport
  confirmation, and available storage. Logs deliberately omit option values.
- 401: check app credentials, proxy Authorization forwarding, and Zotero's saved
  credentials. Home Assistant login credentials are unrelated.
- Verify Server fails: check trusted HTTPS certificate, the base URL, and proxy
  handling of OPTIONS/PROPFIND/PUT/GET/DELETE. A missing `.prop` must return 404,
  not a proxy login page. `/zotero/` should return 207 to authenticated PROPFIND.
- 413/timeouts: proxy upload limits and timeouts may be smaller than the app's
  1 GiB request limit. The app permits 32 connections; start with one client.
- Disk full: stop sync, inspect HA storage and backups. Never delete `.prop` or
  `.zip` files blindly. Successful writes do not protect against SD-card failure.
- Cannot reach the service: port mapping is deliberately disabled. Check the
  proxy's internal DNS/backend or your explicitly configured encrypted network.
- Protection/AppArmor error: collect the denial and app logs for diagnosis;
  do not disable Protection mode or grant broad mappings as a workaround.
- Upgrade: back up, update this app only, run Verify Server, download an existing
  attachment, and check Matter Server still runs. No HA OS or Matter migration
  is part of this installation.
