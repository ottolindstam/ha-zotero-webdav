# Security review — 0.1.0

## Scope and trust

Protect attachment confidentiality/integrity and isolate the app from unrelated
HA/Matter data. Trust HA OS, Supervisor, its administrators, Docker kernel
isolation, the selected image/package supply chain, and the operator's encrypted
transport. This is a source review with functional security checks, not a
penetration test or guarantee against server/kernel vulnerabilities.

## Controls

- Only automatic private `/data` storage; no `map`, devices, host namespace,
  Docker socket, Supervisor/Home Assistant/auth APIs, ingress, or capabilities
  requested. Protection mode and default AppArmor remain enabled.
- Startup is root only to read Supervisor-managed options, create/chown fixed
  directories, and write a private credential verifier. It clears supplementary
  groups, sets GID/UID 10001, removes unused Supervisor token environment entries,
  and execs lighttpd. Functional tests check effective UID and zero effective
  capabilities. The app requests Docker's init; that small init process may
  remain root while the server is unprivileged.
- Root-only `options.json`, traversable but unlistable `/data`, private managed
  directories (0700), umask 0077. No recursive chown on 6 GB every startup.
  SQLite state, plaintext options and runtime password hashes are outside the
  document root. Managed storage symlinks are rejected and lighttpd symlink
  following is disabled. HTTP tests probe traversal, symlinks, and private files.
- Global Basic authentication covers the entire document root and WebDAV methods.
  Username syntax prevents htpasswd/config injection. Password is passed to
  htpasswd via stdin, never command arguments, config templates or logs. The runtime directory and verifier remain root-owned; the server can read but
  cannot replace or modify the verifier, including across restarts. Only a
  cost-12 bcrypt hash is given to lighttpd; passwords exceeding bcrypt's 72-byte
  limit are rejected. No default usable password.
- Port mapping disabled; startup refuses default options until the operator
  confirms encryption. No TLS private keys or broad `/ssl` map in this app.
  Use the documented same-host TLS proxy. The acknowledgment does not enforce
  encryption or prove the route is secure.
- No shell interpolation of options or custom server config. No directory-listing
  HTML module, CGI, executable handlers, access logs, or arbitrary document root.
  WebDAV PROPFIND intentionally lists authenticated attachment names.
- Startup and lighttpd errors go to container logs. lighttpd can log attempted
  usernames, client IPs and request paths; it does not log Authorization headers
  or passwords in normal operation. Logs still deserve privacy protection.
- Upload request limit 1 GiB, 32 connections, idle timeouts. Large request spill
  files use SD-backed `/data/tmp` to avoid exhausting RAM on a Pi.

## Remaining limitations and operational risks

- Basic credentials and PDF contents are exposed on any unencrypted network hop.
  A port mapped to the host is not restricted to VPN interfaces by this app.
  Keep it disabled with a same-host TLS proxy; never expose it directly online.
- One shared identity, no per-user authorization, quotas, rate limiting, or login
  lockout. bcrypt and connection limits do not prevent network/CPU denial of
  service. Restrict access at the proxy/firewall. Concurrent clients are supported
  by WebDAV, but do not promise conflict-free simultaneous PDF editing.
- An authenticated client can read, overwrite or delete all attachments, upload
  arbitrary files, and fill the SD card. Storage is shared with HA OS at the disk
  level, so exhaustion or I/O load can affect HA and Matter despite container
  isolation. Monitor free space; sync in batches. No automatic pruning is used.
- Supervisor stores the application password in its options file. Hashing the
  server verifier does not encrypt that source, HA backups, or PDF storage.
  A host admin or root/kernel compromise defeats isolation. Protect backups and
  use full-disk/off-device security appropriate to your threat model.
- Default AppArmor has not been exercised on HA OS hardware. Startup has a small
  root phase and the default Docker capability set until UID drop. Dropping
  all capabilities externally prevents initialization; do not infer the entire
  container runs rootless. No privileged mode or extra capabilities are needed.
- No custom seccomp/AppArmor policy is shipped before hardware denial testing.
  Distribution packages include utilities used for initialization; this is not
  a distroless image. Depend on reviewed Debian updates and rebuild regularly.
- Builds fetch signed Debian package indexes/checksums. The base manifest digest
  is pinned; dependencies are intentionally refreshed from supported repositories.
  This is not byte-for-byte reproducible or independently vulnerability-audited.
- Cold backups and atomic WebDAV writes do not guarantee recovery after sudden
  power loss/SD failure. Keep tested off-device backups and reliable power.
- This initial release is experimental until the hardware acceptance checklist
  passes. No existing Home Assistant or Matter settings are altered by this repo.

Report suspected vulnerabilities privately to the repository maintainer through
GitHub's private vulnerability reporting when enabled; avoid public credentials
or attachment uploads. Rotate the WebDAV password after a suspected exposure.
