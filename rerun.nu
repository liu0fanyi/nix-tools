# 在 nix-tools 目录下执行
#
# 用法:
#   nu rerun.nu [用户名]                # 自动检测系统类型并执行对应部署
#   nu rerun.nu --home-target liou      # 非 NixOS 部署指定的 homeConfigurations
#   nu rerun.nu --nixos [用户名]        # 强制 NixOS 系统 switch（与系统类型不一致会报错）
#   nu rerun.nu --no-nixos [用户名]     # 强制 standalone home-manager switch（同上）
#   nu rerun.nu liou --host liu-bigpc --boot
#                                        # 仅设置下次启动，不热切换当前系统
#
# 说明:
#   - 自动读取 /etc/os-release 判断系统：ID=nixos → NixOS 主机。
#   - NixOS 主机：走 `sudo nixos-rebuild switch --flake .#<host>`，
#     重建整个系统，包含 NixOS 集成的 home-manager（用户配置随系统一起更新），
#     因此不应再单独跑 standalone home-manager switch。
#   - 非 NixOS 主机（如 Ubuntu）：走 standalone home-manager：
#     `nix run .#home-manager -- switch --flake .#<home-target>`，
#     此时 nixos-rebuild / nixosConfigurations 不可用。
#   - --nixos / --no-nixos 可显式覆盖自动检测；若覆盖结果与本机系统类型矛盾，
#     脚本拒绝执行并提示（防止在 NixOS 上跑 standalone、或反之）。
#   - 目标默认 liou；NixOS 主机名默认 homebox（可用 --host 覆盖）。
#   - 非 NixOS 机器默认部署 homeConfigurations.liou-nuc；可用
#     --home-target 选择其他 standalone 配置。target 参数仅 NixOS 分支有效。
def main [
    target: string = "liou"
    --nixos # 强制 NixOS 系统 switch（覆盖自动检测）
    --no-nixos # 强制 standalone home-manager switch（覆盖自动检测）
    --host: string = "homebox" # NixOS 配置名（flake 里的 nixosConfigurations.<host>）
    --home-target: string = "liou-nuc" # standalone 配置名
    --boot # NixOS only：构建并设置下次启动，不立即切换当前系统
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

    if ($boot and (not $use_nixos)) {
        error make { msg: "--boot 仅适用于 NixOS system 部署" }
    }

    if $use_nixos {
        let action = if $boot { "boot" } else { "switch" }
        print $"(ansi green)NixOS system ($action): flake#($host)(ansi reset)"
        # 需要 root：nixos-rebuild 最后要把新系统链接到 /nix/var/nix/profiles/system
        # 用绝对 flake 路径（sudo 可能改变 cwd/环境）；inputs 更新应单独执行
        # `nix flake update`，普通 switch 保持 flake.lock 的可复现性。
        sudo nixos-rebuild $action --flake $"($env.PWD)#($host)"
    } else {
        # CLI 与模块都来自当前 flake.lock 中的同一个 Home Manager input。
        print $"(ansi green)Deploying Home Manager target: ($home_target) - standalone(ansi reset)"
        nix run .#home-manager -- switch --flake $".#($home_target)" -b backup
    }

    if ($use_nixos and $boot) {
        print $"(ansi yellow)✓ 已设置 flake#($host) 为下次启动配置；当前系统尚未热切换。(ansi reset)"
        print "  确认账户迁移等启动前步骤完成后再重启。"
        return
    }

    # ── 部署后自检：home-manager 是否真正更新到当前 git 状态 ──
    # NixOS 集成的 home-manager 有时不会被 switch 正确重新激活（历史上 activation
    # 被 exit 0 中断过）。这里对比生效指针与当前 git 构建结果即可：
    # generation 对齐 = 该 generation 下的所有文件（systemd units、ssh config、
    # wrapper 脚本等）必然都已部署，无需逐个检查。
    #
    # 生效指针说明：home-manager >= 24.11 用 $XDG_STATE_HOME/nix/profiles/home-manager
    # 作为真实生效 generation（switch 会更新它）。旧的
    # $XDG_STATE_HOME/home-manager/gcroots/current-home 已废弃不再维护（会停在旧值，
    # 导致误报“未对齐”），故这里读 profile 链接。
    print $"(ansi cyan)--- 部署后自检 ---(ansi reset)"
    # NixOS 集成的权威来源：home-manager-<user>.service 的 ExecStart 参数
    # 就是实际激活的 generation（由 nixos-rebuild 生成/更新）。
    # 读 ~/.local/state/nix/profiles/home-manager 指针在 NixOS 集成下不会被
    # nixos-rebuild 更新（那是 standalone 模式的路径），会永久误报"未对齐"。
    let current_gen = if $use_nixos {
        # systemctl cat 输出含 ExecStart=...hm-setup-env <gen>，取最后一个 store 路径
        let unit_name = $"home-manager-($target).service"
        let unit = (systemctl cat $unit_name | complete)
        if $unit.exit_code != 0 {
            error make { msg: $"无法读取 ($unit_name)：($unit.stderr | str trim)" }
        }
        let exec_lines = ($unit.stdout | lines | where { |l| ($l | str starts-with "ExecStart=") })
        if ($exec_lines | is-empty) {
            error make { msg: $"($unit_name) 中没有 ExecStart，无法确认 Home Manager generation" }
        }
        let svc = ($exec_lines | first | str replace "ExecStart=" "")
        ($svc | split row " " | last | str trim)
    } else if ($env.HOME | path join ".local/state/nix/profiles/home-manager" | path exists) {
        (readlink -f ($env.HOME | path join ".local/state/nix/profiles/home-manager") | str trim)
    } else {
        # 极老版本 fallback：读 legacy current-home
        let legacy = ($env.HOME | path join ".local/state/home-manager/gcroots/current-home" | path expand)
        if not ($legacy | path exists) {
            error make { msg: "找不到 standalone Home Manager profile；switch 可能没有成功创建 generation" }
        }
        (readlink -f $legacy | str trim)
    }
    # 按系统类型取构建路径；standalone 必须与上面实际 switch 的目标一致。
    let flake_attr = if $use_nixos {
        $".#nixosConfigurations.($host).config.home-manager.users.($target).home.activationPackage"
    } else {
        $".#homeConfigurations.($home_target).activationPackage"
    }
    # nix build 输出多行（构建日志 + 路径），取最后一行非空 = store 路径
    let expected_gen = (nix build --no-link --print-out-paths $flake_attr | lines | where { |l| ($l | str trim) != "" } | last | str trim)

    if ($current_gen == $expected_gen) {
        print $"(ansi green)✓ home-manager generation 已更新: ($current_gen)(ansi reset)"
    } else {
        print $"(ansi yellow)⚠ home-manager generation 未对齐:(ansi reset)"
        print $"  当前: ($current_gen)"
        print $"  期望: ($expected_gen)"
        print "  → switch 已构建但生效指针未指向新 generation（部署可能未激活）。"
        print "    先手动激活，再重跑确认："
        print $"      ($expected_gen)/activate"
        print "    若激活后仍不一致（nix profile 已指向新 gen 而显示旧值），"
        print "    说明是 home-manager 旧 current-home 指针残留，可忽略："
        print "    实际生效以 nix profile 链接 ~/.local/state/nix/profiles/home-manager 为准。"
    }
}
