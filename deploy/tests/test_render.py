from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


DEPLOY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEPLOY_DIR / "scripts"))

import render


class RenderTests(unittest.TestCase):
    def test_dufs_templates_enable_server_side_archives(self) -> None:
        writable = (DEPLOY_DIR / "compose.yaml").read_text(encoding="utf-8")
        readonly = (DEPLOY_DIR / "compose.readonly.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("--allow-archive", writable)
        self.assertIn("--allow-archive", readonly)

    def test_locked_git_crypt_secret_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "source"
            destination = root / "runtime"
            source.mkdir()
            (source / "token").write_bytes(b"\x00GITCRYPT\x00encrypted")

            with self.assertRaisesRegex(
                render.ConfigError, "still git-crypt encrypted"
            ):
                render.sync_runtime_secrets(source, destination)

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
            'secret_source = "/media/liou/project/me/nix-tools/deploy/secrets"',
            f'secret_source = "{secrets}"',
        ).replace(
            'secrets = "/home/liou/.config/dufs-plus/secrets"',
            f'secrets = "{root / "runtime-secrets"}"',
        )
        if profile == "vps-direct":
            text = text.replace(
                'profile = "home-ipv6-cdn"', 'profile = "vps-direct"'
            ).replace("ddns = true", "ddns = false").replace(
                "terminal = true", "terminal = false"
            )
        config = root / "instance.toml"
        config.write_text(text, encoding="utf-8")
        writing_ssh = root / "runtime-secrets" / "writing-git"
        writing_ssh.mkdir(parents=True)
        (writing_ssh / "id_ed25519").write_text("test-private-key\n")
        (writing_ssh / "known_hosts").write_text("github.com test-key\n")
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
            "path /device-api/v1/session /device-api/v1/files /device-api/v1/tags /device-api/v1/items /device-api/v1/progress /device-api/v1/thumbnail /device-api/v1/cover /device-api/v1/pdf/info /device-api/v1/pdf/page /device-api/v1/epub/info /device-api/v1/epub/page /device-api/v1/comics/manifest /device-api/v1/comics/page /device-api/v1/openapi.json /device-api/v1/docs",
            caddy,
        )
        self.assertIn("method GET HEAD OPTIONS", caddy)
        self.assertIn("@device_session_revoke {", caddy)
        self.assertIn("method DELETE", caddy)
        self.assertIn("handle @device_session_revoke", caddy)
        self.assertIn("@device_progress_write {", caddy)
        self.assertIn("method PUT", caddy)
        self.assertIn("path /device-api/v1/progress", caddy)
        self.assertIn("handle @device_progress_write", caddy)
        self.assertIn("@device_transcription_upload {", caddy)
        self.assertIn("method POST", caddy)
        self.assertIn("path /device-api/v1/transcriptions", caddy)
        self.assertIn("@device_transcription_read {", caddy)
        self.assertIn("path /device-api/v1/transcriptions/*", caddy)
        self.assertIn(
            "uri replace /device-api/v1/transcriptions /v1/device/transcriptions",
            caddy,
        )
        self.assertIn("@device_writing_commit {", caddy)
        self.assertIn("path /device-api/v1/writing/commits", caddy)
        self.assertIn(
            "uri replace /device-api/v1/writing/commits /v1/device/writing/commits",
            caddy,
        )
        self.assertIn("@device_writing_conflict_resolved {", caddy)
        self.assertIn(
            "path /device-api/v1/writing/conflicts/*/resolved",
            caddy,
        )
        self.assertIn(
            "uri replace /device-api/v1/writing/conflicts /v1/device/writing/conflicts",
            caddy,
        )
        self.assertIn("@device_writing_snapshot {", caddy)
        self.assertIn("method GET HEAD", caddy)
        self.assertIn("path /device-api/v1/writing/snapshots/*", caddy)
        self.assertIn(
            "uri replace /device-api/v1/writing/snapshots /v1/device/writing/snapshots",
            caddy,
        )
        self.assertIn("@device_writing_status {", caddy)
        self.assertIn("path /device-api/v1/writing/status/*", caddy)
        self.assertIn(
            "uri replace /device-api/v1/writing/status /v1/device/writing/status",
            caddy,
        )
        self.assertIn("handle /tag-api/device-sessions", caddy)
        self.assertIn("@device_enrollment {", caddy)
        self.assertIn(
            "path /device-api/v1/enrollments /device-api/v1/enrollments/*/claim",
            caddy,
        )
        self.assertIn(
            "uri replace /device-api/v1/enrollments /v1/device/enrollments",
            caddy,
        )
        self.assertIn("handle /tag-api/v1/device-enrollments*", caddy)
        self.assertIn("handle /tag-api/v1/device-tokens*", caddy)
        self.assertIn("handle /tag-api/v1/writing-projects*", caddy)
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
        self.assertIn(
            '"/home/liou/.local/share/whisper.cpp/models:/models:ro"',
            instance,
        )
        self.assertIn("runtime-secrets/writing-git:/root/.ssh:ro", instance)
        readonly_service = instance.split("  tag-server-readonly:", 1)[1]
        self.assertNotIn("writing-git:/root/.ssh", readonly_service)
        self.assertTrue((output / "ttyd-compose.service").is_file())
        terminal_unit = (output / "ttyd-compose.service").read_text(
            encoding="utf-8"
        )
        self.assertIn("Environment=HOME=/home/liou", terminal_unit)
        self.assertIn("ExecStart=/home/liou/.nix-profile/bin/ttyd", terminal_unit)
        self.assertNotIn("/media/liou/.nix-profile", terminal_unit)
        unit = (output / "dufs-plus-compose.service").read_text(encoding="utf-8")
        self.assertIn("Restart=on-failure", unit)
        self.assertIn("RestartSec=15s", unit)
        self.assertIn(f"WorkingDirectory={output}", unit)
        self.assertIn(f"ExecStart={output / 'compose-control'} up -d", unit)
        self.assertNotIn(str(DEPLOY_DIR), unit)
        self.assertTrue((output / "compose.yaml").is_file())
        self.assertTrue((output / "compose.home-ipv6-cdn.yaml").is_file())
        self.assertTrue((output / "haproxy.readonly.cfg").is_file())
        self.assertEqual(
            (output / "haproxy.readonly.cfg").stat().st_mode & 0o777,
            0o644,
        )
        self.assertTrue((output / "compose-control").is_file())
        self.assertEqual((output / "compose-control").stat().st_mode & 0o777, 0o700)
        runtime_secret = Path(temp.name) / "runtime-secrets/authelia_jwt_secret"
        self.assertEqual(
            runtime_secret.read_text(encoding="utf-8"),
            "jwt-secret-long-enough-for-test",
        )
        self.assertEqual(runtime_secret.stat().st_mode & 0o777, 0o600)
        self.assertIn(str(output / "compose.yaml"), files)
        self.assertNotIn(str(DEPLOY_DIR / "compose.yaml"), files)

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
