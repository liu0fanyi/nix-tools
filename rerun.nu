# 在 ~/nix-config 目录下执行
# 用法: nu rerun.nu [用户名]
# 示例: nu rerun.nu liou
def main [username: string = "liou"] {
    nix run nixpkgs#home-manager -- switch --flake $".#($username)" -b backup
}
