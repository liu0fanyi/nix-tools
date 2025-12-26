{
  description = "Nix Config";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, home-manager, ... }:
    let
      system = "x86_64-linux"; # 如果是 ARM 架构则改为 "aarch64-linux"
      pkgs = nixpkgs.legacyPackages.${system};

      # 动态生成 home-manager 配置的函数
      mkHomeConfig = username: home-manager.lib.homeManagerConfiguration {
        inherit pkgs;
        extraSpecialArgs = {
          inherit username;
        };
        modules = [ ./home-manager/home.nix ];
      };
    in
    {
      homeConfigurations = {
        # 使用 mkHomeConfig 生成配置，用户名作为参数
        "liou" = mkHomeConfig "liou";

        # 添加其他用户时只需一行：
        # "otheruser" = mkHomeConfig "otheruser";
      };
    };
}
