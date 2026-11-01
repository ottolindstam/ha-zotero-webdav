# Sources checked during implementation

Reviewed 2026-11-01. Official Home Assistant documentation now uses “apps” for
add-ons. Specifications were read from the official source repository:

- [App configuration](https://developers.home-assistant.io/docs/apps/configuration/)
  ([source](https://github.com/home-assistant/developers.home-assistant/blob/50b518898989b67bb76b69827f227aa6f0acd32a/docs/apps/configuration.md)):
  `/data`, `options.json`, architecture labels, disabled port mappings, API flags,
  AppArmor, init handling, and cold backups. No HA-specific base image is required.
- [Repository format](https://developers.home-assistant.io/docs/apps/repository/)
  and [tutorial](https://developers.home-assistant.io/docs/apps/tutorial/).
- [Zotero's official WebDAV implementation](https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/storage/webdav.js):
  `_init` appends `zotero/`; `checkServer` checks DAV header, PROPFIND depth 0,
  missing `.prop` 404, and PUT/GET/DELETE of `zotero-test-file.prop`.
  The automated protocol check mirrors the existing-directory path, not the
  complete Zotero UI, authentication cache, or every recovery branch.
- [Zotero sync documentation](https://www.zotero.org/support/sync) is the user
  reference for personal-library WebDAV file sync versus metadata/group sync.
- [Reference add-on](https://github.com/ElVit/hassio-addons/tree/22f9c6ad7904516c6a9b275f14b2439ccf0fe84a/webdav):
  reviewed manifest, Dockerfile, initialization, and lighttpd templates.

The reference is not a runtime dependency and no source was copied. Its broad
filesystem mappings, Supervisor API access, enabled host port, symlink following,
and configurable document root are deliberately omitted. Its installed
apache2-utils approach informed the choice of a standard htpasswd backend;
this implementation explicitly selects bcrypt cost 12 and tests real login.

Debian's signed repositories provide the maintained distribution build of
lighttpd (including WebDAV and htpasswd modules). Version/security support follows
Debian's maintenance lifecycle, not just upstream release numbering. Package
updates require rebuilding the image; do not assume an installed image updates
itself. Revisit the base distribution before its support expires.
