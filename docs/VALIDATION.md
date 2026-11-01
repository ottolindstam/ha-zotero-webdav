# Validation record and hardware acceptance

## Cloud — 2026-11-01

Executed in an isolated AMD64 Linux cloud environment, not on Home Assistant OS:

- Production Docker image built for `linux/amd64`.
- Production Docker image built for `linux/arm64` using BuildKit's QEMU emulation;
  image metadata confirmed `linux/arm64`. This checks the complete build,
  including ARM64 package installation, but is not a Raspberry Pi runtime test.
- Seven Python unittest integration cases passed against the AMD64 production
  image: authenticated/unauthorized method handling; Zotero's existing-directory
  verification sequence; MKCOL, XML PROPFIND listing, binary ZIP PUT/GET and
  DELETE; fail-closed invalid options; non-root UID/capabilities and bcrypt;
  persistence after container removal/recreation using the same Docker volume;
  private files, traversal and symlink protection.
- Native GitHub Actions jobs are configured for AMD64 and ARM64. A configured
  workflow is not evidence of a completed hosted CI run.

The tests use synthetic data and an HTTP loopback backend. They do not exercise
a real TLS proxy, Zotero desktop UI, HA Supervisor lifecycle, backup restoration,
SD-card performance, 6 GB synchronization, or Matter Server. No Raspberry Pi was
accessible from this cloud session; its exact model/architecture is still unknown.

## Required on actual HA OS before using the real library

Record results (including OS/Supervisor/Zotero versions) rather than assuming
success from the cloud image tests:

- [ ] Record Pi model, `aarch64` OS architecture, free storage, and Matter status.
- [ ] Install from the GitHub repository through the store with Protection mode on.
- [ ] Confirm startup fails with empty/default credentials and no encryption acknowledgment.
- [ ] Start with valid options; inspect logs for AppArmor or permission failures.
- [ ] Verify a trusted HTTPS certificate and no direct unencrypted/public backend
      exposure. Test unauthenticated access returns 401 through the actual proxy.
- [ ] Zotero desktop Verify Server passes. Upload a small PDF, download it on a
      second client, compare its content, and verify changes/deletion using a
      disposable test library/attachment.
- [ ] Restart app and reboot HA OS; verify the same attachment is available.
- [ ] Test a version upgrade with a known attachment and cold-backup restore on a
      spare/test installation. Confirm automatic resume after backup.
- [ ] Sync roughly 6 GB in batches; monitor free space, CPU/RAM/I/O, and logs.
      Include the largest actual PDF and multiple clients. Keep client backups.
- [ ] Confirm Home Assistant automations and Matter devices continue responding
      during sync, backup, and after app restart/update. Do not change Matter.

Report a failed AppArmor check with the specific denial; do not disable protection
to make an acceptance check pass. Keep this release experimental until these
checks are recorded. Passing these checks on one Pi does not validate every model.
