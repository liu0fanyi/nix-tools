# 在 nix-tools 目录下执行
#
# 用法:
#   nu rerun.nu [用户名]                # standalone home-manager switch（非 NixOS 主机）
#   nu rerun.nu --nixos [用户名]        # NixOS 系统 switch（含 NixOS 集成的 home-manager）
#
# 说明:
#   - 默认走 standalone home-manager：`nix run nixpkgs#home-manager -- switch --flake .#<user>`
#     适用于非 NixOS 主机（如 Ubuntu），或单独管理用户配置。
#   - --nixos 走 NixOS 系统级 rebuild：`nixos-rebuild switch --flake .#<host>`
#     适用于 flake 部署的 NixOS 主机（本仓库 homebox）。这会重建整个系统，
#     包括 NixOS 集成的 home-manager（用户配置随系统一起更新），
#     因此不需要（也不应）再单独跑 standalone home-manager switch。
#   - 目标默认 liou；NixOS 主机名默认 homebox（可用 --host 覆盖）。
def main [
    target: string = "liou"
    --nixos # NixOS 系统 switch（flake 部署主机）
    --host: string = "homebox" # NixOS 配置名（flake 里的 nixosConfigurations.<host>）
] {
    if $nixos {
        print $"(ansi green)NixOS system switch: flake#($host)(ansi reset)"
        # 需要 root：nixos-rebuild 最后要把新系统链接到 /nix/var/nix/profiles/system
        # 用绝对 flake 路径（sudo 可能改变 cwd/环境），--refresh 确保拉到最新 inputs
        sudo nixos-rebuild switch --flake $"($env.PWD)#($host)" --refresh
    } else {
        print $"(ansi green)Deploying Home Manager target: ($target)(ansi reset)"
        nix run nixpkgs#home-manager -- switch --flake $".#($target)" -b backup
    }
}
