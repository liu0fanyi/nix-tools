from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


DEPLOY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEPLOY_DIR / "scripts"))

import render


class RenderTests(unittest.TestCase):
    def prepare(self, profile: str) -> tuple[Path, Path, tempfile.TemporaryDirectory]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        secrets = root / "secrets"
        secrets.mkdir()
        for name, value in {
            "authelia_jwt_secret": "jwt-secret-long-enough-for-test",
            "authelia_session_secret": "session-secret-long-enough-for-test",
            "authelia_storage_key": "storage-secret-long-enough-for-test",
            "authelia_users_database.yml": "---\nusers: {}\n",
            "dufs-readonly.yaml": "serve-path: /data\n",
            "caddy_lan_basic_auth": (
                "admin $2a$14$jQ8iy6ybRwnQVDxCFAxEO."
                "VoyPMR7GZVbYgyjcimvUMU1lePXP7NK\n"
            ),
        }.items():
            (secrets / name).write_text(value, encoding="utf-8")
            (secrets / name).chmod(0o600)

        text = (DEPLOY_DIR / "instances/home.toml").read_text(encoding="utf-8")
        text = text.replace(
            'secrets = "/home/liou/dufs-lan/project/nix-tools/deploy/secrets"',
            f'secrets = "{secrets}"',
        )
        if profile == "vps-direct":
            text = text.replace(
                'profile = "home-ipv6-cdn"', 'profile = "vps-direct"'
            ).replace("ddns = true", "ddns = false").replace(
                "terminal = true", "terminal = false"
            )
        config = root / "instance.toml"
        config.write_text(text, encoding="utf-8")
        output = root / "generated"
        return config, output, temp

    def test_home_profile(self) -> None:
        config, output, temp = self.prepare("home-ipv6-cdn")
        self.addCleanup(temp.cleanup)
        render.render(config, output)
        caddy = (output / "Caddyfile").read_text(encoding="utf-8")
        files = (output / "compose-files.txt").read_text(encoding="utf-8")
        self.assertIn("home.wttliou.top:5009", caddy)
        self.assertIn("http://:5008", caddy)
        self.assertIn("https://work.wttliou.top:5443", caddy)
        self.assertIn("compose.ddns.yaml", files)
        self.assertIn("compose.readonly.yaml", files)
        self.assertIn("compose.authelia.yaml", files)
        self.assertIn('"dufs_write":true', caddy)
        self.assertIn('"game_tools":true', caddy)
        self.assertIn('"terminal":true', caddy)
        self.assertIn('"dufs_write":false', caddy)
        self.assertIn('"tag_write":false', caddy)
        self.assertIn('"game_tools":false', caddy)
        self.assertIn("unix//run/host-ttyd/ttyd.sock", caddy)
        self.assertIn("reverse_proxy dufs-readonly:5000", caddy)
        self.assertIn("reverse_proxy tag-server-readonly:8081", caddy)
        self.assertIn(
            "path /device-api/listing /device-api/v1/files /device-api/v1/comics/manifest /device-api/v1/comics/page /device-api/v1/pdf/info /device-api/pdf/render /device-api/v1/epub/info /device-api/v1/epub/page /device-api/thumbnail /device-api/media/cover /device-api/device-session",
            caddy,
        )
        self.assertIn("handle /tag-api/device-sessions", caddy)
        self.assertIn("uri strip_prefix /tag-api", caddy)
        self.assertIn("header_up X-Dufs-Device-Api 1", caddy)
        self.assertIn("header_up X-Dufs-Device-Provisioning 1", caddy)
        self.assertGreaterEqual(caddy.count("header_up -X-Dufs-Device-Api"), 4)
        self.assertGreaterEqual(caddy.count("header_up -X-Dufs-Device-Provisioning"), 4)
        self.assertIn("path /device-api /device-api/*", caddy)
        self.assertIn('respond "Unknown device API" 404', caddy)
        self.assertIn('@public_device_api path /device-api /device-api/*', caddy)
        self.assertLess(caddy.index("@public_device_api"), caddy.index("forward_auth"))
        self.assertIn("not path /authelia/* /device-api /device-api/*", caddy)
        self.assertIn('respond "Read-only tag service" 405', caddy)
        self.assertIn('@game_tools {', caddy)
        self.assertIn('path /dist/bevy-game /dist/bevy-game/*', caddy)
        self.assertIn(
            "/dist/bevy-game/animation-editor/index.html "
            "/dist/bevy-game/galgame",
            caddy,
        )
        self.assertIn(
            "/dist/bevy-game/gallery-2d/index.html "
            "/dist/bevy-game/gallery-3d",
            caddy,
        )
        self.assertIn(
            "handle_path /dist/*",
            caddy,
        )
        self.assertIn(
            'header @html_entry Cache-Control "no-cache, must-revalidate"',
            caddy,
        )
        self.assertNotIn("{query}.contains('json')", caddy)
        self.assertIn(
            "expression {query}=='json'||{query}.startsWith('json&')",
            caddy,
        )
        self.assertLess(
            caddy.index("handle_path /tag-api/*"),
            caddy.index("handle @dufs_api"),
        )
        self.assertGreaterEqual(caddy.count("root * /srv/dist"), 3)
        instance = (output / "compose.instance.yaml").read_text(encoding="utf-8")
        env = (output / "compose.env").read_text(encoding="utf-8")
        self.assertIn(
            "READONLY_GATEWAY_IMAGE=docker.io/library/haproxy:3.2.21-alpine",
            env,
        )
        self.assertIn("/run/host-ttyd:ro", instance)
        self.assertIn("tag-server-readonly:", instance)
        self.assertIn(
            '"/home/liou/dufs:/workspace:ro"',
            instance,
        )
        self.assertIn(
            '"/home/liou/dufs/.dufs_plus_state:/data"',
            instance,
        )
        self.assertIn("--metadata-dir /data/metadata", instance)
        self.assertTrue((output / "ttyd-compose.service").is_file())

    def test_cors_origins_are_explicit_and_shell_quoted(self) -> None:
        config, output, temp = self.prepare("home-ipv6-cdn")
        self.addCleanup(temp.cleanup)
        text = config.read_text(encoding="utf-8").replace(
            "cors_origins = []",
            'cors_origins = ["http://device.local:8080"]',
        )
        config.write_text(text, encoding="utf-8")
        render.render(config, output)
        instance = (output / "compose.instance.yaml").read_text(encoding="utf-8")
        self.assertEqual(instance.count("--cors-origin http://device.local:8080"), 2)

    def test_invalid_cors_origin_is_rejected(self) -> None:
        config, output, temp = self.prepare("home-ipv6-cdn")
        self.addCleanup(temp.cleanup)
        text = config.read_text(encoding="utf-8").replace(
            "cors_origins = []",
            'cors_origins = ["https://device.local/path"]',
        )
        config.write_text(text, encoding="utf-8")
        with self.assertRaises(render.ConfigError):
            render.render(config, output)

    def test_vps_profile(self) -> None:
        config, output, temp = self.prepare("vps-direct")
        self.addCleanup(temp.cleanup)
        render.render(config, output)
        caddy = (output / "Caddyfile").read_text(encoding="utf-8")
        files = (output / "compose-files.txt").read_text(encoding="utf-8")
        self.assertIn("nas.wttliou.top {", caddy)
        self.assertIn('@public_device_api path /device-api /device-api/*', caddy)
        self.assertNotIn("tls internal", caddy)
        self.assertNotIn("compose.ddns.yaml", files)
        self.assertIn("compose.vps-direct.yaml", files)
        self.assertNotIn("unix//run/host-ttyd/ttyd.sock", caddy)
        self.assertFalse((output / "ttyd-compose.service").exists())

    def test_aliyun_edgeone_profile(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        config = root / "aliyun.toml"
        config.write_text(
            (DEPLOY_DIR / "instances" / "aliyun.toml").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        output = root / "generated"
        render.render(config, output)

        caddy = (output / "Caddyfile").read_text(encoding="utf-8")
        files = (output / "compose-files.txt").read_text(encoding="utf-8")
        instance = (output / "compose.instance.yaml").read_text(encoding="utf-8")
        manifest = (output / "manifest.json").read_text(encoding="utf-8")
        self.assertIn("http://wttliou.top, http://www.wttliou.top", caddy)
        self.assertIn("X-Forwarded-Proto http", caddy)
        self.assertIn('@public_device_api path /device-api /device-api/*', caddy)
        self.assertNotIn("authelia", caddy)
        self.assertIn("compose.aliyun-edgeone-http.yaml", files)
        self.assertNotIn("compose.authelia.yaml", files)
        self.assertNotIn("compose.ddns.yaml", files)
        self.assertNotIn("--allow-all", instance)
        self.assertIn('"dufs_write":false', caddy)
        self.assertIn('"tag_write":false', caddy)
        self.assertIn('"game_tools":false', caddy)
        self.assertIn('"terminal":false', caddy)
        self.assertIn('respond "Read-only tag service" 405', caddy)
        self.assertIn('@game_tools {', caddy)
        self.assertIn('"/root/nix-tools/dufs_data:/data:ro"', instance)
        self.assertIn('"/root/nix-tools/dufs_data:/workspace:ro"', instance)
        self.assertIn('"/root/nix-tools/tag-db:/data"', instance)
        self.assertIn("--metadata-dir /data/metadata", instance)
        self.assertIn('"engine": "docker"', manifest)


if __name__ == "__main__":
    unittest.main()
