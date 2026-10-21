# 默认浏览器

Home Manager 明确将 `http`、`https`、HTML 和 XHTML 的默认应用设为 `zen.desktop`。
Codex/ChatGPT 官方桌面入口同时声明了普通 `http/https`；之前直接复制该入口，
而配置只有磁力和种子默认应用，网页协议会回退选择关联缓存中的 ChatGPT。
参见 [默认应用规范](https://specifications.freedesktop.org/mime-apps/latest/default.html)。

`chatgpt-desktop.nix` 在复制官方入口后移除普通网页协议关联，保留 `codex://`
及文件关联。`home.nix` 固定实际浏览器，避免软件安装顺序影响链接打开程序。

2026-10-10 已即时恢复当前会话：`xdg-settings get default-web-browser` 与
`xdg-mime query default x-scheme-handler/https` 均返回 `zen.desktop`；
Codex 深链接仍指向 `chatgpt.desktop`，磁力链接仍指向 qBittorrent。
原 MIME 配置已备份到 `/tmp`；原有 `mimeapps.list.hm-backup` 改名保留，
避免下一次 HM 激活因已有备份而失败。未执行系统 switch。

完整 liu-bigpc toplevel 与 HM generation 构建通过；检查生成的 mimeapps.list
确认四类网页默认应用为 Zen、磁力关联保留；检查生成的 ChatGPT desktop 确认
不再含 http/https 且仍含 codex 专用协议。

永久配置随用户下一次在普通终端运行以下命令应用：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```
