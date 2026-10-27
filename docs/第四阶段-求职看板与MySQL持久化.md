# 第四阶段：求职看板与 MySQL 持久化

> 核对日期：2026-10-27。最初使用 SQLite，当前运行配置已切换为 MySQL；仓储自动化测试仍使用临时 SQLite。第十二阶段已在独立表补充日程，见[第十二阶段说明](第十二阶段-投递日程提醒与面试准备.md)。
> [返回项目说明](../README.md) · [上一阶段](第三阶段-岗位解析与匹配报告.md)

> 后续第六阶段在原五表基础上增加 `draft_versions`。本页的“五表扩展”描述专指第四阶段当时的数据库升级；当前完整结构见[数据库字段说明](数据库设计与字段说明.md)。

> 第七阶段又增加每条投递独立、需显式同意的 `application_sources` 原文留存表；旧投递不自动回填。见[第七阶段说明](第七阶段-原文留存与证据核对.md)。

## 1. 成果总览

| 项目 | 完成的工作 |
| --- | --- |
| 目标 | 保存分析结果，管理多个目标岗位与投递进展 |
| 页面入口 | `/upload` 下方“我的求职看板” |
| 保存入口 | 匹配报告下方“保存岗位与匹配报告” |
| 操作 | 保存、列表、状态筛选、匹配分排序、状态/链接/备注修改、删除 |
| 后端能力 | 增删改查；详情接口可返回完整画像和报告 |
| 存储方案 | MySQL + PyMySQL + SQLAlchemy 2 Core |
| 数据组织 | 五张关联表；`applications` 保留旧 JSON 快照以兼容接口 |
| 模型调用 | CRUD 操作不调用大模型 |

## 2. 具体完成的工作

### 2.1 保存分析快照

前端将当前候选人画像、岗位画像、匹配报告一起提交，附加文件名、匹配服务商和模型名、状态、链接、备注。

每条记录携带保存时的结果。后续修改状态和备注不会重新调用模型或评分。保存的是结构化内容和文件名，不是原始简历文件。

2026-10-21 已扩展为 `resumes`、`jobs`、`match_reports`、`applications`、`application_events`。新保存同步写入关联表，状态变更记录事件；完整字段字典见[数据库设计与字段说明](数据库设计与字段说明.md)。报告表支持同一简历/岗位多条记录，但版本管理 UI 尚未实现。

### 2.2 状态、筛选和排序

六个状态为待投递、已投递、笔试、面试、Offer、已拒绝，可以直接切换，没有强制状态流转顺序。

| 查询参数 | 值 | 功能 |
| --- | --- | --- |
| `status` | 六种状态之一，省略表示全部 | 在数据库查询中筛选 |
| `sort` | `updated_desc` | 最近更新时间倒序，默认 |
| `sort` | `score_desc` | 匹配分从高到低 |
| `sort` | `score_asc` | 匹配分从低到高 |

以上是第四阶段交付时的列表行为。第八阶段另增 `GET /api/applications/search`，在数据库端做关键词搜索、排序和分页；原列表接口保持兼容。详见[第八阶段说明](第八阶段-看板搜索与历史回看.md)。

### 2.3 前端求职看板

- 页面加载时主动读取记录。
- 卡片显示公司、岗位、地点、更新时间和匹配分。
- 下拉框直接修改状态。
- “查看与编辑”展开岗位链接、备注和保存按钮。
- 可打开已保存链接；删除前弹出确认。
- 支持刷新、筛选、排序、空状态与错误提示。
- 采用响应式卡片布局。

当前看板仍是卡片列表，不是拖拽分栏。第八阶段已让“查看与编辑”读取完整历史分析快照和事件时间线，并增加投递日期编辑；本节上方的清单记录第四阶段当时的交付范围。

### 2.4 从 SQLite 改为 MySQL

