#!/usr/bin/env nu

# 更新 clipboard-sync 并等待对应 GitHub Actions 成功：
#   nu update-clipboard-sync.nu
#
# 它会把子模块快进到 origin/master，等待该精确提交的 Linux/Cachix 与 Windows
# workflow 成功，然后更新 flake.lock、提交并推送 main。
# 使用 --no-push 可只生成本地提交。
def wait-for-ci [revision: string] {
    if (which gh | is-empty) {
        error make { msg: "需要 GitHub CLI (`gh`) 才能确认 CI；安装并登录后重试，或显式使用 --skip-ci-check" }
    }

    let repo = "liu0fanyi/clipboard-sync"
    let workflow = "nix.yml"
    mut run = {
        databaseId: 0
        status: ""
        conclusion: ""
        headSha: ""
        url: ""
    }
    mut found = false

    print $"等待 GitHub Actions 登记提交 ($revision | str substring 0..11)..."
    for _ in 1..12 {
        let query = (
            gh run list --repo $repo --workflow $workflow --commit $revision --limit 1
                --json databaseId,status,conclusion,headSha,url
            | complete
        )
        if $query.exit_code != 0 {
            let detail = ($query.stderr | str trim)
            error make { msg: $"查询 GitHub Actions 失败：($detail)" }
        }

        let output_type = ($query.stdout | describe)
        let runs = if ($output_type | str starts-with "string") {
            $query.stdout | from json
        } else {
            $query.stdout
        }
        if ($runs | length) > 0 {
            $run = ($runs | first)
            $found = true
            break
        }
        sleep 5sec
    }

    if not $found {
        error make { msg: $"60 秒内未找到提交 ($revision) 对应的 ($workflow)；请检查 workflow 是否触发" }
    }
    if $run.headSha != $revision {
        error make { msg: $"CI revision 不匹配：expected=($revision) actual=($run.headSha)" }
    }

    let run_id = ($run.databaseId | into string)
    print $"等待 CI：($run.url)"
    mut completed = false
    mut succeeded = false
    while not $completed {
        let check = (
            gh run view $run_id --repo $repo --json status,conclusion
            | complete
        )
        if $check.exit_code != 0 {
            let detail = ($check.stderr | str trim)
            error make { msg: $"读取 GitHub Actions 状态失败：($detail)" }
        }
        let state = ($check.stdout | from json)
        if $state.status == "completed" {
            $completed = true
            $succeeded = ($state.conclusion == "success")
        } else {
            sleep 10sec
        }
    }

    if not $succeeded {
        let failed = (gh run view $run_id --repo $repo --log-failed | complete)
        if not ($failed.stdout | str trim | is-empty) {
            print ($failed.stdout | str trim)
        }
        error make { msg: $"clipboard-sync CI 未成功（run ($run_id)），父仓库未更新" }
    }
    print $"CI 已成功：($revision | str substring 0..11)"
}

def main [
    --no-push # 提交后不执行 git push
    --skip-ci-check # 跳过 GitHub Actions 检查（仅用于明确的离线/紧急维护）
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

    if $skip_ci_check {
        print $"(ansi yellow)已显式跳过 CI 检查：($child_rev | str substring 0..11)(ansi reset)"
    } else {
        wait-for-ci $child_rev
    }

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
