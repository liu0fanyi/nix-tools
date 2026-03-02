{
  description = "Nix Config";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nix-gl = {
      url = "github:nix-community/nixGL";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    niri = {
      url = "github:YaLTeR/niri";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, home-manager, ... }@inputs:
    let
      system = "x86_64-linux"; # 如果是 ARM 架构则改为 "aarch64-linux"
      pkgs = nixpkgs.legacyPackages.${system};

      # 动态生成 home-manager 配置的函数
      mkHomeConfig =
        username: extraModules:
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          extraSpecialArgs = {
            inherit username inputs;
          };
          modules = [
            ./home-manager/home.nix
          ]
          ++ extraModules;
        };
    in
    {
      homeConfigurations = {
        # 使用 mkHomeConfig 生成配置，用户名作为参数
        # 现在通过传递模块列表来灵活开启功能，比 Boolean 切关更优雅
        "liou" = mkHomeConfig "liou" [ ./home-manager/nix_modules/ddns-go.nix ];
        "liou-no-ddns" = mkHomeConfig "liou" [ ];

        # 添加环境时只需一行：
        # "otheruser" = mkHomeConfig "otheruser" [ ];

        # 生产服务器配置 (剥离所有桌面/GUI 工具，仅保留 Dufs/Tag/Caddy 服务)
        "production" = home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          extraSpecialArgs = {
            username = "root"; # 生产环境默认用户
            inherit inputs;
          };
          modules = [
            # 仅加载服务核心模块，忽略主 home.nix 重型配置
            ./home-manager/nix_modules/podman-prod.nix
            ./home-manager/nix_modules/caddy-prod.nix
            {
              home.username = "root";
              home.homeDirectory = "/root";
              home.stateVersion = "24.05";
              targets.genericLinux.enable = true;
              nixpkgs.config.allowUnfree = true;
            }
          ];
        };
      };
    };
}
