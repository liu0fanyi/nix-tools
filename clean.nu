#!/usr/bin/env nu

# Nix 环境清理工具
# 自动适配 NixOS（集成模式）与 standalone（非 NixOS）部署：
#   - NixOS：generation 由 nixos-rebuild 管理，用 nix-env --delete-generations 清理
#   - 非 NixOS：home-manager 独立管理，用 home-manager expire-generations 清理
def main [
    mode: string = "help" # 清理模式: gc, all, 或 help
] {
    let os_id = (open /etc/os-release | lines | where ($it | str starts-with "ID=") | first | str replace "ID=" "" | str trim)
    let is_nixos = ($os_id == "nixos")

    match $mode {
        "gc" => {
            print "--- 开始普通清理 (保留回滚能力) ---"
            # 仅删除当前未被引用的包（保留所有 generation，可回滚）
            nix-store --gc
            # 优化存储空间：合并相同文件
            nix-store --optimise
            print "--- 普通清理完成 ---"
        }
        "all" => {
            print "--- 开始彻底清理 (删除所有历史版本) ---"
            if $is_nixos {
                # NixOS 集成模式：home-manager 随系统 generation 管理，
                # 没有独立 home-manager 命令。删除除当前外的所有 NixOS generations
                #（写 /nix/var/nix/profiles/system 需要 root）。
                print "NixOS 模式：清理系统历史 generations..."
                sudo nix-env --delete-generations old -p /nix/var/nix/profiles/system
                # nix-collect-garbage -d 同样需要 root 才能删系统 profile 引用的路径
                sudo nix-collect-garbage -d
                sudo nix-store --optimise
            } else {
                # standalone home-manager：清理其历史 generations
                print "standalone 模式：清理 home-manager 历史 generations..."
                home-manager expire-generations "-0 days"
                # 删除所有历史生成并执行垃圾回收（删除未被引用的 store 路径）
                nix-collect-garbage -d
                # 优化存储层
                nix-store --optimise
            }
            print "--- 彻底清理完成 ---"
        }
        _ => {
            print "用法: nu clean.nu [模式]"
            print "模式:"
            print "  gc   : 普通清理，保留回滚能力"
            print "  all  : 彻底清理，释放最大空间 (不可回滚)"
        }
    }
}
