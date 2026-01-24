# 在 ~/nix-config 目录下执行
# 用法: nu rerun.nu [用户名] [--full]
# 示例: nu rerun.nu liou --full=false
def main [username: string = "liou", --full = true] {
    let target = if $full { $username } else { $"($username)-lite" }
    nix run nixpkgs#home-manager -- switch --flake $".#($target)" -b backup
}
