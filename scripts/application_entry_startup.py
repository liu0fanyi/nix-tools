"""Keep the frozen startup guard; permit only the reviewed public TCP routing file."""
from pathlib import Path
import os
import stat
import native_nuc_startup as guard

TRANSPORT_PATH = Path('/home/liou/.local/share/dufs-plus/runtime/home/haproxy.readonly.cfg')
KNOWN_TRANSPORTS = ('global\n    log stdout format raw local0\n\ndefaults\n    log global\n    mode tcp\n    timeout connect 5s\n    timeout client 1h\n    timeout server 1h\n\nfrontend readonly_dual_protocol\n    bind :5008\n    tcp-request inspect-delay 100ms\n    tcp-request content accept if { req.ssl_hello_type 1 }\n    use_backend readonly_https if { req.ssl_hello_type 1 }\n    default_backend readonly_http\n\nbackend readonly_http\n    server caddy_http caddy:5008 check\n\nbackend readonly_https\n    server caddy_https caddy:5443 check\n', 'global\n    log stdout format raw local0\n\ndefaults\n    log global\n    mode tcp\n    timeout connect 5s\n    timeout client 1h\n    timeout server 1h\n\nfrontend readonly_dual_protocol\n    bind :5008\n    tcp-request inspect-delay 100ms\n    tcp-request content accept if { req.ssl_hello_type 1 }\n    use_backend readonly_https if { req.ssl_hello_type 1 }\n    default_backend readonly_http\n\nbackend readonly_http\n    server native_http host.containers.internal:18182 check\n\nbackend readonly_https\n    server caddy_https caddy:5443 check\n')
PRIVATE_FILE = guard.private_file


def runtime_file(name):
    path = Path(name)
    if path == TRANSPORT_PATH and not path.is_symlink():
        info = path.stat()
        if stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o644 and path.read_text() in KNOWN_TRANSPORTS:
            return path
    return PRIVATE_FILE(name)


def configure():
    guard.private_file = runtime_file


if __name__ == '__main__':
    configure()
    raise SystemExit(guard.main())
