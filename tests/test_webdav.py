"""Black-box tests against the production image; Python stdlib only."""
import base64
import http.client
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import uuid
import xml.etree.ElementTree as ET
import zipfile

IMAGE = os.environ.get('TEST_IMAGE', 'zotero-webdav:test')
PASSWORD = 'test-only-long-password-42'
AUTH = 'Basic ' + base64.b64encode(('zotero:' + PASSWORD).encode()).decode()


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


class WebDAV(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = 'zotero-test-' + uuid.uuid4().hex[:10]
        cls.volume = cls.name + '-data'
        docker('volume', 'create', cls.volume)
        cls.addClassCleanup(lambda: docker('volume', 'rm', cls.volume))
        cls.addClassCleanup(lambda: docker('rm', '-f', cls.name))
        cls.options = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.options.cleanup)
        cls.options_path = Path(cls.options.name) / 'options.json'
        cls.write_options()
        cls.start()

    @classmethod
    def write_options(cls, **updates):
        options = dict(username='zotero', password=PASSWORD, encrypted_transport_confirmed=True)
        options.update(updates)
        cls.options_path.write_text(json.dumps(options))

    @classmethod
    def start(cls):
        # /data/options.json is a writable Supervisor-managed file on HA OS.
        docker('run', '-d', '--name', cls.name, '--security-opt=no-new-privileges',
               '-p', '127.0.0.1::8080', '-v', cls.volume + ':/data',
               '-v', str(cls.options_path) + ':/data/options.json', IMAGE)
        cls.port = int(docker('port', cls.name, '8080/tcp').rsplit(':', 1)[1])
        for _ in range(100):
            try:
                if cls.request('OPTIONS', '/zotero/')[0] == 200:
                    return
            except (OSError, http.client.HTTPException):
                pass
            if docker('inspect', '-f', '{{.State.Running}}', cls.name) == 'false':
                raise RuntimeError(docker('logs', cls.name))
            time.sleep(.1)
        raise RuntimeError('Server readiness timeout: ' + docker('logs', cls.name))

    @classmethod
    def request(cls, method, path, body=None, headers=None, auth=AUTH):
        connection = http.client.HTTPConnection('127.0.0.1', cls.port, timeout=15)
        values = dict(headers or {})
        if auth:
            values['Authorization'] = auth
        try:
            connection.request(method, path, body=body, headers=values)
            result = connection.getresponse()
            return result.status, dict(result.getheaders()), result.read()
        finally:
            connection.close()

    def test_authentication_and_unauthorized_methods(self):
        for method in ('OPTIONS', 'PROPFIND', 'GET', 'PUT', 'DELETE', 'MKCOL'):
            for auth in (None, 'Basic ' + base64.b64encode(b'zotero:incorrect').decode()):
                with self.subTest(method=method, auth=bool(auth)):
                    status, headers, _ = self.request(method, '/zotero/denied', auth=auth)
                    self.assertEqual(status, 401)
                    self.assertIn('WWW-Authenticate', headers)
        self.assertEqual(self.request('GET', '/zotero/denied')[0], 404)

    def test_zotero_verification(self):
        # Mirrors Zotero storage/webdav.js checkServer's existing-directory path.
        status, headers, _ = self.request('OPTIONS', '/zotero/')
        self.assertIn(status, (200, 204))
        self.assertIn('DAV', headers)
        body = "<propfind xmlns='DAV:'><prop><getcontentlength/></prop></propfind>"
        status, _, xml = self.request('PROPFIND', '/zotero/', body,
                                     {'Depth': '0', 'Content-Type': 'text/xml; charset=utf-8'})
        self.assertEqual(status, 207)
        self.assertEqual(ET.fromstring(xml).tag, '{DAV:}multistatus')
        self.assertEqual(self.request('GET', '/zotero/nonexistent.prop')[0], 404)
        path = '/zotero/zotero-test-file.prop'
        self.assertIn(self.request('PUT', path, b' ')[0], (200, 201, 204))
        self.assertEqual(self.request('GET', path)[2], b' ')
        self.assertIn(self.request('DELETE', path)[0], (200, 204))

    def test_collection_listing_and_binary_roundtrip(self):
        path = '/zotero/collection/'
        self.assertEqual(self.request('MKCOL', path)[0], 201)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('attachment.pdf', b'%PDF-1.7\n' + bytes(range(256)) * 4096)
        data = stream.getvalue()
        self.assertEqual(self.request('PUT', path + 'ABC12345.zip', data)[0], 201)
        self.assertEqual(self.request('GET', path + 'ABC12345.zip')[2], data)
        status, _, xml = self.request('PROPFIND', path, headers={'Depth': '1'})
        self.assertEqual(status, 207)
        hrefs = [node.text for node in ET.fromstring(xml).iter('{DAV:}href')]
        self.assertTrue(any('ABC12345.zip' in href for href in hrefs))
        self.assertIn(self.request('DELETE', path + 'ABC12345.zip')[0], (200, 204))
        self.assertEqual(self.request('GET', path + 'ABC12345.zip')[0], 404)
        self.assertIn(self.request('DELETE', path)[0], (200, 204))

    def test_private_paths(self):
        for path in ('/options.json', '/users', '/state/webdav.sqlite', '/etc/passwd',
                     '/%2e%2e/options.json', '/zotero/../../options.json'):
            with self.subTest(path=path):
                self.assertIn(self.request('GET', path)[0], (400, 403, 404))
        docker('exec', '-u', '10001', self.name, 'ln', '-s', '/data/options.json', '/data/attachments/leak')
        self.assertIn(self.request('GET', '/leak')[0], (403, 404))

    def test_nonroot_and_hash(self):
        status = docker('exec', self.name, 'cat', '/proc/1/status')
        self.assertIn('Uid:\t10001\t10001\t10001\t10001', status)
        self.assertIn('CapEff:\t0000000000000000', status)
        hashed = docker('exec', self.name, 'cat', '/run/zotero/users')
        result = subprocess.run(['docker', 'exec', '-u', '10001', self.name, 'test', '-w', '/run/zotero/users'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(hashed.startswith('zotero:$2y$12$'))
        self.assertNotIn(PASSWORD, hashed)
        self.assertNotIn(PASSWORD, docker('logs', self.name))
        result = subprocess.run(['docker', 'exec', '-u', '10001', self.name, 'cat', '/data/options.json'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_persistence_and_recreation(self):
        path = '/zotero/persistent.prop'
        self.assertIn(self.request('PUT', path, b'keep-me')[0], (201, 204))
        docker('rm', '-f', self.name)
        self.start()
        self.assertEqual(self.request('GET', path)[2], b'keep-me')
        self.assertIn(self.request('DELETE', path)[0], (200, 204))

    def test_fail_closed_options(self):
        # No restart of the main server; independent instances use their own data.
        for overrides in ({'password': ''}, {'password': 'x' * 73},
                          {'username': 'bad\nname'}, {'encrypted_transport_confirmed': False}):
            with self.subTest(overrides=list(overrides)):
                options = dict(username='zotero', password=PASSWORD, encrypted_transport_confirmed=True)
                options.update(overrides)
                with tempfile.TemporaryDirectory() as directory:
                    file = Path(directory) / 'options.json'
                    file.write_text(json.dumps(options))
                    result = subprocess.run(['docker', 'run', '--rm', '-v', str(file) + ':/data/options.json', IMAGE],
                                            capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(PASSWORD, result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
