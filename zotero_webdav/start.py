"""Validate Supervisor options, prepare private data, then permanently drop root."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

UID = GID = 10001


def main():
    os.umask(0o077)
    try:
        options = json.loads(Path('/data/options.json').read_text())
    except (OSError, ValueError):
        raise ValueError('Cannot read valid /data/options.json') from None
    username = options.get('username')
    password = options.get('password')
    if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', username):
        raise ValueError('Username must contain 1–64 letters, digits, dots, underscores or hyphens')
    # bcrypt uses at most 72 bytes; never silently truncate a credential.
    if (not isinstance(password, str) or not 16 <= len(password.encode()) <= 72
            or any(c in password for c in '\r\n\0')):
        raise ValueError('Password must be 16–72 UTF-8 bytes without NUL or line breaks')
    if options.get('encrypted_transport_confirmed') is not True:
        raise ValueError('Configure an encrypted access path and confirm encrypted_transport_confirmed first')
    Path('/data').chmod(0o711)
    Path('/data/options.json').chmod(0o600)
    for name in ('attachments', 'attachments/zotero', 'state', 'tmp'):
        path = Path('/data') / name
        if path.is_symlink():
            raise ValueError('Refusing symlink in managed storage')
        path.mkdir(mode=0o700, exist_ok=True)
        os.chown(path, UID, GID)
        path.chmod(0o700)
    runtime = Path('/run/zotero')
    os.chown(runtime, 0, 0)
    runtime.chmod(0o711)
    # stdin keeps the plaintext password out of argv and logs. Only hash is written.
    result = subprocess.run(['htpasswd', '-niBC', '12', username], input=password + '\n',
                            text=True, capture_output=True, check=True)
    users = runtime / 'users'
    descriptor = os.open(users, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o640)
    with os.fdopen(descriptor, 'w') as handle:
        handle.write(result.stdout)
    os.chown(users, 0, GID)
    users.chmod(0o640)
    os.setgroups([])
    os.setgid(GID)
    os.setuid(UID)
    # Supervisor tokens have no purpose in this service, even if injected.
    for name in list(os.environ):
        if name in ('SUPERVISOR_TOKEN', 'HASSIO_TOKEN'):
            del os.environ[name]
    print('Starting authenticated WebDAV on port 8080 as uid 10001; encrypted transport required', flush=True)
    os.execv('/usr/sbin/lighttpd', ['lighttpd', '-D', '-f', '/etc/zotero/lighttpd.conf'])


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError):
        # Avoid exception details containing options or credentials.
        print('Startup refused: check options, encrypted transport confirmation, and private storage permissions', file=sys.stderr)
        sys.exit(1)
