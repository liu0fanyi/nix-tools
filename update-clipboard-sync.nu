#!/usr/bin/env nu

# 在 clipboard-sync 的 Cachix CI 成功后运行：
#   nu update-clipboard-sync.nu
#
# 它会把子模块快进到 origin/master、更新 flake.lock、提交并推送 main。
# 使用 --no-push 可只生成本地提交。
def main [
    --no-push # 提交后不执行 git push
] {
    cd $env.FILE_PWD

    if not (("flake.nix" | path exists) and ("clipboard-sync" | path exists)) {
        error make { msg: "请从 nix-tools 仓库中的脚本运行，未找到 flake.nix 或 clipboard-sync" }
    }

    let branch = (git branch --show-current | str trim)
    if $branch != "main" {
        error make { msg: $"当前父仓库分支是 ($branch)，请切换到 main 后再运行" }
    }

    let lock_changes = (git status --porcelain -- flake.lock | str trim)
    if not ($lock_changes | is-empty) {
        error make { msg: "flake.lock 已有未提交修改，请先处理，避免覆盖现有工作" }
    }

    git submodule update --init clipboard-sync

    let child_changes = (git -C clipboard-sync status --porcelain | str trim)
    if not ($child_changes | is-empty) {
        error make { msg: "clipboard-sync 子仓库有未提交修改，请先提交或处理" }
    }

    print "更新 clipboard-sync 子模块到 origin/master..."
    git -C clipboard-sync fetch origin master
    git -C clipboard-sync switch master
    git -C clipboard-sync merge --ff-only origin/master
    let child_rev = (git -C clipboard-sync rev-parse HEAD | str trim)

    print "更新 flake.lock 的 clipboard-sync-src..."
    nix flake update clipboard-sync-src

    let locked_rev = (open --raw flake.lock | from json | get nodes.clipboard-sync-src.locked.rev)
    if $locked_rev != $child_rev {
        error make {
            msg: $"版本不一致：submodule=($child_rev)，flake.lock=($locked_rev)"
        }
    }

    git add flake.lock clipboard-sync
    let staged = (git diff --cached --quiet | complete)
    if $staged.exit_code == 0 {
        print $"已经是最新版：($child_rev | str substring 0..11)"
        return
    }

    let short_rev = ($child_rev | str substring 0..11)
    git commit -m $"update clipboard-sync to ($short_rev)"

    if $no_push {
        print $"已创建本地提交（($short_rev)），未推送"
    } else {
        git push origin main
        print $"已更新并推送 clipboard-sync：($short_rev)"
    }
}