- 新增 SQLAlchemy、PyMySQL 依赖。
- 原直接使用 `sqlite3` 的仓储改为 SQLAlchemy Core。
- `.env.example` 和配置默认值改为 `mysql+pymysql://`。
- `validated_database_url()` 要求运行配置使用 MySQL + PyMySQL 前缀。
- `create_engine(..., pool_pre_ping=True)` 创建带连接检查的引擎。
- `metadata.create_all()` 创建不存在的表。
- `engine.begin()` 管理写操作事务。

此前规划曾提及 ORM 和 Alembic，当前实际实现是 SQLAlchemy Core 的 `Table` 和增删改查语句，没有 ORM 实体映射，也没有 Alembic 迁移文件。

## 3. 文件清单与作用

路径相对 `D:\Agent`。

| 文件 | 阶段归属 | 职责 |
| --- | --- | --- |
| `job-agent/app/models/application.py` | 本阶段引入 | 状态、新建/更新请求、摘要/详情响应 |
| `job-agent/app/services/application_repository.py` | 本阶段引入，后续改为 MySQL | 表定义、引擎、事务、CRUD、摘要转换和排序 |
| `job-agent/app/api/applications.py` | 本阶段引入 | 五个接口、缓存仓储、记录不存在时返回 404 |
| `job-agent/app/core/config.py` | 扩展已有文件 | 数据库地址和 MySQL 前缀校验 |
| `job-agent/app/main.py` | 扩展已有文件 | 注册投递管理路由 |
| `job-agent/app/static/index.html` | 扩展已有文件 | 保存表单、看板、状态/排序控件 |
| `job-agent/app/static/app.js` | 扩展已有文件 | 保存请求、`loadApplications()`、`createApplicationCard()`、`updateApplication()` |
| `job-agent/app/static/styles.css` | 扩展已有文件 | 保存区、列表、卡片、编辑区、响应式 |
| `job-agent/pyproject.toml` | 扩展已有文件 | SQLAlchemy 和 PyMySQL 依赖 |
| `job-agent/.env.example` | 更新已有模板 | MySQL 连接占位示例 |
| `job-agent/.gitignore` | 复用配置 | 忽略 `.env` 和旧的本地 `*.db` 文件 |
| `job-agent/tests/test_applications_api.py` | 本阶段引入 | 临时数据库 CRUD、非法状态 |
| `job-agent/tests/test_config.py` | 扩展已有测试 | MySQL 配置可用，运行配置拒绝 SQLite 地址 |
| `job-agent/tests/test_frontend.py` | 扩展已有测试 | 保存入口、看板文字与请求代码 |
| `job-agent/scripts/__init__.py` | 测试数据工具新增 | 维护脚本包入口 |
| `job-agent/scripts/seed_applications.py` | 测试数据工具新增 | 构造六种状态的虚构记录，校验结构、事务插入、跳过已有标记并回读 |
| `job-agent/tests/test_seed_applications.py` | 测试数据工具新增 | 验证六种状态、不同分数、重复执行跳过、保留已有数据 |
| `job-agent/app/core/database_schema.py` | 五表扩展新增 | 统一维护表、外键和索引 |
| `job-agent/app/services/application_relations.py` | 五表扩展新增 | 画像复用、岗位/报告快照、事件保存 |
| `job-agent/scripts/init_database.py` | 五表扩展新增 | MySQL 增量建表、旧记录回填、导入与检查 |
| `job-agent/tests/test_database_relations.py` | 五表扩展新增 | 关联、状态事件、投递时间、删除、旧快照保留 |

真实连接信息在本地 `.env` 中，不写入阶段文档或代码仓库。

## 4. 数据模型与表结构

### 4.1 请求响应模型

| 模型 | 用途 |
| --- | --- |
| `ApplicationCreate` | 文件名、画像、报告、模型信息、状态、链接、备注 |
| `ApplicationUpdate` | 局部修改 `status`、`job_url`、`notes` |
| `ApplicationSummary` | 看板摘要及时间信息 |
| `ApplicationDetail` | 摘要加完整画像、报告、来源文件名和模型信息 |

