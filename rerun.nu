# 在 nix-tools 目录下执行
#
# 用法:
#   nu rerun.nu [用户名]                # 自动检测系统类型并执行对应部署
#   nu rerun.nu --nixos [用户名]        # 强制 NixOS 系统 switch（与系统类型不一致会报错）
#   nu rerun.nu --no-nixos [用户名]     # 强制 standalone home-manager switch（同上）
#
# 说明:
#   - 自动读取 /etc/os-release 判断系统：ID=nixos → NixOS 主机。
#   - NixOS 主机：走 `sudo nixos-rebuild switch --flake .#<host>`，
#     重建整个系统，包含 NixOS 集成的 home-manager（用户配置随系统一起更新），
#     因此不应再单独跑 standalone home-manager switch。
#   - 非 NixOS 主机（如 Ubuntu）：走 standalone home-manager：
#     `nix run nixpkgs#home-manager -- switch --flake .#<user>`，
#     此时 nixos-rebuild / nixosConfigurations 不可用。
#   - --nixos / --no-nixos 可显式覆盖自动检测；若覆盖结果与本机系统类型矛盾，
#     脚本拒绝执行并提示（防止在 NixOS 上跑 standalone、或反之）。
#   - 目标默认 liou；NixOS 主机名默认 homebox（可用 --host 覆盖）。
def main [
    target: string = "liou"
    --nixos # 强制 NixOS 系统 switch（覆盖自动检测）
    --no-nixos # 强制 standalone home-manager switch（覆盖自动检测）
    --host: string = "homebox" # NixOS 配置名（flake 里的 nixosConfigurations.<host>）
] {
    # 自动检测：/etc/os-release 中 ID=nixos 即为 NixOS 系统
    let os_id = (open /etc/os-release | lines | where ($it | str starts-with "ID=") | first | str replace "ID=" "" | str trim)
    let detected_is_nixos = ($os_id == "nixos")

    # 显式覆盖：--nixos 与 --no-nixos 互斥
    if ($nixos and $no_nixos) {
        error make { msg: "--nixos 与 --no-nixos 不能同时使用" }
    }

    let use_nixos = if $nixos {
        true
    } else if $no_nixos {
        false
    } else {
        $detected_is_nixos
    }

    # 防呆：覆盖结果与本机系统类型矛盾时拒绝执行
    if ($use_nixos != $detected_is_nixos) {
        let sys_label = if $detected_is_nixos { "NixOS" } else { "非 NixOS" }
        let mode_label = if $use_nixos { "NixOS system switch" } else { "standalone home-manager switch" }
        error make {
            msg: $"本机是 ($sys_label)，但你显式指定了 ($mode_label)。"
        }
    }

    if $use_nixos {
        print $"(ansi green)NixOS system switch: flake#($host)(ansi reset)"
        # 需要 root：nixos-rebuild 最后要把新系统链接到 /nix/var/nix/profiles/system
        # 用绝对 flake 路径（sudo 可能改变 cwd/环境），--refresh 确保拉到最新 inputs
        sudo nixos-rebuild switch --flake $"($env.PWD)#($host)" --refresh
    } else {
        print $"(ansi green)Deploying Home Manager target: ($target)(ansi reset)"
        nix run nixpkgs#home-manager -- switch --flake $".#($target)" -b backup
    }
}
