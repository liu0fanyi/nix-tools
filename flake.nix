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
    in
    {
      homeConfigurations = {
        # 原有的配置
        "liou" = home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          modules = [ ./home-manager/home.nix ];
        };

        # 新环境的配置
        # "otheruser" = home-manager.lib.homeManagerConfiguration {
        #   inherit pkgs;
        #   modules = [ ./home-manager/home.nix ]; # 可以指向不同的 home.nix
        # };
      };
    };
}
