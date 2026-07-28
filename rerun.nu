# 在 nix-tools 目录下执行
# 用法: nu rerun.nu [用户名]
def main [target: string = "liou"] {
    print $"Deploying Home Manager target: ($target)"
    nix run nixpkgs#home-manager -- switch --flake $".#($target)" -b backup
}
