# 特性规格：dsh Web 外网远程访问

**Feature Branch**: `002-dsh-web-remote`

**Created**: 2026-09-10

**Status**: Draft

**Input**: User description: "把根 todo.md 中「外网远程操作 nuc（dsh web 方案）」转成正式规格；同时废除 todo.md，以后统一用 specs。"

## 背景与目标 (Context & Objectives)

当前从外网访问 NUC 只能走 `ssh nuc-remote`（autossh 反向隧道 + 阿里云跳板），交互式打字存在约 60ms RTT 卡顿（homebox → 阿里云 31ms，往返两次）。

本特性目标：让用户在**任意浏览器**中访问运行于 NUC 的 dsh Web GUI，体验优于 SSH 隧道，且**不削弱现有安全边界**。dsh 是完整编程环境（可执行命令、读写文件），公网暴露必须经过认证与安全评估。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 浏览器远程访问 dsh Web (Priority: P1)

用户在外网（无 SSH 客户端、或不便打字）打开浏览器，经域名访问 NUC 上运行的 dsh Web GUI，可正常创建会话、查看 AI 流式输出、使用终端。

**Why this priority**: 这是本特性的核心价值——摆脱 SSH 隧道卡顿，降低外网访问门槛。

**Independent Test**: 从外网浏览器打开专属域名，完成一次 dsh 会话并看到 AI 流式回复，即验证通过。

**Acceptance Scenarios**:

1. **Given** 用户在外网环境，**When** 浏览器打开 dsh 专属域名，**Then** 经认证后进入 dsh Web GUI 界面。
2. **Given** 用户已进入 dsh GUI，**When** 发起一次会触发长时流式输出的会话，**Then** 输出持续增量显示且连接不被 CDN 中断。
3. **Given** 用户使用 dsh 的终端/交互能力，**When** 进行持续交互，**Then** 双向通信稳定、无频繁断连。

---

### User Story 2 - 未认证访问被拒绝 (Priority: P1)

未通过认证的访问者（包括直接访问域名、伪造请求）无法进入 dsh GUI。

**Why this priority**: dsh 等同完整机器权限；未授权访问是最高风险，与 P1 同等关键。

**Independent Test**: 用未认证会话访问域名，确认被拦截在认证页，无法到达 dsh 界面。

**Acceptance Scenarios**:

1. **Given** 访问者未认证，**When** 打开 dsh 域名，**Then** 被要求认证，无法访问 GUI 内容。
2. **Given** 访问者未认证，**When** 直接请求 dsh 的后端路径，**Then** 请求被拒绝而非穿透。

---

### User Story 3 - NUC 重启后服务自动恢复 (Priority: P2)

NUC 重启或 dsh 进程异常退出后，dsh 服务自动恢复，无需人工登录 NUC 手动拉起。

**Why this priority**: 远程访问的价值依赖服务长期可用；但可在 P1 验证后补。

**Independent Test**: 重启 NUC（或 kill dsh 进程），确认服务自动恢复且外网可再次访问。

**Acceptance Scenarios**:

1. **Given** dsh 服务已配置，**When** NUC 重启完成，**Then** dsh 服务自动运行且监听在预期端口。
2. **Given** dsh 进程被异常终止，**When** 等待重启策略生效，**Then** 服务恢复。

---

### User Story 4 - 性能满足日常使用 (Priority: P3)

经 CDN 访问时，AI 流式输出延迟可接受，受 NUC 上行带宽约束但无明显卡顿。

**Why this priority**: 性能是体验目标，但可在功能可用后度量。

**Independent Test**: 从外网发起多次流式会话，记录首字延迟与输出连续性。

**Acceptance Scenarios**:

1. **Given** 用户在外网发起会话，**When** AI 开始输出，**Then** 首字延迟在可接受范围且输出连续无长时间停顿。

---

### Edge Cases

