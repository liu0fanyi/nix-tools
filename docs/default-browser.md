# 默认浏览器

## 文档与表格默认应用（2026-10-31）

Office 默认关联同样由 `home-manager/home.nix` 的 `xdg.mimeApps` 声明。
此前未显式指定 DOCX/XLSX/CSV 等类型，Codex 官方 desktop 又声明支持这些格式，
因此桌面会回退选择 Codex。`~/.config/mimeapps.list` 与旧位置的同名文件由
Home Manager 软链接管理，文件管理器右键修改可能失败或在下一次激活时被覆盖。

现已显式设置 DOCX、DOC、ODT、RTF、ABW 为 AbiWord；XLSX、XLS、XLSM、ODS、
Gnumeric 原生格式、CSV、TSV 为 Gnumeric（desktop ID 为
`org.gnumeric.gnumeric.desktop`）。不改变网页/磁力/Codex 深链接的现有默认值。
MIME 增量反哺脚本保留 MIME 键名大小写，避免 XLSM 的 `macroEnabled` 被转成不同键。

完整 liu-bigpc 系统/HM generation 构建通过，生成配置的14项关联及原有条目均核验。
当前会话已备份旧配置并原子替换用户动态 MIME 文件；14项 `xdg-mime` 查询通过，
GIO 对 DOCX、XLSX、CSV 的默认应用查询与声明一致，无需为此立即系统 switch。
下次正常 switch 会重新建立包含这些声明的受管软链接；未打开或修改用户文档。
本地备份与验证结果留 `/tmp/office-mime-20261031/`。

## 默认浏览器历史记录

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
