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
    python3 -m unittest discover -s scripts/tests

# 镜像 specs、docs 与看板到 NUC todos/nix-tools/
sync-todos *args:
    python3 scripts/sync-todos.py {{args}}

# 只读设备预检；不接收 --yes/--flake，不执行安装。
install-check host *args:
    python3 scripts/host-install.py --host "$1" --check "${@:2}"

install-plan host *args:
    python3 scripts/host-install.py --host "$1" --plan "${@:2}"

# PC 上用独立虚拟盘验证 NUC 分区和 UEFI 引导，不连接真实磁盘。
install-test-nuc:
    nix build --impure --no-link --print-out-paths -L --file scripts/tests/nuc-install-vm.nix

# 本机规则安装：默认预演，--apply 安装，--check 核验。
agent-rules *args:
    python3 scripts/agent-rules.py "$@"
