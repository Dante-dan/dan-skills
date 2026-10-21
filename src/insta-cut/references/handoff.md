# 选镜 → 剪辑 → 总流程交接

以下是项目文件约定，不是云端接口。文件放当前制作日的 `records/` 或已有项目记录目录；所有交接路径统一相对 `projectRoot` 指定的项目根（不是清单所在目录或制作日目录），并记录 `pathBase: "project-root"`；跨目录的真实原片/应用draft可存明确绝对路径。读取方必须从该根解析，不能按自己的工作目录猜。未观察到的值用 `null` 加缺项说明，不能填示例参数当实测。

## selection.json：insta360-select 输出

镜头传输基本结构示例（保留v1兼容；新批次另补下节故事选镜记录，示例值不是实测）：

```json
{
  "schemaVersion": 1,
  "projectRoot": "/absolute/project",
  "pathBase": "project-root",
  "productionDate": "2026-01-02",
  "status": "ready_for_edit",
  "sources": [{
    "sourceId": "camera-001",
    "shootingDate": "2026-01-01",
    "originalName": "VID_20260101_120000_00_001.insv",
    "originalPath": "shooting-days/2026-01-01/originals/VID_20260101_120000_00_001.insv",
    "sidecarPaths": [],
    "localIntegrity": "passed",
    "sourceFps": "120000/1001",
    "sourceDurationUs": 30000000,
    "studioProject": "production-days/2026-01-02/records/studio-project-location.json"
  }],
  "shots": [{
    "shotId": "s01",
    "sourceId": "camera-001",
    "sourceInUs": 10000000,
    "sourceOutUs": 15000000,
    "status": "ready_for_edit",
    "action": "孩子走近镜头并观察",
    "possibleRoles": ["冷开场", "人物引入"],
    "storyCandidates": ["第一次发现镜头"],
    "originalSoundObservation": "未听；待剪辑阶段确认",
    "adultRisks": ["右后景成人侧脸需覆盖"],
    "reframe": {"tool": "Insta360 Studio", "aspect": "9:16", "parametersRecord": "production-days/2026-01-02/records/s01-reframe.json"},
    "handlesUs": {"before": 500000, "after": 500000},
    "proxyPath": "production-days/2026-01-02/work/proxies/s01.mp4",
    "qualityPath": "production-days/2026-01-02/work/selected/s01-high-quality.mp4",
    "outputFps": "60000/1001",
    "outputSize": [2160, 3840],
    "qualityNote": "重构/升采样限制按实际源片填写"
  }],
  "openItems": []
}
```

- `sourceInUs`包含、`sourceOutUs`不包含，统一对应**原始源片时间轴**，不是剪映时间轴。精确帧号可附 `sourceInFrame/sourceOutFrame` 和所依据时基；在不同帧率之间通过时间换算，不能直接复用帧号。
- `handlesUs`是实际导出额外包含的前后余量，不是口头希望；`qualityPath`时间0通常对应 `sourceInUs - handlesUs.before`，必须以实际导出记录为准。必要时明确 `renderSourceStartUs`，防止剪辑重复裁掉余量或错位音频。
- `candidate`表示仅观察候选；`selected`表示已选时间码；`export_pending`表示未完成可用选段；`ready_for_edit`要求实际文件存在且规格/头尾可用。仅要时间码的用户任务可整体 `selected` 交付，不冒充有导出。
- 源片完整性检查与云核对分开；云状态若需记录只用唯一文件名核对及目标目录，不要求hash。选镜阶段没有匿名化时，成人风险不能填“已遮挡”。

剪辑方先读清单并实际看镜头。完整原片仍可用且用户授权时，可直接读取清单所指区段或请求选镜skill补导出，不为已有有效选段重做整批。只有代理时可制作标明限制的预览，不能直接交最高画质成片。多个视角来自同一源时刻时保持关联，不编成先后发生。

## edit-result.json：insta-edit 输出

每条影片单独记录，允许同一镜头包产生多条实际不同的故事：

```json
{
  "schemaVersion": 1,
  "projectRoot": "/absolute/project",
  "pathBase": "project-root",
  "productionDate": "2026-01-02",
  "title": "第一次发现镜头",
  "version": "v01",
  "status": "independent_review_pending",
  "selectionPath": "production-days/2026-01-02/records/selection.json",
  "usedShotIds": ["s01"],
  "sourceDependencies": ["camera-001"],
  "draft": {"name": "2026-01-02-第一次发现镜头-v01", "path": "应用真实draft路径"},
  "timelineVersion": "v01",
  "previewPath": "production-days/2026-01-02/work/previews/第一次发现镜头-v01-待审.mp4",
  "finalPath": null,
  "actualEncoding": {"size": [2160, 3840], "fps": "60000/1001"},
  "qualityLimitations": [],
  "licensesRecord": "production-days/2026-01-02/records/sources.json",
  "review": {"status": "pending", "reportPath": "production-days/2026-01-02/records/review-v01.json", "missingCapabilities": ["完整实时听音"]},
  "qcRecord": "production-days/2026-01-02/records/qc-v01.json",
  "userApproval": null,
  "publicationAuthorization": null,
  "openItems": ["独立审片尚未完成"]
}
```

