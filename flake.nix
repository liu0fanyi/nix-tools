{
  description = "Nix Config";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    disko = {
      url = "github:nix-community/disko";
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
    # Zen Browser（自动跟随上游更新，GitHub Actions 每日检查）
    zen-browser = {
      url = "github:youwen5/zen-browser-flake";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, home-manager, disko, ... }@inputs:
    let
      system = "x86_64-linux"; # 如果是 ARM 架构则改为 "aarch64-linux"
      pkgs = nixpkgs.legacyPackages.${system};
      username = "liou";

      # 动态生成 home-manager 配置的函数
      mkHomeConfig =
        username: extraModules:
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          extraSpecialArgs = {
            inherit username inputs;
            # standalone（非 NixOS）：显式提供 isNixOS = false
            isNixOS = false;
          };
          modules = [
            ./home-manager/home.nix
          ]
          ++ extraModules;
        };
    in
    {
      homeConfigurations = {
        "liou" = mkHomeConfig "liou" [ ];

        # 添加环境时只需一行：
        # "otheruser" = mkHomeConfig "otheruser" [ ];
      };

      # 192.168.1.15 的 NixOS 配置（nixos-anywhere 远程安装用）
      nixosConfigurations.homebox = nixpkgs.lib.nixosSystem {
        inherit system;
        specialArgs = {
          inherit username inputs;
        };
        modules = [
          inputs.disko.nixosModules.disko
          ./nixos/configuration.nix
          # 官方流程：安装时用
          #   --generate-hardware-config nixos-generate-config ./nixos/hardware-configuration.nix
          # 在目标机上生成并覆盖此文件（当前为官方 throw 占位）
          ./nixos/hardware-configuration.nix
          home-manager.nixosModules.home-manager
          {
            home-manager = {
              useGlobalPkgs = true;
              useUserPackages = true;
              extraSpecialArgs = {
                inherit username inputs;
                # 标记 NixOS 集成，home.nix/niri.nix 据此分流
                # （非 NixOS 的 standalone 配置不传，默认为 false）
                isNixOS = true;
              };
              users.liou = import ./home-manager/home.nix;
            };
          }
        ];
      };
    };
}
