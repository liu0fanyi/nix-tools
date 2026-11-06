{
  inputs,
  lib,
  pkgs,
  config,
  ...
}:

let
  chatgptFiles = pkgs.stdenvNoCC.mkDerivation {
    pname = "chatgpt-desktop-files";
    version = "latest";
    src = inputs.chatgpt-deb;

    nativeBuildInputs = [ pkgs.dpkg ];
    dontConfigure = true;
    dontBuild = true;

    unpackPhase = ''
      runHook preUnpack
      dpkg-deb -x "$src" unpacked
      runHook postUnpack
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p "$out/bin" "$out/lib"
      cp -a unpacked/usr/bin/. "$out/bin/"
      cp -a unpacked/usr/lib/chatgpt "$out/lib/chatgpt"
      runHook postInstall
    '';
  };

  # Prefer native Wayland for per-output scaling, while retaining X11 support
  # for standalone Home Manager profiles launched outside a Wayland session.
  chatgptLauncher = pkgs.writeShellScript "chatgpt-launcher" ''
    # An absolute Chromium scale, not a multiplier on Wayland output scaling.
    # Also keeps this app readable on the 100% secondary output.
    ${lib.optionalString config.features.desktopScaling.enable ''
      set -- --force-device-scale-factor=${toString config.features.desktopScaling.scale} "$@"
    ''}
    if [ -n "''${WAYLAND_DISPLAY:-}" ]; then
      exec ${chatgptFiles}/bin/chatgpt --ozone-platform=wayland "$@"
    fi
    exec ${chatgptFiles}/bin/chatgpt "$@"
  '';

  chatgptFhs = pkgs.buildFHSEnv {
    name = "chatgpt";
    # fs.cp preserves source modes. Store files are read-only, but Codex edits
    # copied plugin manifests before activating its runtime marketplace.
    # Keep the bundle read-only inside FHS while supplying normal copy modes.
    extraPreBwrapCmds = ''
      ${pkgs.python3}/bin/python3 ${../../scripts/chatgpt-pending-settings.py} || exit 1
      chatgpt_plugin_cache="''${XDG_CACHE_HOME:-$HOME/.cache}/chatgpt/nix-plugin-sources/${baseNameOf chatgptFiles}"
      ${pkgs.coreutils}/bin/mkdir -p -m 700 "$chatgpt_plugin_cache" || exit 1
      (
        set -e
        ${pkgs.util-linux}/bin/flock 9
        if [ ! -d "$chatgpt_plugin_cache/openai-bundled" ]; then
          plugin_stage="$(${pkgs.coreutils}/bin/mktemp -d "$chatgpt_plugin_cache/.staging.XXXXXX")"
          trap '${pkgs.coreutils}/bin/rm -rf -- "$plugin_stage"' EXIT
          ${pkgs.coreutils}/bin/cp -a \
            ${chatgptFiles}/lib/chatgpt/resources/plugins/openai-bundled \
            "$plugin_stage/openai-bundled"
          ${pkgs.coreutils}/bin/chmod -R u+w "$plugin_stage/openai-bundled"
          ${pkgs.coreutils}/bin/mv -- "$plugin_stage/openai-bundled" "$chatgpt_plugin_cache/openai-bundled"
        fi
      ) 9>"$chatgpt_plugin_cache/.lock" || exit 1
    '';
    extraBwrapArgs = [
      ''--ro-bind "$chatgpt_plugin_cache/openai-bundled" "${chatgptFiles}/lib/chatgpt/resources/plugins/openai-bundled"''
    ];
    targetPkgs = p: [
      chatgptFiles
      p.alsa-lib
      p.at-spi2-atk
      p.at-spi2-core
      p.atk
      p.cairo
      p.cups
      p.dbus
      p.expat
      p.fontconfig
      p.freetype
      p.gdk-pixbuf
      p.glib
      p.gsettings-desktop-schemas
      p.gtk3
      p.libdrm
      p.libgbm
      p.libglvnd
      p.libnotify
      p.libpulseaudio
      p.libsecret
      p.libusb1
      p.libX11
      p.libXScrnSaver
      p.libXcomposite
      p.libXcursor
      p.libXdamage
      p.libXext
      p.libXfixes
      p.libXi
      p.libXrandr
      p.libXrender
      p.libXtst
      p.libxcb
      p.libxkbcommon
      p.mesa
      p.nspr
      p.nss
      # buildFHSEnv does not inherit NixOS' NSS modules. Without nssmdns,
      # Codex remote SSH connections cannot resolve hosts such as nuc.local.
      p.nssmdns
      p.pango
      p.pipewire
      p.stdenv.cc.cc.lib
      p.systemd
      p.wayland
      p.xz
      p.zlib
      p.zstd
    ];
    runScript = chatgptLauncher;
  };

  desktopAssets = pkgs.stdenvNoCC.mkDerivation {
    pname = "chatgpt-desktop-assets";
    version = "latest";
    src = inputs.chatgpt-deb;

    nativeBuildInputs = [ pkgs.dpkg ];
    dontConfigure = true;
    dontBuild = true;

    unpackPhase = ''
      runHook preUnpack
      dpkg-deb -x "$src" unpacked
      runHook postUnpack
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p "$out/share/applications" "$out/share/pixmaps" \
        "$out/share/icons/hicolor/256x256/apps"
      cp -a unpacked/usr/share/applications/. "$out/share/applications/"
      # The vendor entry claims generic web URLs; keep Codex deep links but
      # let the real browser handle http(s), including MIME fallback lookup.
      substituteInPlace "$out/share/applications/chatgpt.desktop" \
        --replace-fail 'x-scheme-handler/http;' "" \
        --replace-fail 'x-scheme-handler/https;' ""
      cp -a unpacked/usr/share/pixmaps/. "$out/share/pixmaps/"
      install -Dm644 unpacked/usr/share/pixmaps/chatgpt.png \
        "$out/share/icons/hicolor/256x256/apps/chatgpt.png"
      runHook postInstall
    '';
  };

  chatgptDesktop = pkgs.buildEnv {
    name = "chatgpt-desktop";
    paths = [
      chatgptFhs
      desktopAssets
    ];
    meta = {
      description = "OpenAI ChatGPT desktop app with Codex support";
      homepage = "https://learn.chatgpt.com/docs/linux/linux-app";
      license = lib.licenses.unfree;
      mainProgram = "chatgpt";
      platforms = [ "x86_64-linux" ];
    };
  };
in
{
  home.packages = [ chatgptDesktop ];
}
