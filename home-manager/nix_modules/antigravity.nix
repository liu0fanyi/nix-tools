{ pkgs, lib, config, inputs, ... }:
let
  cfg = config.features.antigravity;
  system = pkgs.stdenv.hostPlatform.system;
  ag = inputs.antigravity-nix.packages.${system};
in
{
  options.features.antigravity = {
    app.enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Install the Antigravity 2.0 base app (command `antigravity`)";
    };

    ide.enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Install the legacy Antigravity IDE (command `antigravity-ide`).
        Off by default: it is the pre-2.0 product, and Google now steers
        users to the 2.0 base app.
      '';
    };

    cli.enable = lib.mkOption {
      type = lib.types.bool;
      default = config.features.full.enable;
      description = "Install the Antigravity CLI (command `agy`)";
    };

    useFHS = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Use the buildFHSEnv (bubblewrap) variant instead of the autoPatchelf
        one. The FHS sandbox sets no_new_privileges, which breaks `sudo` and
        `pkexec` inside the integrated terminal, so the patched variant is the
        default here.
      '';
    };
  };

  config = lib.mkIf (cfg.app.enable || cfg.ide.enable || cfg.cli.enable) {
    # 来源：github:jacopone/antigravity-nix（见 flake.nix 顶部注释）。
    # 该 flake 把 nixpkgs 作为输入，本仓库让它 follows 自己的 nixpkgs，
    # 所以这里的包与系统其余部分共用同一份 nixpkgs。
    #
    # 三个属性名对应三个不同产品，别混：
    #   google-antigravity      Antigravity 2.0 主应用（本模块默认装这个）
    #   google-antigravity-ide  上一代 IDE，2.0 之后属遗留
    #   google-antigravity-cli  agy 命令行
    # 每个 GUI 包都有 -no-fhs 变体；上面的 useFHS 开关决定选哪个。
    #
    # 依赖 google-chrome（unfree）：GUI 包做浏览器集成，x86_64 上默认用它。
    # 构建期需要 allowUnfree，且运行期若 /run/current-system/sw/bin/google-chrome-stable
    # 不存在会回退到 flake 自带的 google-chrome。本机 allowUnfree 已开启。
    #
    # FHS 变体在 bubblewrap 里跑，会带上 no_new_privileges —— 这正好和本会话
    # 沙箱遇到的限制同源：一旦在集成终端里用 sudo/pkexec 就会失败，所以默认选
    # no-fhs。两个变体都已构建验证。
    home.packages =
      lib.optional cfg.app.enable (
        if cfg.useFHS then ag.google-antigravity else ag.google-antigravity-no-fhs
      )
      ++ lib.optional cfg.ide.enable (
        if cfg.useFHS then ag.google-antigravity-ide else ag.google-antigravity-ide-no-fhs
      )
      ++ lib.optional cfg.cli.enable ag.google-antigravity-cli;
  };
}
