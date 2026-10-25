# 知识卡交付配套

产品权威：/data/project/knowledge-cards/specs/001-knowledge-cards。本仓只提供固定PC消费者、Cachix发布/latest Pin、Niri快捷键和独立web部署白名单，不复制产品模型/UI。

- 固定包必须通过真实桌面隔离验证再发布运行闭包；缓存精确路径、可信签名和knowledge-cards-latest（保留1版）核对，原有四个Pin不改变。
- 消费者只引用已发布固定路径；liu-bigpc桌面菜单与Ctrl+Alt+K调用同一包；不代用户system switch。
- 独立网页只拥有NUC /home/liou/dufs-lan/dist/knowledge-cards/，不替换dufs-plus固定根前端、其他应用、后端或数据库；实际部署单独记录，不以构建当上线。
- 既有fcitx5/010用户修改保留且不纳入本次提交。
