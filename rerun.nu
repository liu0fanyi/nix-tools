# 在 ~/nix-config 目录下执行
# 用法: nu rerun.nu [用户名] [--full]
# 示例: nu rerun.nu liou --full=false
def main [username: string = "liou", --full = true, --ddns = true] {
    let suffix_lite = if $full { "" } else { "-lite" }
    let suffix_ddns = if $ddns { "" } else { "-no-ddns" }
    # Construct target: liou, liou-lite, or liou-no-ddns
    # Note: liou-lite currently implies no-ddns in flake.nix, but logic accommodates expansion
    let target = if ($full == false) {
        $"($username)-lite" 
    } else if ($ddns == false) {
        $"($username)-no-ddns"
    } else {
        $username
    }
    
    nix run nixpkgs#home-manager -- switch --flake $".#($target)" -b backup
}
