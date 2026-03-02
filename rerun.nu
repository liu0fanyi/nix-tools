# 在 ~/nix-config 目录下执行
# 用法: nu rerun.nu [用户名] [--ddns=true/false] [--prod]
# 示例: 
#   nu rerun.nu liou --ddns=false  (局域网开发环境)
#   nu rerun.nu --prod             (生产环境)
def main [username: string = "liou", --ddns = true, --prod = false] {
    # Construct target
    let target = if ($prod == true) {
        "production"
    } else if ($ddns == false) {
        $"($username)-no-ddns"
    } else {
        $username
    }
    
    print $"Deploying target: ($target)"
    nix run nixpkgs#home-manager -- switch --flake $".#($target)" -b backup
}
