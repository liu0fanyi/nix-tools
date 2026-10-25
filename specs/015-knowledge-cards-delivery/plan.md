# 交付方案

Constitution Check：复核工作区、本仓AGENTS/constitution。构建仅PC，目标/删除白名单严格；不改NUC系统/核心/认证、Bevy或其他应用；无新增外部参考、依赖采用正常包管理锁。源码与产品规格独立，本仓仅配套交付。

共用desktop-cache publisher接受明确产品仓库/属性和Pin，只读预演不读凭据；实际构建确定唯一包并推运行闭包，narinfo及签名核验后更新该Pin，回读确认其他Pin不变。凭据仅从既有受保护文件/环境读取，永不进Nix或日志。

PC包和Niri键位只有固定包核验后才接入；完整PC/HM候选验证菜单/快捷键/原生服务注册，不switch。web部署仅产品自己的子目录，支持checksum dry-run；不扩大已有dufs-plus同步删除范围。新文件/证据提交推送和白名单镜像，真实安装/上线/手机验收分开。

现用后端/dist映射固定frontend，应用名白名单无knowledge-cards；不改后端/认证。发布器现将独立固定UI产物组合到固定frontend的knowledge-cards子树，以显式index.html访问；仅prepare既有原生事务，实际apply仍需本轮保存确认。独立可变目录上传不代表上线。只在自有临时副本放开复制自Nix store的目录写权限，不改源store；其他独立应用路径和原生参数保持。
