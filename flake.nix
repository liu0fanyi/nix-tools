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
    # OpenAI Codex CLI（sadjow/codex-cli-nix：社区维护、每小时自动更新、
    # 原生 Rust 二进制 + Cachix 缓存；比 nixpkgs unstable 滞后更少，
    # 见 https://github.com/sadjow/codex-cli-nix）
    codex-cli-nix = {
      url = "github:sadjow/codex-cli-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, home-manager, disko, ... }@inputs:
    let
      system = "x86_64-linux"; # 如果是 ARM 架构则改为 "aarch64-linux"
      pkgs = nixpkgs.legacyPackages.${system};
      username = "liou";

      homeManagerNixosModule = {
        home-manager = {
          useGlobalPkgs = true;
          useUserPackages = true;
          extraSpecialArgs = {
            inherit username inputs;
            # 标记 NixOS 集成，home.nix/niri.nix 据此分流。
            isNixOS = true;
          };
          users.liou = import ./home-manager/home.nix;
        };
      };

      mkNixosConfiguration =
        { installSwapSizeGiB ? null }:
        nixpkgs.lib.nixosSystem {
          inherit system;
          specialArgs =
            {
              inherit username inputs;
            }
            // nixpkgs.lib.optionalAttrs (installSwapSizeGiB != null) {
              inherit installSwapSizeGiB;
            };
          modules =
            [
              inputs.disko.nixosModules.disko
              ./nixos/configuration.nix
              home-manager.nixosModules.home-manager
              homeManagerNixosModule
            ]
            ++ nixpkgs.lib.optional (installSwapSizeGiB != null) ./nixos/install-swap-lv.nix;
        };

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
      # Expose the Home Manager CLI from the same locked input as the modules.
      # `nix run .#home-manager` therefore cannot drift to a registry nixpkgs.
      packages.${system}.home-manager = home-manager.packages.${system}.home-manager;

      homeConfigurations = {
        "liou" = mkHomeConfig "liou" [ ];

        # nuc（家庭 NAT，无公网 IPv4）：额外加载 autossh 反向隧道模块，
        # 让外网能 SSH 进来（经 aliyun VPS 跳板）。
        # nuc 上直接跑 `nu rerun.nu`（rerun.nu 的非 NixOS 分支固定用此配置）。
        "liou-nuc" = mkHomeConfig "liou" [ ./home-manager/nix_modules/nuc-tunnel.nix ];

        # 添加环境时只需一行：
        # "otheruser" = mkHomeConfig "otheruser" [ ];
      };

      # 192.168.1.6 的 NixOS 配置（nixos-anywhere 远程安装用）。
      # hardware-configuration.nix 只保留通用占位；nixos-anywhere 安装时临时生成
      # 目标机版本，脚本退出后恢复占位文件。
      nixosConfigurations.homebox = mkNixosConfiguration { };

      # Fresh nixos-anywhere installs. The script chooses a tier from target RAM.
      nixosConfigurations.homebox-install = mkNixosConfiguration {
        installSwapSizeGiB = 16;
      };
      nixosConfigurations.homebox-install-16g = mkNixosConfiguration {
        installSwapSizeGiB = 16;
      };
      nixosConfigurations.homebox-install-32g = mkNixosConfiguration {
        installSwapSizeGiB = 32;
      };
      nixosConfigurations.homebox-install-24g = mkNixosConfiguration {
        installSwapSizeGiB = 24;
      };
      nixosConfigurations.homebox-install-64g = mkNixosConfiguration {
        installSwapSizeGiB = 64;
      };
    };
}