- **CDN 不支持 WebSocket 长连接**时：需要可判定的探测方法，且在结论为"不支持"时有明确回退路径（保留 SSH 隧道方案），不得默认假设可用。
- **认证服务不可用**时：访问必须失败关闭（拒绝访问），不得放行未认证流量。
- **NUC 上行带宽不足**时：需要明确的现象描述与判定，区分"CDN 问题"与"带宽问题"。
- **并发/多标签访问**时：多个浏览器会话不得互相干扰或导致服务崩溃。
- **dsh 版本更新**后：远程入口不得因版本变化而失效（或需明确升级步骤）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 用户 MUST 能通过浏览器经专属域名访问 NUC 上的 dsh Web GUI。
- **FR-002**: 访问 MUST 经过认证方可到达 dsh 界面；未认证请求 MUST 被拒绝（失败关闭）。
- **FR-003**: 系统 MUST 支持 dsh 所需的 WebSocket 长连接，且在所选 CDN 路径下保持稳定（不得仅凭"其他应用的 WS 可用"推断 dsh 可用，MUST 实测）。
- **FR-004**: dsh 服务 MUST 在 NUC 上以声明式配置管理，并具备异常退出后的自动恢复能力。
- **FR-005**: dsh 服务 MUST 仅监听本机回环地址，由前置代理对外暴露（不得直接暴露服务端口）。
- **FR-006**: 认证 MUST 复用现有访问控制体系，并遵循其现有安全强度要求。
- **FR-007**: 本特性 MUST NOT 削弱现有三种访问场景（NUC dufs-lan 认证读写、NUC dufs 密码只读、阿里云匿名只读）的安全边界。
- **FR-008**: 本特性 MUST 产出安全评估结论，明确 dsh 公网暴露的可接受性与缓解措施；评估未通过时 MUST NOT 上线。
- **FR-009**: 必须提供可判定的性能度量结果（首字延迟、输出连续性），作为是否推进的决策依据。
- **FR-010**: 本特性所有产出 MUST 遵循项目宪法，特别是"构建只在 PC 执行"与"不执行 NixOS switch"约束。

### Key Entities

- **远程入口域名**：对外访问 dsh 的地址，需与现有域名体系并存。
- **认证策略**：决定谁能访问 dsh 的规则集合。
- **服务运行单元**：NUC 上承载 dsh 的受管服务。
- **评估记录**：CDN 兼容性、安全评估、性能度量的结论与证据。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 用户从外网浏览器可在 1 分钟内进入 dsh GUI 并开始会话（不含认证输入时间）。
- **SC-002**: 未认证访问 100% 被拒绝，无法到达 dsh 界面（安全测试用例全覆盖）。
- **SC-003**: 一次 5 分钟以上的长时流式会话中，连接中断次数为 0（或不超过可定义的容忍阈值）。
- **SC-004**: NUC 重启后 dsh 服务在无人干预下自动恢复，外网可再次访问（验证 ≥1 次）。
- **SC-005**: 性能度量给出明确的"推进/不推进"结论，且结论有可复现的测量数据支撑。

## Assumptions

- **复用现有架构**：认证与反向代理沿用仓库中已有的部署体系与域名/证书管理方式；本规格只要求"经过认证"，不规定具体实现。
- **dsh 已具备 Web GUI**：dsh 本身提供 Web 界面（已在 PC 验证可用），本特性只解决"如何安全地远程访问"，不涉及 dsh 功能开发。
- **NUC 为运行宿主**：dsh 服务运行于 NUC；PC 仍为唯一构建与配置权威源（宪法原则 I）。
- **CDN 能力待测**：现有 ttyd 走 WebSocket 的经验不能直接推定 dsh 可用，兼容性必须实测（FR-003）。
- **用户规模**：单用户/家庭使用场景，非多租户；不要求复杂权限模型。
- **回退路径**：若 CDN WebSocket 兼容性或安全评估不通过，保留现有 SSH 隧道方案作为回退，本特性可不推进。
- **范围边界**：不含 dsh 本身的功能改造、不含多用户支持、不含移动端 App。

## 与 todo.md 的关系

本规格承接原根目录 `todo.md` 中「🌐 外网远程操作 nuc（dsh web 方案）」一节的 7 项未完成待办。
按项目宪法原则 IV（单源 Spec 规范），`todo.md` 在本特性建立后**废除**，其已完成的历史条目（电源与合盖策略、mihomo 分流、Rime 词库、waybar 模块）为既成事实，不再保留独立清单。
