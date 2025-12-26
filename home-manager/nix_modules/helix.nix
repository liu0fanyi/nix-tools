{ config, pkgs, theme, ... }: {
  programs.helix = {
    enable = true;
    settings = {
      theme = "gruvbox_dark_hard";
      editor = {
        line-number = "relative";
        idle-timeout = 800;
        mouse = false;
        auto-completion = true;
        auto-save = true;
        auto-format = true;
        text-width = 80;
        gutters = [ "diff" "diagnostics" "line-numbers" "spacer" ];
        soft-wrap.enable = true;
        soft-wrap.max-indent-retain = 80;
        file-picker = { hidden = false; };
        statusline = {
          left = [
            "mode"
            "spinner"
            "file-modification-indicator"
            "read-only-indicator"
          ];
          center = [ "file-name" ];
          right = [
            "diagnostics"
            "register"
            "selections"
            "position"
            "file-encoding"
            "file-line-ending"
            "file-type"
          ];
          separator = "│";
          mode.normal = "LOCKED";
          mode.insert = "WORKING";
          mode.select = "VISUAL SEL";
        };
        lsp = {
          enable = true;
          auto-signature-help = true;
          display-messages = true;
          display-inlay-hints = true;
        };
        indent-guides = {
          render = true;
          character = "┊";
          skip-levels = 1;
        };
      };
      keys = {
        normal = {
          # C-s = ":w" # Maps Ctrl-s to the typable command :w which is an alias for :write (save file)
          # "C-*" = "maw*/" # Maps Ctrl-s to the typable command :w which is an alias for :write (save file)
          "C-S-esc" = "extend_line"; # Maps Ctrl-Shift-Escape to extend_line
          # g = { a = "code_action",   d = ["hsplit", "jump_view_up", "goto_definition"] } # Maps `ga` to show possible code actions
          g = { a = "code_action"; }; # Maps `ga` to show possible code actions
          "ret" = [
            "open_below"
            "normal_mode"
          ]; # Maps the enter key to open_below then re-enter normal mode
          C-j = [ "extend_to_line_bounds" "delete_selection" "paste_after" ];
          C-k = [
            "extend_to_line_bounds"
            "delete_selection"
            "move_line_up"
            "paste_before"
          ];
          M = [ "select_mode" "match_brackets" "normal_mode" ];

          # https://github.com/LGUG2Z/helix-vim/blob/master/config.toml
          G = "goto_file_end";
          "%" = "match_brackets";
          "0" = "goto_line_start";
          "$" = "goto_line_end";
          # Search for word under cursor
          "*" = [
            "move_char_right"
            "move_prev_word_start"
            "move_next_word_end"
            "search_selection"
            "search_next"
          ];
          "#" = [
            "move_char_right"
            "move_prev_word_start"
            "move_next_word_end"
            "search_selection"
            "search_prev"
          ];
          # If you want to keep the selection-while-moving behaviour of Helix, this two lines will help a lot,
          # especially if you find having text remain selected while you have switched to insert or append mode
          #
          # There is no real difference if you have overridden the commands bound to 'w', 'e' and 'b' like above
          # But if you really want to get familiar with the Helix way of selecting-while-moving, comment the
          # bindings for 'w', 'e', and 'b' out and leave the bindings for 'i' and 'a' active below. A world of difference!
          i = [ "insert_mode" "collapse_selection" ];
          a = [ "append_mode" "collapse_selection" ];

          D = "kill_to_line_end";

          X = [ "extend_line_up" "extend_to_line_bounds" ];
          A-x = "extend_to_line_bounds";

          # [keys.insert]
          # "A-x" = "normal_mode"     # Maps Alt-X to enter normal mode
          # j = { k = "normal_mode" } # Maps `jk` to exit insert mode
        };
        select = {
          # https://github.com/LGUG2Z/helix-vim/blob/master/config.toml
          G = "goto_file_end";
          "%" = "match_brackets";
          "0" = "goto_line_start";
          "$" = "goto_line_end";
          # Search for word under cursor
          "*" = [
            "move_char_right"
            "move_prev_word_start"
            "move_next_word_end"
            "search_selection"
            "search_next"
          ];
          "#" = [
            "move_char_right"
            "move_prev_word_start"
            "move_next_word_end"
            "search_selection"
            "search_prev"
          ];
          X = [ "extend_line_up" "extend_to_line_bounds" ];
          A-x = "extend_to_line_bounds";
        };
      };
    };
    languages = with pkgs; {
      language-server = {
        nil = {
          command = "${nil}/bin/nil";
          config.nil = {
            # TODO: 没生效
            formatting.command = [ "${nixfmt}/bin/nixfmt" "-q" ];
            nix.flake.autoEvalInputs = true;
          };
        };
        eslint = {
          command = "vscode-eslint-language-server";
          args = [ "--stdio" ];
          config = {
            codeActionsOnSave = {
              mode = "all";
              "source.fixAll.eslint" = true;
            };
            format = { enable = true; };
            nodePath = "";
            quiet = false;
            rulesCustomizations = [ ];
            run = "onType";
            validate = "on";
            experimental = { };
            problems = { shortenToSingleLine = false; };
            codeAction = {
              disableRuleComment = {
                enable = true;
                location = "separateLine";
              };
              showDocumentation = { enable = false; };
            };
          };
        };
        # volar = {
        #   command = "vue-language-server";
        #   args = [ "--stdio" ];
        #   config = {
        #     vue = { hybridmode = true; };
        #     typescript = { tsdk = "./node_modules/typescript/lib"; };
        #   };
        # };
        typescript-language-server.config = {
          plugins = [{
            name = "@vue/typescript-plugin";
            location = "vue-language-server";
            languages = [ "vue" ];
          }];
          vue.inlayHints = {
            includeInlayEnumMemberValueHints = true;
            includeInlayFunctionLikeReturnTypeHints = true;
            includeInlayFunctionParameterTypeHints = true;
            includeInlayParameterNameHints = "all";
            includeInlayParameterNameHintsWhenArgumentMatchesName = true;
            includeInlayPropertyDeclarationTypeHints = true;
            includeInlayVariableTypeHints = true;
          };
        };
        vscode-json-language-server = {
          config = {
            json = {
              validate = { enable = true; };
              format = { enable = true; };
            };
            provideFormatter = true;
          };
        };
        vscode-css-language-server = {
          config = {
            css = { validate = { enable = true; }; };
            scss = { validate = { enable = true; }; };
            less = { validate = { enable = true; }; };
            provideFormatter = true;
          };
        };
      };

      language = [
        # https://github.com/helix-editor/helix/discussions/10691
        # https://www.reddit.com/r/HelixEditor/comments/17kizxs/vue3_usage/ 
        # https://github.com/helix-editor/helix/issues/12493 
        {
          name = "vue";
          # scope = "source.vue";
          # injection-regex = "vue";
          # file-types = [ "vue" ];
          # roots = [ "package.json" ".git" ];
          # auto-format = true;
          # language-servers = [ "volar" "typescript-language-server" ];
          language-servers = [ "typescript-language-server" ];
          formatter = {
            command = "prettier";
            args = [ "--parser" "vue" ];
          };
        }
        {
          name = "typescript";
          language-servers =
            [ "typescript-language-server" "eslint" "emmet-ls" ];
          formatter = {
            command = "prettier";
            args = [ "--parser" "typescript" ];
          };
          # formatter = {
          #   command = "dprint";
          #   args = [ "fmt" "--stdin" "typescript" ];
          # };
          auto-format = true;
        }
        {
          name = "tsx";
          language-servers = [ "eslint" "emmet-ls" ];
          formatter = {
            command = "prettier";
            args = [ "--parser" "typescript" ];
          };
          # formatter = { command = "dprint"; args = [ "fmt", "--stdin", "tsx" ] }
          auto-format = true;
        }

        {
          name = "javascript";
          language-servers =
            [ "typescript-language-server" "eslint" "emmet-ls" ];
          formatter = {
            command = "prettier";
            args = [ "--parser" "typescript" ];
          };
          # formatter = { command = "dprint", args = [ "fmt", "--stdin", "javascript" ] }
          auto-format = true;
        }

        {
          name = "jsx";
          auto-format = true;
          language-servers =
            [ "typescript-language-server" "eslint" "emmet-ls" ];
          formatter = {
            command = "prettier";
            args = [ "--parser" "typescript" ];
          };
          # formatter = { command = "dprint"; args = [ "fmt" "--stdin" "jsx" ]; };
        }
        {
          name = "json";
          auto-format = true;
          formatter = {
            command = "prettier";
            args = [ "--parser" "json" ];
          };
          # formatter = { command = "dprint", args = [ "fmt", "--stdin", "json" ] }
        }

        {
          name = "html";
          auto-format = true;
          language-servers = [ "vscode-html-language-server" "emmet-ls" ];
          formatter = {
            command = "prettier";
            args = [ "--parser" "html" ];
          };
        }
        {
          name = "css";
          auto-format = true;
          language-servers = [ "vscode-css-language-server" "emmet-ls" ];
          formatter = {
            command = "prettier";
            args = [ "--parser" "css" ];
          };
        }
        {
          name = "toml";
          auto-format = true;
          formatter = {
            command = "${taplo}/bin/taplo";
            args = [ "fmt" "-" ];
          };
        }
        {
          name = "bash";
          auto-format = true;
          file-types = [ "sh" "bash" ];
          formatter = { command = "${shfmt}/bin/shfmt"; };
        }
        {
          name = "nix";
          auto-format = true;
          language-servers = [ "nil" ];
        }
      ];
    };
  };
}
