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

    # ── 部署后自检：home-manager 是否真正更新到当前 git 状态 ──
    # NixOS 集成的 home-manager 有时不会被 switch 正确重新激活（历史上 activation
    # 被 exit 0 中断过），这里对比 current-home 与当前 git 构建结果，并检查关键文件。
    print $"(ansi cyan)--- 部署后自检 ---(ansi reset)"
    let current_home = ($env.HOME | path join ".local/state/home-manager/gcroots/current-home" | path expand)
    let current_gen = (readlink -f $current_home | str trim)
    # nix build 输出多行（构建日志 + 路径），取最后一行非空 = store 路径
    let expected_gen = (nix build --no-link --print-out-paths $".#nixosConfigurations.($host).config.home-manager.users.($target).home.activationPackage" | lines | where { |l| ($l | str trim) != "" } | last | str trim)
    let ok = ($current_gen == $expected_gen)

    if $ok {
        print $"(ansi green)✓ home-manager generation 已更新: ($current_gen)(ansi reset)"
    } else {
        print $"(ansi yellow)⚠ home-manager generation 未对齐:(ansi reset)"
        print $"  当前: ($current_gen)"
        print $"  期望: ($expected_gen)"
        print "  → 系统 switch 未重新激活 home-manager，需要手动激活："
        print $"    ($expected_gen)/activate"
    }

    # 关键文件检查（pattern 用字面字符串，str contains 匹配）
    let checks = [
        { name: "SSH config (nuc.local)", path: ($env.HOME | path join ".ssh/config"), pattern: "HostName nuc.local" }
        { name: "dsh-web.service", path: ($env.HOME | path join ".config/systemd/user/dsh-web.service"), pattern: "dsh web" }
        { name: "dsh-web-toggle", path: ($env.HOME | path join ".local/bin/dsh-web-toggle"), pattern: "notify=" }
    ]
    for c in $checks {
        if ($c.path | path exists) {
            let content = (open $c.path | to text)
            if ($content | str contains $c.pattern) {
                print $"(ansi green)✓ ($c.name) 已部署(ansi reset)"
            } else {
                print $"(ansi red)✗ ($c.name) 内容不符（缺 '($c.pattern)'）(ansi reset)"
            }
        } else {
            print $"(ansi red)✗ ($c.name) 缺失(ansi reset)"
        }
    }

    if not $ok {
        print $"(ansi yellow)提示: 运行上面的 activate 命令完成 home-manager 激活，或再跑一次 nu rerun.nu(ansi reset)"
    }
}