状态按实际进度：`editing / preview_exported / independent_review_pending / agent_approved / final_checks_pending / final_verified`。审片报告和本地QC按现有规范绑定确切版本/编码，云备份只看名字的规则不放宽成片审阅。每条独立成片列全实际源依赖，避免清理一个故事时删掉另一个仍需用的源。子skill不把 `agent_approved`或 `final_verified` 写成用户OK。

## insta-cut 接续记录

总流程在项目台账连接两个清单，另外保存：

- `backup`: 原片/侧车、成片、剪映草稿/素材分别记录本地来源、唯一完整文件名、实际云目录、`queued/uploading/name_verified/blocked`及一次核对时间；已核对的直接复用，不下载验证。
- `userApproval`: 实际用户消息、准确片名/版本和明确范围；有问题的新版不能继承旧版OK。
- `cleanup`: 明确路径白名单、授权范围、共享依赖检查、实际删除记录及清理前后可用空间。默认保留本地成片，额外清理依本次真实授权。
- `publication`: 上传、公开发布、用户已自行发布分开记录。未授权公开就只做私有交付；不能因镜头清单完成或云备份存在自动发布。

仅处理归档或接续清理时不再调用Studio或剪辑skill。发现当前缺某一阶段的具体产物才退回相应阶段；已有真实缺项时明确报告，不反复启动同一无能力审片或重复上传。

## 故事与选镜记录扩展

新批次使用 `schemaVersion: 2`；前面的v1示例仍说明路径/时间码传输，不能仅凭该最小示例称已完成故事选镜。读取已有v1清单时复用有效记录，缺项只针对当前需作的选镜/剪辑补齐，已获认可/已发布片不追溯重做。以下字段合并进同一清单，可把长表放单独记录路径，避免重复六份报告：

| 字段 | 内容与判定 |
| --- | --- |
| `coverage` | 每来源 `sourceId`、`visual`和`audio`分别记 `mode/rangesUs/fullyReviewed`，以及未覆盖区间、回看要求。mode如continuous、stills、listened、unavailable；抽帧不称全段已看，音频存在不称已听。 |
| `events` | `eventId/sourceId/sourceInUs/sourceOutUs/eventGroupId/facts/claimKind`，观察方式、动作阶段、关键瞬间、声音/视觉条件及不确定性。claimKind为observed或inference，未知不填成已观察。 |
| `storyCandidates` | 通常2–3条；每条 `storyId/oneSentenceChange/targetAudience/viewerReward/visualConcept/opening/beats/shareReason/shotIds/gaps`，beats给eventIds。仅1条或用户指定方向时用 `candidateLimitReason`解释，不虚构事件凑数。 |
| `selectedStoryId` | 明确所选主线。`opening`含knownContext/viewerQuestion/withheldInformation/payoffShotIds，兑现必须来自实际所选shotIds；时间/因果依据与视觉联想分开。 |
| `shots`新增项 | `eventIds/roles/viewerAddition/removalLoss`，及独立的 `audioSelection`（sourceId/inUs/outUs，未选可null）、手机可读性、关键瞬间、技术限制。roles用hook/context/development/evidence/reaction/payoff/transition/pause。 |
| `relationships` | fromShotId/toShotId/kind/basis：kind为cause_effect、contrast、escalation、question_answer、action_reaction、time_ellipsis或spatial_context。同次反应用basis=observed_same_event并对应同eventGroupId；跨事件因果须basis=documented_causal_link及observed的evidenceEventIds/factBasis，不凭先后断言因果。视觉类比用kind=contrast、basis=associative，不把associative放kind，不伪装现场反应。 |
| `alternatives` | 对每个重要取舍记shotId/alternativeShotId/decision/reason及相邻镜头；候选可未导出，不能因此丢失唯一事件。 |
| `sequenceReview` | status、方法/实际画面与声音覆盖、逐项checks、问题时间码、改动及未审项。纸面串联只称纸面检查；不能代替独立审片。 |
| `audienceBrief` | platform/topic/targetAudience/viewerReward/shareReason/pacePreference；缺平台不阻塞通用制作，平台预设不是算法定义。 |

`insta-edit`的 `edit-result.json` 复用上述当前主线/来源映射，另列 `timelineClips`（clipId、shotId/eventIds、视频/音频源时间、timeline时间、作用与贡献）、段落 `rhythmPlan`（动作/信息/情绪、节奏/切点意图）、`sequenceReview`以及实际 `openingPayoffMapping`（payoffClipIds及兑现时间码）。替代开头与发布反馈有数据时记 `alternateOpening/feedback`，不要求为了字段生成额外影片或读取账号统计。

可选运行 [选镜清单检查器](../../insta360-select/scripts/audit_selection.py)：`python3 .../audit_selection.py /absolute/selection.json --output /absolute/selection-audit.json`。它只检查ID引用、时间范围、覆盖声明和开头兑现是否引用入选镜头等机械约束；不访问视频、不上传、不删文件，不判故事/节奏或观众感受。报告分开 `mechanicalChecks`、`handoffCompleteness`、`mediaReadiness: not_checked`和 `creativeReview: unreviewed`；完整性partial不能当完整交接，音频未听会提示，文件是否存在/实际画面仍由接收方核实。不能当独立审片或用户OK。旧v1仅提示缺少新记录，不使历史认可失效。
