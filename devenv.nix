{ pkgs, lib, config, inputs, ... }:

{
  # 本仓库 deploy/ 脚本仅依赖 Python 标准库（tomllib/urllib/argparse 等），
  # 外部命令 curl/podman/podman-compose/ssh/rsync/zstd/docker 均由系统或
  # home-manager 提供，无需在此重复声明。这里只保证 python3 可用，
  # 其余依赖跟随系统 profile。
  packages = with pkgs; [
    python3
  ];

  # 与 home.toml 的 engine 保持一致：本机部署用 podman。

  scripts.manage.exec = ''
    python3 deploy/scripts/manage.py --config deploy/instances/home.toml "$@"
  '';

  scripts.release.exec = ''
    python3 deploy/scripts/release-apps.py "$@"
  '';

  enterShell = ''
    echo "nix-tools devenv: python3"
    echo "  manage  → python3 deploy/scripts/manage.py (home 实例, output 默认 ~/.local/share/dufs-plus/runtime/home)"
    echo "  release → python3 deploy/scripts/release-apps.py"
  '';
}