文件名和模型名长度限制为 1～255 字符；链接最多 2000 字符，备注最多 5000 字符。

### 4.2 `applications` 表

| 字段 | SQLAlchemy 类型及约束 | 用途 |
| --- | --- | --- |
| `id` | Integer，主键、自增 | 记录 ID |
| `resume_filename` | String(255)，非空 | 简历文件名 |
| `candidate_profile` | JSON，非空 | 候选人快照 |
| `job_profile` | JSON，非空 | 岗位快照 |
| `match_result` | JSON，非空 | 报告快照 |
| `provider` | String(20)，非空 | 匹配服务商 |
| `model` | String(255)，非空 | 匹配模型 |
| `status` | String(20)，非空、索引 | 投递状态 |
| `job_url` | String(2000)，可空 | 岗位链接 |
| `notes` | Text，可空 | 备注 |
| `created_at` | DateTime，非空 | 创建时间 |
| `updated_at` | DateTime，非空、索引 | 修改时间 |
| `resume_id` | Integer，外键、索引，可空 | 关联简历画像 |
| `job_id` | Integer，外键、索引，可空 | 关联岗位 |
| `match_report_id` | Integer，外键、索引，可空 | 采用的报告 |
| `applied_at` | DateTime，可空 | 首次记录为已投递的时间，旧数据未知时为空 |

兼容接口仍从快照提取公司、岗位、地点、分数和建议。新建的 `jobs` 与 `match_reports` 中已有对应独立列，完整说明见数据库专题文档。

应用以 UTC 生成时间。`DateTime(timezone=True)` 不意味着 MySQL 自动保存时区偏移，跨时区展示仍需统一约定与测试。

## 5. 接口契约

| 方法与路径 | 输入 | 成功响应 |
| --- | --- | --- |
| `POST /api/applications` | 新建记录 JSON | `201`，完整记录 |
| `GET /api/applications` | 可选 `status`、`sort` | `200`，摘要数组 |
| `GET /api/applications/{id}` | 记录 ID | `200`，完整记录 |
| `PATCH /api/applications/{id}` | 局部修改 JSON | `200`，更新后的完整记录 |
| `DELETE /api/applications/{id}` | 记录 ID | `204`，无响应正文 |

详情、修改、删除找不到记录返回 `404`；字段或枚举不合法通常返回 `422`。

更新示例：

```json
{
  "status": "面试",
  "notes": "已收到一面邀请，等待确认时间"
}
```

`exclude_unset=True` 使未提交字段保持原值。链接、备注可用 `null` 清空；显式 `status=null` 现在会被校验器拒绝。状态发生变化时追加事件，链接更新同步岗位表，事务内一起提交。

## 6. 数据流与初始化

```text
两个画像 + 报告 + 用户填写内容
→ POST /api/applications → 请求模型校验
→ ApplicationRepository.create() → MySQL 保存快照
→ 返回完整记录 → 刷新看板

筛选/排序 → GET /api/applications → 查询与摘要转换
→ 渲染卡片 → PATCH 修改 / DELETE 删除
```

`get_repository()` 使用缓存，第一次访问投递管理接口时创建仓储并尝试创建缺失表。已有旧单表必须先运行 `scripts.init_database` 增加关联列，`create_all()` 不会升级旧列。仅启动 FastAPI 不保证数据库已连接或升级成功。

## 7. 配置与使用

```env
DATABASE_URL=mysql+pymysql://job_agent:你的密码@127.0.0.1:3306/job_agent?charset=utf8mb4
```

数据库、用户需预先创建；建表账户要有对应权限，完整步骤见根目录 README。密码中的 URL 特殊字符需编码。

使用步骤：

