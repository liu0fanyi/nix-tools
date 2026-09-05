set positional-arguments
set shell := ["bash", "-euo", "pipefail", "-c"]

# 目标必须明确；infra 只更新基础设施，all 包括两个产品。
deploy target component="infra" *args:
    python3 deploy/scripts/release-apps.py --target "$1" "$2" "${@:3}"

# NUC 运维，所有操作在 NUC 执行。
manage +args:
    python3 -c 'import shlex, subprocess, sys; subprocess.run(["ssh", "liou@nuc.local", shlex.join(["python3", "/media/liou/project/me/nix-tools/deploy/scripts/manage.py", "--config", "/media/liou/project/me/nix-tools/deploy/instances/home.toml", "--output", "/home/liou/.local/share/dufs-plus/runtime/home", *sys.argv[1:]])], check=True)' "$@"

test:
    python3 -m unittest discover -s deploy/tests
