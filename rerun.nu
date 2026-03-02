# 在 nix-tools 目录下执行
# 用法: nu rerun.nu [目标/用户名] [--ddns=true/false]
# 示例: 
#   nu rerun.nu liou               (部署已开启 DDNS 的 liou 配置)
#   nu rerun.nu liou --ddns=false  (部署关闭 DDNS 的 liou 配置)
#   nu rerun.nu production         (直接部署生产环境生产配置)
def main [target: string = "liou", --ddns = true] {
    # Determine the actual flake target
    let flake_target = if ($target == "production") {
        "production"
    } else if ($ddns == false) {
        $"($target)-no-ddns"
    } else {
        $target
    }
    
    print $"Deploying target: ($flake_target)"
    nix run nixpkgs#home-manager -- switch --flake $".#($flake_target)" -b backup
}