1. 配置 MySQL 并启动服务。
2. 完成简历画像、岗位解析、匹配报告。
3. 在报告下方填写链接、初始状态和备注并保存。
4. 在看板筛选、排序、修改状态和备注。
5. 刷新页面验证记录仍在，用专门的测试记录验证删除。

原 SQLite 数据不会自动跨库迁移。MySQL 旧单表已有专用增量升级工具 `scripts.init_database`，没有通用 Alembic 版本迁移体系。工具保留旧数据，回填关联并生成迁移状态快照。

## 8. 测试与验证范围

在 `D:\Agent\job-agent` 执行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_applications_api.py tests/test_config.py tests/test_frontend.py
```

测试构造临时 SQLite 文件作为 SQLAlchemy 仓储，替换接口仓储函数，覆盖：

- 新增、列表读取、状态和备注修改、详情、删除后 404。
- 非法状态返回 422。
- MySQL 运行配置格式。
- 前端看板和保存入口存在。

这不验证真实 MySQL 登录、权限、JSON 行为、字符集、时区、网络。多条记录排序和数据库性能也未完整覆盖。

## 9. 当前边界

- 第八阶段已补充前端完整报告快照回看、事件时间线和 `applied_at` 手动编辑；仍没有独立的可视化历史报告页。第十二阶段通过独立 `application_milestones` 表补充面试/截止/跟进日程；未知历史投递日期保持为空，不会从备注推断日程。
- 没有去重或幂等键，重复保存可能生成重复记录。
- 没有登录、用户隔离，当前定位是本地个人使用。
- 数据库地址只校验前缀，数据库异常尚未统一转换为友好响应。
- 链接当前是普通字符串，协议校验待加强。
- 原 `GET /api/applications` 仍是未分页数组；第八阶段另增分页搜索接口供网页使用，不包含全文索引或高级筛选。
- `create_all()` 只创建缺失表，升级旧 MySQL 表需执行 `scripts.init_database`。
- 不包含网站自动投递、定时提醒、历史报告导出。

## 10. 后续维护

### 看板测试数据工具

在 `job-agent` 目录运行 `.\.venv\Scripts\python.exe -m scripts.seed_applications`，使用配置的 MySQL，按 `board-demo-v1-01.txt` 至 `board-demo-v1-06.txt` 标记添加虚构数据。包含六种状态、不同城市和分数、完整画像及报告。标题有 `【测试】`，备注有 `[board-demo-v1]`，不调用真实模型。

导入使用一个事务；单次串行重复执行跳过已有固定文件名，不覆盖记录。投递文件名没有唯一约束，不应并发执行。五表导入同时写关联记录和创建事件；旧库先运行初始化工具。可在看板删除测试记录；重跑会补回样例，独立画像/岗位/报告保留。具体方法见根目录 README。

2026-10-21：临时 SQLite 上的导入与重复运行测试通过，Ruff 检查通过。首次 MySQL 连接因用户名与密码所属账号不匹配而返回 `1045`；根据用户确认修正连接账号后，已在真实 MySQL 插入六条记录（本次 ID 为 1～6）并通过完整回读校验。另使用 FastAPI TestClient 连接真实数据库验证列表、六种状态筛选、分数降序和详情读取。本次未验证真实数据库的修改、删除、并发或浏览器交互，也未调用模型。修改本地连接配置后应重启应用。

### 维护要求

五表扩展实测：真实 MySQL 已完成六条旧投递回填，五表数量为 1/6/6/6/6，重复初始化数量不变。旧记录状态事件标为迁移快照，不虚构过去的流转时间。新增关联、状态更新、删除级联和旧快照保留通过临时 SQLite 测试。第八阶段已接入事件时间线；独立的可视化历史报告页仍未接入。

修改字段时同步请求响应模型、仓储、数据库升级方式、页面和测试；切换数据库时更新本文件、根目录 README 与 `.env.example`，说明旧数据处理方式。必须区分应用测试通过与真实 MySQL 联调成功。
