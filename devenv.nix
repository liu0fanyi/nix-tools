{ pkgs, ... }:
{
  packages = with pkgs; [ python3 just ];
  enterShell = ''
    echo "nix-tools: just deploy nuc|aliyun infra|frontend|tag-server|all"
    echo "预演：just -- deploy nuc all --dry-run"
    echo "NUC 运维：just manage <操作>"
  '';
}
