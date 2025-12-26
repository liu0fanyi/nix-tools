#!/usr/bin/env nu

# Nix 环境清理工具
def main [
    mode: string = "help" # 清理模式: gc, all, 或 help
] {
    match $mode {
        "gc" => {
            print "--- 开始普通清理 (保留历史版本) ---"
            # 仅删除当前未被引用的包
            nix-store --gc
            # 优化存储空间：合并相同文件
            nix-store --optimise
            print "--- 普通清理完成 ---"
        }
        "all" => {
            print "--- 开始彻底清理 (删除所有历史版本) ---"
            # 1. 清理 Home Manager 旧版本
            home-manager expire-generations "-0 days"
            # 2. 删除所有历史生成并执行垃圾回收
            nix-collect-garbage -d
            # 3. 优化存储层
            nix-store --optimise
            print "--- 彻底清理完成 ---"
        }
        _ => {
            print "用法: nu clean-nix.nu [模式]"
            print "模式:"
            print "  gc   : 普通清理，保留回滚能力"
            print "  all  : 彻底清理，释放最大空间 (不可回滚)"
        }
    }
}
