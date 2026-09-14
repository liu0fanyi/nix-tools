# 技术方案

复用 deploy/release_pc.py、render.py、迁移与恢复工具。操作说明在 deploy/README.md、deploy/docs 与 nixos/reinstall-checklist.md。

NUC 2026-09-06 最终重启记录已取代“待重装/待恢复”旧段落；它不是本轮服务健康检查。保留最终业务快照及恢复报告的决定不授权本轮再清备份。

## 宪法检查

PC 本地维护和构建；NUC 仅镜像。文档整理不授权系统切换、应用发布、密钥轮换或实机操作。

## Edge 编码修复方案
实测公开JS响应在请求br时标记br，但正文是579026字节未压缩JavaScript，Brotli解码失败。转发子请求显式请求identity，避免读取压缩缓存变体；重新包装fetch正文时去掉旧Content-Encoding/Content-Length，让出站层依据实际正文决定编码及长度，同时去掉源站Alt-Svc。保留状态、其他安全头、认证顺序、POST正文和no-store；无需重建NUC容器。以模拟已解码fetch响应的Node回归覆盖头体一致性，控制台发布后再验公网br/gzip/identity、登录和设备401边界。

## ESP32 静态发布方案

新增 PC Python 发布入口，默认 dry-run，显式 apply 才写入。远端固定目录、命名白名单、symlink 拒绝；版本文件先校验后不可变发布，目录更新持 flock 并比较旧摘要，防并发丢失记录。HTTPS 禁止跨源重定向；镜像回下载校验通过才提交目录，提交后回查目录。只管理静态发布文件，不调用全量部署或改现有容器。Constitution Check：本机打包，服务器仅校验/写静态文件；不写任何 Android/Bevy 目录，无秘密外传。
