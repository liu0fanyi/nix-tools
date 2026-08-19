# 官方原样：https://github.com/nix-community/nixos-anywhere-examples/blob/main/hardware-configuration.nix
# 安装时由 nixos-anywhere 在目标机上生成真实硬件配置并覆盖此文件：
#   nixos-anywhere --generate-hardware-config nixos-generate-config ./nixos/hardware-configuration.nix ...
throw "Have you forgotten to run nixos-anywhere with `--generate-hardware-config nixos-generate-config ./nixos/hardware-configuration.nix`?"
