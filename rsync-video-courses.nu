#!/usr/bin/env nu

# 从 4TB My Passport 的正确目录续传到 5TB Art 的正确目录。
# Ctrl+C 可安全中止；再次运行本脚本会利用 .rsync-partial 继续传输。
sudo rsync -rtvh --modify-window=1 --partial --partial-dir=.rsync-partial --info=progress2 "/mnt/my-passport/绘画/视频课程-Nma/" "/mnt/art/绘画/视频课程-Nma/"
