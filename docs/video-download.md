# 视频下载（yt-dlp）

Home Manager 安装 yt-dlp，版本跟随本仓库 flake.lock 中的 nixpkgs。
该 Nix 包自带 FFmpeg、Deno 和 yt-dlp-ejs，支持视频与音频处理。

本机配置构建完成后，在普通终端执行：

```bash
cd /home/liou/nix-tools
nu rerun.nu liou --host liu-bigpc
```

下载单个视频到 `~/Videos/YouTube/`（默认选择最佳画质，不展开播放列表）：

```bash
yt-dlp --no-playlist -P ~/Videos/YouTube "视频链接"
```

只提取 MP3 音频：

```bash
yt-dlp --no-playlist -x --audio-format mp3 -P ~/Music/YouTube "视频链接"
```

查看可用格式或下载整个播放列表：

```bash
yt-dlp -F "视频链接"
yt-dlp --yes-playlist -P ~/Videos/YouTube "播放列表链接"
```

不指定 `-P` 时保存到当前目录；输出扩展名由原始媒体格式决定。
链接须加引号，防止 shell 将 `&` 等字符解释为操作符。

版本检查为 `yt-dlp --version`。Nix 管理的包不使用 `yt-dlp -U` 自更新；
若站点改动导致下载失败，维护时更新 nixpkgs 锁定输入，重新验证完整系统并手动切换。
升级 nixpkgs 会影响其他包，应先审核锁定与构建变更。

上游项目与用法：[yt-dlp](https://github.com/yt-dlp/yt-dlp)。
构建通过不代表真实视频已下载；系统激活与网络下载分别验收。
