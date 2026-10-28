# AI 求职助手

这是一个基于证据分析简历与实习岗位描述匹配度的 AI Agent 项目。

网页操作入门：[网页端使用指南](网页端使用指南.md)，介绍 `/upload` 页面从上传简历到看板、草稿版本和下载的完整流程。

## 阶段文档索引

根目录 `README.md` 是项目总入口，持续维护当前进度、启动配置、接口索引、测试方法和下一步计划。详细实施说明放在 `docs` 目录，便于快速了解各阶段的成果、文件职责和实现边界。

| 阶段 | 核心成果或规划目标 | 详细说明 |
| --- | --- | --- |
| 第一阶段 | 三种格式简历上传、文本提取和中文页面 | [简历上传与文本解析](docs/第一阶段-简历上传与文本解析.md) |
| 第二阶段 | 两家模型接入、候选人画像和原文证据 | [候选人画像与模型接入](docs/第二阶段-候选人画像与模型接入.md) |
| 第三阶段 | 岗位结构化、五维匹配报告和独立模型选择 | [岗位解析与匹配报告](docs/第三阶段-岗位解析与匹配报告.md) |
| 第四阶段 | 岗位记录保存、投递看板和 MySQL | [求职看板与 MySQL 持久化](docs/第四阶段-求职看板与MySQL持久化.md) |
| 第五阶段 | 定制简历与求职信预览、DOCX/PDF 导出 | [定制简历与求职信](docs/第五阶段-定制简历与求职信.md) |
| 第六阶段 | 人工编辑、草稿版本保存与核对后导出 | [人工编辑与草稿版本](docs/第六阶段-人工编辑与草稿版本.md) |
| 第七阶段 | 授权留存原文、草稿字面证据与版本差异 | [原文留存与证据核对](docs/第七阶段-原文留存与证据核对.md) |
| 第八阶段 | 看板搜索、分页、完整历史报告回看、状态事件时间线与投递日期管理 | [看板搜索与历史回看](docs/第八阶段-看板搜索与历史回看.md) |
| 第九阶段 | 独立简历与岗位资料库、岗位收藏、精确去重、匹配报告历史及重新分析 | [资料库与报告历史](docs/第九阶段-资料库与报告历史.md) |
| 第十阶段 | 用户指定 Greenhouse/Lever 招聘板的岗位发现、筛选、确认导入与来源去重 | [公开岗位发现与导入](docs/第十阶段-公开岗位发现与导入.md) |
| 第十一阶段 | 定制材料标准/精简模板、逐行人工来源关联与保守风险提示 | [材料模板与人工证据标注](docs/第十一阶段-材料模板与人工证据标注.md) |
| 第十二阶段 | 投递截止/面试/跟进日程、站内近期提醒、已确认版本的面试准备提纲 | [投递日程提醒与面试准备](docs/第十二阶段-投递日程提醒与面试准备.md) |
| 第十三阶段 | 本机账号登录、按账号数据隔离、个人数据导出与删除、访问控制 | [账号登录与数据隔离](docs/第十三阶段-账号登录与数据隔离.md) |
| 第十四阶段 | 模型输出离线评估、浏览器端到端测试、本机就绪检查与可选容器配置 | [评估、端到端测试与部署监控](docs/第十四阶段-评估端到端测试与部署监控.md) |

第一至第十四阶段的代码已实现；第十三阶段初始账号升级已由用户在本机执行，真实账号网页登录仍待人工验证。第十四阶段的本机浏览器测试使用虚构账号和临时 SQLite，容器运行尚未验证。已完成的每份说明包含成果总览、文件归属与作用、数据流、接口、测试、限制和维护事项。文件归属按阶段功能梳理，共享文件持续扩展，不等同于某一次提交的精确新增清单。

数据库专题：[十四张表的职责、字段字典、主外键与初始化说明](docs/数据库设计与字段说明.md)。

### 文档维护约定

- 后续功能、接口、配置、依赖或目录变化时，在同一次工作中更新本 README 和对应阶段说明，统一使用中文。
- README 保持总览和运行入口，实现细节与阶段边界放在阶段文档。
- 新增阶段时创建独立说明并补充索引；修改已有阶段时更新文档核对日期。
- 明确区分已实现、提示词约束、待完善和验证范围；不能将模拟测试通过写成真实模型或 MySQL 联调成功。
- 示例只使用占位密钥和密码，不复制 `.env` 中的真实信息。
- 本轮文档核对日期：2026-10-28；第十三阶段的真实库只读复核和第十四阶段的验证边界见下方及各自的独立说明。

## 当前进度

第一阶段的简历上传与文本解析功能已经完成：

- 提供独立的中文简历上传测试页面
- 支持点击选择和拖拽上传文件
- 页面展示文件格式、字符数量和完整提取正文
- 支持 PDF、DOCX 和 TXT 文件
- 单个文件最大 10 MB
- 能够读取 DOCX 段落与表格内容
- TXT 支持 UTF-8 和 GB18030 编码
- 对空文件、损坏文件、不支持格式和无文字 PDF 返回明确错误
- 扫描版 PDF 暂不进行 OCR，会提示用户先完成文字识别；详见[第一阶段说明](docs/第一阶段-简历上传与文本解析.md)

第二阶段的候选人画像功能已经完成：

- 使用 Pydantic 定义严格的候选人画像结构
- 提取基本信息、求职方向、教育、技能、项目、实践、证书与荣誉
- 每项经历和技能可以保留简历原文证据
- 缺失或无法确认的信息通过 `warnings` 返回，不允许模型自行补全
- 提供 `POST /api/resumes/analyze` 结构化分析接口
- 前端页面可以生成并分区展示候选人画像
- 前端分析前可选择使用 OpenAI 或 DeepSeek，选择仅影响当前请求
- 通过同一套 OpenAI Python SDK 支持 OpenAI 和 DeepSeek；详见[第二阶段说明](docs/第二阶段-候选人画像与模型接入.md)

第三阶段的岗位匹配功能已经完成：

- 前端支持粘贴并解析实习岗位描述
- 提取岗位名称、职责、必备技能、加分技能、学历、经验、地点和实习时间要求
- 基于候选人画像和岗位画像生成 0～100 匹配分
- 从技能、项目、教育、实习经历、基本条件五个维度解释评分
- 逐项展示满足、部分满足、不满足或无法确认的岗位要求
- 输出简历证据、匹配优势、关键差距、投递建议和简历优化建议
- 生成匹配报告前可单独选择 OpenAI 或 DeepSeek，不受前面画像分析选择限制
- 优化建议只能调整真实内容的表达与顺序，不允许编造经历
- 提供 `POST /api/jobs/parse` 和 `POST /api/matches/analyze` 接口；详见[第三阶段说明](docs/第三阶段-岗位解析与匹配报告.md)

第四阶段的求职看板已经完成：

- 使用 MySQL 保存岗位画像、候选人画像和完整匹配报告
- 保存岗位链接、个人备注和当前投递状态
- 支持待投递、已投递、笔试、面试、Offer、已拒绝六种状态
- 支持按状态筛选，以及按更新时间或匹配分排序
- 可直接在看板中更新状态、岗位链接和备注
- 支持查看岗位摘要和删除不再需要的记录
- 保存及管理历史报告不会再次调用大模型
- 提供完整的投递记录增删改查接口
- 第四阶段建立 `resumes`、`jobs`、`match_reports`、`applications`、`application_events` 五张基础表；第六阶段另增一张草稿版本表
- 保存新投递时同步建立画像、岗位、报告关联；修改状态时追加事件，保留旧接口快照兼容；详见[第四阶段说明](docs/第四阶段-求职看板与MySQL持久化.md)

第五阶段的定制材料草稿已经完成：

- 在求职看板为已保存岗位生成简历建议稿和求职信草稿，并在页面预览
- 按岗位技能相关度重排已有技能和项目，只引用已保存的候选人画像事实
- 匹配报告的修改建议与正式草稿分开展示，避免把建议写成既有经历
- 两类草稿均可分别下载 DOCX 或 PDF；生成时不调用大模型、不新增数据库表
- 返回原画像警告及投递前核对提示；详见[第五阶段说明](docs/第五阶段-定制简历与求职信.md)

第六阶段的人工定稿流程已经完成：

- 在看板中修改简历与求职信的标题、章节和逐行内容，支持添加、删除章节
- 每次保存创建不可覆盖的新版本；可查看历史、载入旧版作为新版本的编辑起点
- 用户明确核对确认后，才允许下载该版本的 DOCX/PDF；自动生成稿的旧下载接口保持独立
- 新增 `draft_versions` 表保存两份文档和确认时间，原有五张表及投递内容不被重写
- 提供只增建版本表、不导入测试数据的 MySQL 升级脚本；详见[第六阶段说明](docs/第六阶段-人工编辑与草稿版本.md)

第七阶段的原文与版本核对功能已经完成：

- 保存投递时可选择是否留存简历解析正文与岗位描述；默认不留存，旧记录不回填
- 原文按投递保存在 `application_sources`，不写入多个岗位共用的候选人画像行
- 已保存的草稿版本可逐行检查是否与简历/岗位原文有完整字面片段匹配，并显示来源片段；可单独删除留存原文
- 支持比较任意两个已保存版本的简历与求职信文本增删行
- 新增独立 MySQL 升级脚本，不改写旧投递或导入测试数据；详见[第七阶段说明](docs/第七阶段-原文留存与证据核对.md)

第八阶段的看板查找与历史回看已经完成：

- 新增看板关键词搜索、状态组合筛选、数据库端排序与分页；旧列表接口仍可用
- “查看与编辑”可展开保存时的完整候选人画像、岗位画像和匹配报告，以及状态事件时间线
- 可手动设置或清空实际投递日期；改动会产生日期修改事件，未知历史日期不自动推断
- 沿用原七张表和现有字段，不新增数据库迁移；详见[第八阶段说明](docs/第八阶段-看板搜索与历史回看.md)

第九阶段的资料复用与报告历史已经完成：

- `/upload` 新增资料库区，可保存当前候选人画像和岗位画像，并查看已有资料
- 相同画像按结构化内容复用；岗位按规范化链接或完整画像精确去重，可收藏或取消收藏
- 可从资料库选择已有简历和岗位，使用 OpenAI 或 DeepSeek 重新分析并保存新报告；不覆盖旧投递
- 可查看最近 100 条报告历史；仅允许删除没有被报告或投递引用的资料
- 新增 `job_favorites` 收藏表和独立 MySQL 增量脚本；详见[第九阶段说明](docs/第九阶段-资料库与报告历史.md)

第十阶段的公开岗位发现与导入已经完成：

- 网页端可选择 Greenhouse 或 Lever，填写目标公司的 Board / Site 标识后读取该招聘板的公开岗位
- 支持标题/描述关键词、地点和实习字样筛选；预览不保存、不调用大模型
- 用户逐条确认后才用 OpenAI 或 DeepSeek 解析岗位并导入资料库；重复来源跳过模型调用
- 保存来源、招聘板、外部职位 ID、招聘页链接与导入时间；新增 `job_imports` 表和独立升级脚本
- 只访问两家公开 API 的固定域名，不支持全网搜索、任意网址抓取或自动投递；详见[第十阶段说明](docs/第十阶段-公开岗位发现与导入.md)

第十一阶段的材料模板与人工证据标注已经完成：

- 看板生成定制材料前可选标准或精简模板；两者均只使用已保存画像，自动预览与下载参数一致
- 对经同意留存原文的已保存草稿版本，逐行提示未命中与“简历内容只在岗位原文命中”等需重点核对的情况
- 用户可将版本中的某一行人工关联到该投递的简历或岗位原文片段，添加备注；后端核对片段确实存在于所选来源，不将关联当作事实认证
- 来源原文删除时同时删除关联标注；新增 `draft_annotations` 表及独立 MySQL 增量脚本；详见[第十一阶段说明](docs/第十一阶段-材料模板与人工证据标注.md)

第十二阶段的投递日程与面试准备已经完成：

- 看板每条投递可添加、编辑、完成、重新打开或删除截止日期、面试和跟进事项；日程时间按 UTC 保存、按浏览器本地时区展示
- 网页顶部汇总逾期及未来 7 天内的未完成事项；仅打开或刷新页面时读取，没有后台推送或邮件通知
- 已人工确认的草稿版本可生成不调用模型的面试准备提纲，从岗位技能/职责和已确认简历行提供练习线索，不编造回答
- 新增 `application_milestones` 日程表和独立 MySQL 增量脚本；详见[第十二阶段说明](docs/第十二阶段-投递日程提醒与面试准备.md)

第十三阶段的账号与数据隔离代码及现有 MySQL 初始账号升级已经完成：

- `/upload` 增加登录界面、退出、当前账号业务数据 JSON 导出和密码复核后的账号删除
- 所有业务 API 均需有效服务端会话；写请求还需 CSRF 令牌，其他账号的记录无法列出、查看或修改
- 简历、岗位、报告、投递按账号归属；草稿、人工标注、原文和日程跟随所属投递隔离；相同公开来源在不同账号分别导入
- 新增 `users`、`auth_sessions`、`user_assets` 三张表，并调整 `job_imports` 账号归属与唯一约束；已有业务数据须由初始账号认领
- 不开放网页注册或找回密码；初始账号升级、新账号创建及忘记密码后的重置均通过本机交互式脚本完成。详见[第十三阶段说明](docs/第十三阶段-账号登录与数据隔离.md)

第十四阶段的本机质量与运行能力已经实现：

- 三个虚构案例可离线评估简历画像、岗位画像与匹配报告的结构、字面证据和评分一致性；真实模型评估仅在显式指定服务商后运行
- Playwright 使用真实浏览器、临时 SQLite 和虚构账号，覆盖登录、TXT 解析、看板跨账号隔离和退出；普通单元测试默认跳过浏览器用例
- 新增只读 `/ready` 数据库就绪检查、响应请求 ID 和不含查询参数/Cookie 的最小化访问日志
- 提供本机限定端口的可选 Docker Compose 配置，但当前 Docker 引擎未运行，没有完成镜像构建或容器联调。详见[第十四阶段说明](docs/第十四阶段-评估端到端测试与部署监控.md)

### 当前实现边界

- 匹配分由大模型生成；在线业务后端检查范围、五个维度和权重总和，但尚未重新计算总分或逐字核验引用证据。第十四阶段独立评估器可离线检查加权分和字面证据，不改变在线业务校验，也不能证明语义或事实正确。
- 前端“查看与编辑”可回看旧投递快照；第九阶段可在资料库重新分析并新增独立报告，但不会替换旧投递采用的报告，也没有报告版本切换或对比。
- 当前持久化使用 SQLAlchemy Core 和 MySQL，没有 Alembic 迁移；数据库自动化测试使用临时 SQLite。
- 第五阶段自动生成稿只使用数据库里的结构化画像，不含原始简历/JD 全文；第六阶段允许人工编辑和保存，但系统不会核验人工填写的事实。确认时间只代表人工操作，不代表内容已被机器验证。
- 已增加本机账号与数据隔离及本机密码重置，但没有网页自助找回、登录限流或公网部署安全验证，仍不应将含个人信息的服务直接暴露公网。PDF 导出需要本机可用的中文字体。
- 第七阶段证据检查仅是去空白、忽略英文大小写的字面片段查找：简历原文命中、岗位原文命中和未命中都不代表自动事实核验。原始简历文件字节仍不保存。
- 第九阶段资料库只保存结构化画像和报告；重新分析需要所选服务商 API Key，可能产生模型费用。精确去重不是语义识别；第十三阶段起按账号隔离。
- 第十阶段必须由用户提供具体招聘板标识，实习筛选只是关键词启发式；最多展示 100 条结果，Lever 最多读取前三页。导入时岗位描述会发送给所选模型服务商。
- 第十一阶段的精简模板会省略部分事实，模板名不随人工版本单独保存；字面命中、人工片段关联和风险提示都不构成语义或事实核验。人工标注只适用于已授权留存原文的投递。
- 第十二阶段的日程由用户自行录入，提醒只在网页打开或刷新时出现；面试提纲仅从已确认版本挑选复习线索，不能代替人工事实核对或面试准备。
- 第十三阶段初始账号已认领原有资料；真实账号网页登录、写入及删除仍未验证。导出不含密码/API Key，也不等于可直接导入的备份；删除不会清除离线备份。
- 第十四阶段未执行真实模型评估，浏览器测试不连接现有 MySQL；`/ready` 不是业务全链路检查。Docker 配置尚未实际运行，不代表公网生产部署；没有外部监控、告警或自动评估。
- 各阶段说明中列出了更完整的实现限制与后续完善事项。

## 本地运行

推荐直接调用虚拟环境中的 Python，不依赖 PowerShell 激活脚本：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --no-access-log
```

启动后可以访问：

- 前端测试页面：`http://127.0.0.1:8000/upload`
- 接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`
- 数据库就绪检查：`http://127.0.0.1:8000/ready`（需已有账号及第十三阶段库结构）

看板已保存记录可调用 `GET /api/applications/{id}/draft` 预览草稿；下载接口为 `GET /api/applications/{id}/draft/{resume|letter}.{docx|pdf}`。若 PDF 导出返回 503，可设置 `PDF_CJK_FONT_PATH` 指向中文 TTF/TTC 字体后重启应用；Windows 默认尝试系统自带中文字体。

人工版本使用 `POST/GET /api/applications/{id}/draft-versions` 保存和列出；`GET /api/applications/{id}/draft-versions/{version}` 读取；`PATCH .../{version}/review` 提交 `{"confirmed": true}` 后，才能通过 `GET .../{version}/{resume|letter}.{docx|pdf}` 下载该版本。未核对下载返回 409。

第七阶段：保存投递时可显式提交 `retain_source_text: true` 与两份原文；`GET /api/applications/{id}/sources/status` 查看留存状态，`DELETE /api/applications/{id}/sources` 撤回留存。`GET /api/applications/{id}/draft-versions/{version}/evidence` 查看字面证据，`GET /api/applications/{id}/draft-versions/compare?from_version=1&to_version=2` 比较版本。无原文时证据接口返回 409。

第八阶段：`GET /api/applications/search?q=关键词&status=待投递&sort=updated_desc&page=1&page_size=10` 返回分页结果；`GET /api/applications/{id}/events` 返回事件时间线；`PATCH /api/applications/{id}` 可传 `{"applied_at":"2026-10-20"}` 或 `null` 修改实际投递日期。原 `GET /api/applications` 数组接口保持兼容。详见[网页端使用指南](网页端使用指南.md)。

第九阶段：`POST/GET /api/library/resumes` 保存/列出简历画像，`POST/GET /api/library/jobs` 保存/列出岗位，`PATCH /api/library/jobs/{id}/favorite` 切换收藏，`GET /api/library/reports` 查看报告历史，`POST /api/library/reports/reanalyze` 基于已存画像调用模型并保存新报告。完整接口与边界见[第九阶段说明](docs/第九阶段-资料库与报告历史.md)。

第十阶段：`POST /api/discovery/search` 从用户指定的 Greenhouse/Lever 招聘板读取并筛选公开岗位；`POST /api/discovery/imports` 确认后解析并导入单条岗位；`GET /api/discovery/imports` 查看来源记录。预览不写数据库，重复导入不再次调用模型。接口参数与数量上限见[第十阶段说明](docs/第十阶段-公开岗位发现与导入.md)。

第十一阶段：`GET /api/applications/{id}/draft?template=standard|compact` 和自动下载接口可切换模板；版本证据接口新增逐行注意提示及人工关联，`PUT/DELETE /api/applications/{id}/draft-versions/{version}/annotations` 管理关联。详见[第十一阶段说明](docs/第十一阶段-材料模板与人工证据标注.md)。

第十二阶段：`GET /api/planning/reminders?days=7` 返回站内逾期/近期提示；`POST/GET /api/planning/applications/{id}/milestones` 和单项 `PATCH/DELETE` 管理日程；`GET /api/planning/applications/{id}/interview-prep?version=1` 基于已确认版本返回练习提纲。详见[第十二阶段说明](docs/第十二阶段-投递日程提醒与面试准备.md)。

第十三阶段：先运行下文的本机账号升级脚本；`POST /api/auth/login` 登录，`GET /api/auth/me` 获取当前账号和 CSRF 令牌，`POST /api/auth/logout` 退出，`GET /api/auth/export` 导出本账号业务数据，`POST /api/auth/delete` 经密码复核删除。原业务接口均需登录，写请求须附 `X-CSRF-Token`。详见[第十三阶段说明](docs/第十三阶段-账号登录与数据隔离.md)。

如果希望激活虚拟环境，可以在当前 PowerShell 窗口临时放行脚本后再激活：

```powershell
cd D:\Agent\job-agent
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

`Process` 作用域只影响当前 PowerShell 窗口，关闭窗口后自动失效。

## 配置大模型

先复制环境变量示例文件：

```powershell
cd D:\Agent\job-agent
Copy-Item .env.example .env
```

`.env` 已被 Git 忽略，不要把真实 API Key 写入代码、README 或提交记录。

### 使用 OpenAI

编辑 `.env`：

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=你的_OpenAI_API_Key
OPENAI_MODEL=gpt-5.6-luna
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 使用 DeepSeek

编辑 `.env`：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

`LLM_PROVIDER` 是未指定服务商时的默认值。前端页面可以为每次分析单独选择 OpenAI 或 DeepSeek，无需修改 `.env` 或重启服务。项目只支持 `openai` 和 `deepseek`。

如果希望在前端自由切换，请在同一个 `.env` 中同时配置 `OPENAI_API_KEY` 和 `DEEPSEEK_API_KEY`。只配置其中一个 Key 时，仍可使用对应的服务商；选择未配置 Key 的服务商会收到明确提示。

## 解析简历

### 使用前端页面

打开 `http://127.0.0.1:8000/upload`，点击或拖拽上传 PDF、DOCX、TXT 简历，然后点击“开始解析”。页面会显示：

- 文件格式
- 提取字符数量
- 文件处理状态
- 完整简历正文
- 复制正文按钮
- 生成结构化候选人画像
- 在 OpenAI 和 DeepSeek 之间选择本次分析使用的服务商
- 查看技能和经历对应的简历原文证据
- 粘贴并结构化解析岗位描述
- 生成五维匹配评分和针对岗位的简历优化建议
- 保存匹配报告并通过求职看板管理投递进度

### 使用接口文档

打开 `http://127.0.0.1:8000/docs`，在 Swagger 页面中调用：

```text
POST /api/resumes/parse
```

选择 PDF、DOCX 或 TXT 简历文件并执行。成功响应示例：

```json
{
  "filename": "resume.pdf",
  "file_type": "pdf",
  "character_count": 1250,
  "text": "提取出的简历正文"
}
```

简历解析与画像分析相关状态码如下，其中 `502` 和 `503` 属于模型分析接口：

- `400`：文件为空、损坏或无法解析
- `413`：文件超过 10 MB
- `415`：文件格式不受支持
- `422`：文档中没有可提取文字，扫描版 PDF 需要先进行 OCR
- `502`：大模型调用失败、超时或返回的数据不符合画像结构
- `503`：当前服务商的 API Key 未配置

## 候选人画像接口

```text
POST /api/resumes/analyze
```

接口以 `multipart/form-data` 接收简历文件和可选的 `provider` 字段，并返回实际使用的服务商、模型名称和候选人画像。`provider` 可填写 `openai` 或 `deepseek`；省略时使用 `.env` 中的 `LLM_PROVIDER`：

```json
{
  "filename": "resume.pdf",
  "provider": "openai",
  "model": "gpt-5.6-luna",
  "profile": {
    "basic_info": {
      "name": "张晨",
      "email": "zhangchen@example.com",
      "phone": null,
      "location": "上海",
      "links": []
    },
    "job_targets": ["Python 后端开发实习生"],
    "education": [],
    "skills": [],
    "projects": [],
    "experiences": [],
    "certificates": [],
    "warnings": ["简历中未找到手机号码"]
  }
}
```

## 岗位解析与匹配接口

解析岗位描述：

```text
POST /api/jobs/parse
```

请求体为 JSON，`provider` 可以省略：

```json
{
  "description": "岗位职责与任职要求……",
  "provider": "deepseek"
}
```

生成匹配报告：

```text
POST /api/matches/analyze
```

请求体为 JSON：将第二阶段响应的 `profile` 放入 `candidate_profile`，将岗位解析响应的 `profile` 放入 `job_profile`，并提供可选的 `provider`。接口返回总分、投递建议、五个评分维度、岗位要求逐项判断、优势、差距和简历优化建议。

前端使用流程为：上传并解析简历 → 生成候选人画像 → 粘贴岗位描述 → 解析岗位要求 → 生成匹配报告。岗位解析和匹配分析会分别调用一次当前选择的大模型。

岗位解析使用第二阶段模型选择区域中的服务商。岗位解析完成后，第三阶段会在“生成匹配报告”按钮上方显示独立的 OpenAI、DeepSeek 选择项；用户可以为匹配报告重新选择服务商，本次选择只影响匹配分析请求，不需要修改 `.env` 或重启服务。

## 求职看板接口

```text
POST   /api/applications       保存岗位与匹配报告
GET    /api/applications       获取投递记录列表
GET    /api/applications/{id}  获取完整投递记录
PATCH  /api/applications/{id}  更新状态、链接或备注
DELETE /api/applications/{id}  删除投递记录
```

列表接口支持 `status` 和 `sort` 查询参数。`sort` 可选 `updated_desc`、`score_desc` 或 `score_asc`。投递数据保存在 MySQL 中，连接地址通过 `.env` 中的 `DATABASE_URL` 配置。

## 配置 MySQL

项目使用 SQLAlchemy 2 和 PyMySQL 连接 MySQL。请先在 MySQL 中创建数据库和专用账号，下面以 MySQL 8 为例：

```sql
CREATE DATABASE job_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'job_agent'@'localhost' IDENTIFIED BY '请替换为强密码';
GRANT ALL PRIVILEGES ON job_agent.* TO 'job_agent'@'localhost';
FLUSH PRIVILEGES;
```

然后修改 `D:\Agent\job-agent\.env`：

```env
DATABASE_URL=mysql+pymysql://job_agent:你的密码@127.0.0.1:3306/job_agent?charset=utf8mb4
```

如果密码包含 `@`、`:`、`/`、`#` 等特殊字符，需要先进行 URL 编码。数据库和账号需要提前创建。当前代码定义十四张表，现有 MySQL 已完成第十三阶段初始账号升级；其他旧库仍须按下文升级。尚无旧 SQLite 到 MySQL 的跨库迁移脚本。生产环境应使用权限受限的独立账号，不建议直接使用 `root`。

### 完整初始化、旧数据回填与第六阶段升级

以下为第十三阶段之前的历史初始化步骤；只适用于尚无账号的旧库。当前已启用账号的 MySQL 库不要重跑它。其他库若需从更早结构补齐，应在备份、停写并完成各阶段升级后再创建初始账号：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.init_database
```

该命令创建缺失表，给旧投递表添加关联列、外键和索引，回填已有记录，并补齐测试数据。现有 ID、状态、备注和报告快照保留；不会伪造缺失原文或历史投递时间。可以串行重复执行，已回填和已有测试记录会跳过。MySQL 建表/加列会隐式提交，不能视为可整体回滚的事务。完成后重启后端。

已有第四/第五阶段五表库若只需启用第六阶段、避免补导入测试数据，在备份并暂停应用写入后执行：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.upgrade_draft_versions
```

该命令只创建缺失的 `draft_versions` 表并回读现有版本数量，可串行重复执行。完成后重启后端。旧完整初始化脚本仍包含旧数据回填和测试数据导入步骤；账号启用后会拒绝运行。

已有六表库启用第七阶段时，在备份并暂停写入后执行；此命令只增加空的原文留存表，不会替旧记录推断或补填原文：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.upgrade_application_sources
```

已有七表库启用第九阶段岗位收藏时，先备份并暂停应用写入，再执行下面的独立脚本；只增加空的 `job_favorites`，不更改已有岗位、投递或报告：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.upgrade_job_favorites
```

完成后重启后端。MySQL DDL 会隐式提交，不能视为可整体回滚的事务。

已有八表库启用第十阶段来源记录时，先备份并暂停应用写入，再执行只增建 `job_imports` 的脚本；它不会抓取公开岗位或导入测试数据：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.upgrade_job_imports
```

完成后重启后端。岗位查询由用户在网页上明确触发，项目没有后台定时抓取。

已有九表库启用第十一阶段人工证据标注时，先备份并暂停应用写入，再执行只增建 `draft_annotations` 的脚本；它不读取原文或写入示例标注：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.upgrade_draft_annotations
```

完成后重启后端。未同意留存原文的投递不能创建标注。

已有十表库启用第十二阶段投递日程时，先备份并暂停应用写入，再执行只增建 `application_milestones` 的脚本；它不会填入示例截止日期或发送提醒：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.upgrade_application_milestones
```

完成后重启后端。提醒只在页面打开或刷新时查询数据库。

### 第十三阶段：初始账号与历史数据认领

下列命令已由用户在现有 MySQL 库本机执行成功；其他尚未升级的十一表库使用前，先备份数据库，停止应用和其他写入程序，再交互式执行：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.upgrade_user_access
```

脚本提示输入初始用户名、密码并重复确认；不在命令行参数或文档中放密码。它创建缺失的账号表、为 `job_imports` 增加账号归属、把历史简历/岗位/报告/投递和来源记录认领给初始账号，再调整来源唯一约束。应用访问 MySQL 时不会自动建这些表。DDL 不能整体回滚；发生错误应先检查备份和库状态，用同一初始凭据重试。现有库已完成初始账号升级，不要为了登录而重复运行此脚本；重启后端，再打开 `/upload` 登录。其他账号从空资料库开始，可在本机运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.create_user
```

不提供网页自助注册。已有账号后旧 `scripts.init_database` / `scripts.seed_applications` 拒绝向共享库写入；测试资料应在登录后的网页按当前账号创建。详见[第十三阶段说明](docs/第十三阶段-账号登录与数据隔离.md)。

忘记网页账号密码时，不要把明文密码写入 `.env`。能在本机访问数据库配置的管理员可运行以下交互式脚本，输入已有用户名、再次确认用户名，再输入两次新密码。脚本不需要旧密码，成功后只修改该账号的密码哈希，并撤销该账号全部现有会话；其他账号和求职资料不变。完成后用新密码重新登录。

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.reset_user_password
```

新密码不会回显，也不会写入 `.env`、命令行参数或日志。请将密码保存在个人密码管理器中；此脚本只允许可信的本机数据库管理员使用，**不要**通过网页或远程接口开放。

| 表 | 职责 |
| --- | --- |
| `resumes` | 候选人画像，按内容复用 |
| `jobs` | 岗位信息与链接 |
| `match_reports` | 简历与岗位之间的评分报告 |
| `applications` | 当前投递状态、备注与所采用报告，兼容旧快照 |
| `application_events` | 创建、状态变化、迁移时状态快照 |
| `draft_versions` | 人工编辑的简历/求职信版本与核对时间 |
| `application_sources` | 用户明确同意留存的单条投递简历/JD 原文 |
| `job_favorites` | 第九阶段岗位收藏标记，按岗位独立保存 |
| `job_imports` | 第十阶段公开岗位来源身份、链接和导入时间 |
| `draft_annotations` | 第十一阶段草稿单行人工来源关联、引用片段和核对备注 |
| `application_milestones` | 第十二阶段投递截止、面试与跟进日程及完成时间 |
| `users` | 本机账号用户名、密码慢哈希与创建时间 |
| `auth_sessions` | 有效期 12 小时的服务端会话摘要与 CSRF 令牌 |
| `user_assets` | 简历、岗位、报告、投递四类顶层资料的账号归属 |

详细字段类型、是否可空、字段用途、关系与删除规则见[数据库设计与字段说明](docs/数据库设计与字段说明.md)。当前仍没有后台通知、语义级事实核验、跨所有公司的全网搜索、报告版本切换或自动投递。

## 运行测试

通过虚拟环境中的 Python 运行测试：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -m pytest
```

这种方式可以确保调用的是项目虚拟环境中安装的 pytest。如果提示缺少测试依赖，请重新执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

第十四阶段离线评估默认只处理虚构案例、不调用模型；浏览器测试需额外安装可选依赖并显式开启：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_outputs
.\.venv\Scripts\python.exe -m pip install -e ".[dev,e2e]"
.\.venv\Scripts\python.exe -m pytest tests/test_browser_e2e.py --run-browser-e2e -q
```

真实模型评估需主动使用 `--live --provider openai` 或 `--live --provider deepseek`，可能产生费用；本轮未运行。容器部署前需要另行配置被 Git 忽略的 `.env.docker`，参见[第十四阶段说明](docs/第十四阶段-评估端到端测试与部署监控.md)。

## 项目结构

下面的应用和测试路径相对 `job-agent`；各阶段完整文件职责清单见上方文档索引。

```text
app/api/resumes.py                 简历上传接口与请求校验
app/api/applications.py           投递、搜索分页、事件、草稿、版本与证据接口
app/api/library.py                独立资料库、收藏与报告历史接口
app/api/discovery.py              指定公开招聘板的查询、筛选与导入接口
app/api/planning.py               投递日程、站内提醒与面试准备接口
app/models/draft.py              定制材料预览结构
app/models/draft_version.py      人工版本输入、摘要、详情与确认模型
app/models/evidence.py           留存状态、逐行命中和版本对比模型
app/models/annotation.py         人工来源关联请求与响应模型
app/models/planning.py           日程、提醒和面试提纲模型
app/models/library.py            资料保存、收藏、报告历史与重新分析模型
app/models/discovery.py          公开来源、岗位预览与导入响应模型
app/api/jobs.py                    岗位描述解析接口
app/api/matches.py                 简历与岗位匹配接口
app/core/config.py                 OpenAI、DeepSeek 和 MySQL 环境配置
app/core/database_schema.py        十四张表、外键与索引定义
app/core/request_auth.py           会话、同源和 CSRF 校验
app/core/user_scope.py             当前请求账号上下文
app/core/observability.py          请求 ID 与最小化访问日志
app/api/auth.py                    登录、退出、个人数据导出和账号删除接口
app/models/auth.py                 账号请求与响应模型
app/models/candidate.py            候选人画像数据模型
app/models/application.py         投递、分页和事件响应模型
app/models/job.py                  岗位画像数据模型
app/models/match.py                匹配评分数据模型
app/prompts/resume_analysis.py     简历结构化提示词
app/prompts/job_analysis.py        岗位结构化提示词
app/prompts/match_analysis.py      匹配评分提示词
app/services/document_parser.py   PDF、DOCX、TXT 文本解析
app/services/application_repository.py 持久化、搜索分页与事件查询
app/services/library_repository.py 简历/岗位去重、收藏、报告历史与保存
app/services/job_discovery.py     Greenhouse/Lever 公开接口读取与字段标准化
app/services/discovery_repository.py 导入来源去重与记录查询
app/services/application_relations.py 画像复用、报告关联、状态事件
app/services/auth_repository.py   密码慢哈希与服务端会话
app/services/ownership.py         顶层资料归属与账号专属去重键
app/services/personal_data.py     当前账号业务数据导出与删除
app/services/draft_composer.py    根据保存事实组织简历和求职信草稿
app/services/draft_exporter.py    DOCX/PDF 导出及中文 PDF 字体处理
app/services/draft_version_repository.py 人工版本保存、历史查询与确认
app/services/evidence_checker.py  保守字面证据查找与版本文本差异
app/services/annotation_repository.py 单行人工标注保存、读取与删除
app/services/planning_repository.py 日程持久化与实时提醒查询
app/services/interview_preparation.py 已确认版本的面试练习提纲
app/services/llm.py               OpenAI 兼容模型客户端
app/services/resume_analyzer.py   候选人画像分析服务
app/services/job_analyzer.py      岗位描述分析服务
app/services/match_analyzer.py    简历与岗位匹配服务
app/services/evaluation.py        模型输出离线规则评估
app/static/index.html             前端测试页面结构
app/static/styles.css             前端页面样式与响应式布局
app/static/app.js                 上传、画像、匹配、看板与定制材料交互
tests/test_document_parser.py     文档解析单元测试
tests/test_applications_api.py    求职看板、搜索分页、事件与日期测试
tests/test_database_relations.py  关联、旧数据回填与事件测试
tests/test_application_drafts.py  第五阶段草稿与四种文件导出测试
tests/test_draft_versions_api.py  第六阶段版本接口与级联测试
tests/test_evidence_api.py        第七阶段同意留存、证据和差异测试
tests/test_library_api.py         第九阶段资料库与模拟重新分析测试
tests/test_discovery_api.py       第十阶段模拟来源、筛选和去重导入测试
tests/test_stage_eleven.py        第十一阶段模板、人工关联与风险提示测试
tests/test_planning_api.py         第十二阶段日程、提醒和面试准备测试
tests/test_auth_access.py          第十三阶段真实会话、跨账号与个人数据测试
tests/test_password_reset.py       本机重置密码与会话撤销测试
tests/test_evaluation.py           评估规则正反例与命令行默认行为测试
tests/test_browser_e2e.py          真实浏览器登录、解析、隔离与退出测试
tests/test_operational.py          数据库就绪检查与日志最小化测试
tests/test_deployment_config.py    容器配置静态测试
tests/conftest.py                  旧阶段模拟身份与浏览器测试显式开关
evals/cases.json                   三个虚构离线评估案例
Dockerfile / compose.yaml          可选本机容器运行配置
.dockerignore / .env.docker.example 容器构建排除项与占位配置示例
scripts/init_database.py         MySQL 完整增量初始化、回填及检查
scripts/upgrade_draft_versions.py MySQL 只新增草稿版本表
scripts/upgrade_application_sources.py MySQL 只新增原文留存表
scripts/upgrade_job_favorites.py MySQL 只新增岗位收藏表
scripts/upgrade_job_imports.py   MySQL 只新增公开岗位来源表
scripts/upgrade_draft_annotations.py MySQL 只新增草稿标注表
scripts/upgrade_application_milestones.py MySQL 只新增投递日程表
scripts/upgrade_user_access.py     初始账号创建及历史数据认领
scripts/create_user.py             本机交互式创建后续空账号
scripts/reset_user_password.py     本机交互式重置已有账号密码
scripts/evaluate_outputs.py        离线或显式真实模型评估命令
scripts/seed_applications.py     六条虚构测试记录的可重复导入
tests/test_resume_api.py          简历上传接口测试
tests/test_resume_analysis_api.py 候选人画像接口测试
tests/test_job_match_api.py       岗位解析与匹配接口测试
tests/test_match_models.py        匹配评分模型测试
tests/test_frontend.py            前端页面与静态资源测试
```

## 测试简历文件

项目工作区的 `D:\Agent\test` 目录中提供了三种格式的测试简历：

```text
D:\Agent\test\测试简历模板.pdf
D:\Agent\test\测试简历模板.docx
D:\Agent\test\测试简历模板.txt
```

三个文件包含相同的虚构候选人信息，可用于测试文件上传、文本提取、中文编码和 DOCX 表格内容解析。文件中的姓名、联系方式、链接和经历均为测试数据，不能用于真实投递。

## 测试岗位描述文件

项目工作区的 `D:\Agent\test` 目录中提供了一种格式的测试岗位描述：

```text
D:\Agent\test\测试岗位描述.txt
```
岗位描述文件包含一个虚构的岗位描述，内容包含岗位职责、必备技能、加分项、学历要求、实习周期、工作地点和投递材料，可用于测试岗位描述解析、匹配评分和简历优化建议。文件中的岗位描述和职位目标为测试数据，不能用于真实投递。

## 看板数据库测试数据

历史脚本 `job-agent/scripts/seed_applications.py` 曾读取项目 `.env` 的 MySQL 连接信息，向 `applications` 添加六条虚构记录，包含完整候选人画像、岗位画像和匹配报告；账号启用后该脚本拒绝继续向共享库写入。

五表版本的测试导入会同时写入关联表和创建事件；旧库应先运行 `scripts.init_database`。2026-10-21 本次已保留原有六条测试投递并回填：`resumes` 1 条、`jobs` 6 条、`match_reports` 6 条、`applications` 6 条、`application_events` 6 条。六条投递共享相同候选人画像，不再为每个岗位新增相同画像。

| 虚构岗位 | 初始状态 | 测试匹配分 |
| --- | --- | --- |
| Python 后端实习生 | 待投递 | 86 |
| 数据工程实习生 | 已投递 | 72 |
| 测试开发实习生 | 笔试 | 78 |
| AI 应用开发实习生 | 面试 | 90 |
| 平台开发实习生 | Offer | 94 |
| Java 后端实习生 | 已拒绝 | 48 |

以下命令仅供**尚未启用账号的历史库**参考；当前多账号库请勿运行：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -m scripts.seed_applications
```

岗位标题带 `【测试】`，备注带 `[board-demo-v1]`，文件名为 `board-demo-v1-01.txt` 等。分数为人工测试值，模型字段为 `manual-test-fixture`，不会调用大模型。按固定文件名跳过已存在记录，单次串行重复运行不重复插入，也不覆盖手动修改；请勿并发运行。删除某条后重跑会补回该条。

历史运行成功后可在求职看板验证六种状态与分数排序；脚本仅插入缺失的测试记录，不清空业务表。第十三阶段起，应先完成初始账号认领并登录，再查看归属于该账号的既有测试记录。

2026-10-21 验证记录：临时 SQLite 测试验证了插入、重复跳过和已有数据保留，Ruff 检查通过。首次真实 MySQL 连接出现 `1045`，原因是连接用户名与所填密码所属账号不匹配。确认后修正本地连接账号，已向真实 MySQL 插入六条测试记录（本次 ID 为 1～6），回读及完整数据结构校验通过；使用 FastAPI TestClient 连接真实数据库验证了列表、六种状态筛选、匹配分降序和记录详情。此次未调用大模型、未进行浏览器交互测试。

连接字符串中 `://` 后、冒号前是 MySQL 登录用户名，端口后 `/` 后是数据库名，两者可以不同。通过某个账号创建数据库，并不意味着自动创建同名数据库账号；请为连接用户名填写该账号对应的密码。修改 `.env` 后需重启正在运行的应用，使缓存配置生效。

五表升级验证：真实 MySQL 建表、旧记录回填、关系完整性和完整报告回读通过；再次执行初始化没有新增或重复回填。实测五张表共六个外键，现有看板接口的列表、分数排序和详情兼容性通过。应用回归测试 37 项通过，追加的旧快照保留测试及关联重点测试共 6 项通过（临时 SQLite）；Ruff 与文档链接检查通过。此次没有调用大模型，也未进行浏览器操作测试。

2026-10-22 第六阶段验证：完整自动化测试 46 项通过，Ruff 与前端 JavaScript 语法检查通过；版本保存、核对门槛、编辑内容导出和删除级联由临时 SQLite 测试覆盖。真实 MySQL 仅执行了 `scripts.upgrade_draft_versions` 的增量建表和只读检查：原五表计数为 1/6/6/6/6，新表 0 条；确认七个字段、`CASCADE` 外键及 `(application_id, version)` 唯一约束。FastAPI TestClient 读取真实库的投递列表为 200（六条）、版本列表为 200（零条）。没有对真实库写入或确认测试草稿版本，也未调用大模型或进行浏览器操作测试。

2026-10-26 第七阶段验证：完整自动化测试 50 项通过，Ruff、前端脚本语法及差异空白检查通过。真实 MySQL 仅增建 `application_sources` 空表，原六表计数保持 1/6/6/6/6/0，新表 0 条；只读检查确认 `LONGTEXT` 字段和 `CASCADE` 外键。FastAPI TestClient 读取旧投递列表返回 200（六条），原文状态返回 200（未留存）。自动化的同意校验、逐行字面结果、投递隔离、删除留存和版本差异均使用临时 SQLite 与人工文本；没有在真实库保存个人原文，没有调用大模型，也未进行浏览器端到端操作。

2026-10-26 第八阶段验证：完整自动化测试 53 项通过，Ruff、前端脚本语法与差异空白检查通过。新增接口测试使用临时 SQLite 和人工夹具，覆盖搜索分页、排序、旧快照回退、事件与投递日期；真实 MySQL 只执行了不修改数据的分页、关键词/分数排序及事件读取，查询成功。未在真实 MySQL 测试日期写入或删除，未调用大模型，也未进行浏览器端到端操作。

2026-10-27 第九阶段验证：完整自动化测试 57 项通过，Ruff 与前端脚本语法检查通过。新增测试使用临时 SQLite 和模拟匹配模型，覆盖画像/岗位精确复用、收藏切换、引用中的删除保护、报告历史和重新分析不改旧投递。真实 MySQL 已用独立脚本增建空的 `job_favorites`（0 条），只读检查确认两个字段、一个外键，且资料库列表查询成功；没有在真实库保存或删除资料、收藏、生成报告，也没有调用真实大模型或执行浏览器端到端测试。

2026-10-27 第十阶段验证：完整自动化测试 60 项通过，Ruff、前端 JavaScript 语法和差异空白检查通过。新增测试以临时 SQLite、模拟 Greenhouse/Lever 响应和模拟岗位解析器验证来源参数校验、关键词/地点/实习筛选、逐条导入和同源重复跳过模型。真实 MySQL 已用独立脚本增建空的 `job_imports`（0 条），只读检查确认七个字段、`(source, board_token, external_id)` 唯一约束、一个外键及来源列表读取；没有抓取真实招聘板、调用真实大模型、向真实 MySQL 导入岗位或执行浏览器端到端测试。

2026-10-27 第十一阶段验证：完整自动化测试 65 项通过，Ruff、前端 JavaScript 语法和差异空白检查通过。新增测试以临时 SQLite 和人工文本验证模板切换、来源片段校验、标注的投递/版本隔离、风险提示与撤回原文后的清理、删除投递时级联清理，以及升级脚本拒绝 SQLite。真实 MySQL 已用独立脚本增建空的 `draft_annotations`（0 条）；只读检查确认十一列、行定位唯一约束和分别指向 `draft_versions`、`application_sources` 的两个外键；真实库的投递列表与精简草稿只读接口均返回 200。没有在真实 MySQL 写入标注或原文、调用真实大模型或进行浏览器端到端测试。

2026-10-27 第十二阶段验证：完整自动化测试 70 项通过，Ruff、前端 JavaScript 语法、差异空白及本地 Markdown 链接检查通过。新增测试使用临时 SQLite 和人工数据，覆盖日程增删改查、时区要求、逾期/近期提醒、跨投递隔离、完成时间幂等、删除级联和已确认版本的面试提纲。真实 MySQL 日程表在测试隔离修复前被应用自动建表逻辑创建，并误写 9 条虚构日程；已核对 ID、内容与创建时间后精确清理，最终 0 条。独立升级脚本随后幂等执行成功，只读结构检查确认九列和一个外键；真实库提醒与单条投递日程列表只读接口均返回 200，提醒为空。没有保留测试日程或修改原有投递，也没有真实模型调用、后台通知或浏览器端到端测试。

2026-10-27 第十三阶段验证：完整自动化测试 **75 项通过**，Ruff、前端 JavaScript 语法、差异空白和本地 Markdown 链接检查通过。新增测试使用临时 SQLite 和 TestClient，覆盖真实登录、CSRF、登出、跨账号记录访问、资料去重、来源去重、个人数据导出与删除；旧阶段测试以模拟身份回归。真实 MySQL **未执行**第十三阶段账号迁移或登录/删除联调，未调用真实模型，也未做浏览器端到端或公网安全测试。

2026-10-28 升级前只读复核：数据库可连接，当时已有 14 张表（其中 `users`、`auth_sessions`、`user_assets` 均为 0 行），`job_imports` 仍无 `user_id` 列、使用旧唯一约束；投递记录 7 条，三个关联 ID 均非空。该检查没有执行写入。历史章节中 2026-10-27 的投递数量仅代表当时状态。

2026-10-28 用户在本机交互式运行 `scripts.upgrade_user_access` 成功，脚本报告认领 `resumes` 2、`jobs` 7、`match_reports` 7、`applications` 7 条。随后只读复核确认：`users` 1 行、`user_assets` 23 行，四类归属数与业务表数量一致且均归属初始账号；`job_imports.user_id` 非空，唯一约束为 `(user_id, source, board_token, external_id)`，旧唯一约束已移除。真实库 API 只读检查：`/api/auth/status` 返回 200 且已配置，未登录读取投递返回 401，`/upload` 返回 200。未获取或使用登录密码，因此**未验证真实账号登录、登录后读取、写入、导出或删除**；本轮复核未向真实库写入测试数据。

2026-10-28 本机密码重置脚本新增验证：完整自动化测试 **79 项通过**，Ruff 和差异空白检查通过。新增临时 SQLite 测试覆盖指定账号密码更新、该账号全部会话失效、其他账号保持有效、无效账号/短密码不修改数据，以及终端用户名二次确认；文档本地链接已核对。没有在真实 MySQL 上重置现有账号密码，也没有读取用户密码。

2026-10-28 第十四阶段验证：普通自动化测试 **88 项通过、1 项按设计跳过**；另行显式启动的本机 Edge 浏览器端到端用例 **1 项通过**，使用临时 SQLite、虚构账号和本机随机端口，覆盖登录、TXT 解析、看板数据隔离与退出。三个虚构案例的离线模型输出评估 **3/3 通过**。Ruff 与差异空白检查通过。对现有真实 MySQL 只调用 `GET /ready`，返回 200 `{"status":"ready"}`；没有用真实账号网页登录、写入/删除数据或调用 OpenAI/DeepSeek。Docker 引擎未运行，容器配置仅做静态测试，未构建或启动镜像；没有公网部署或外部监控联调。

## 下一阶段

建议先用初始账号在 `/upload` 人工登录，确认能看到原有 7 条投递；如需容器化，再启动 Docker 引擎并按[第十四阶段说明](docs/第十四阶段-评估端到端测试与部署监控.md)配置受限数据库账号，验证镜像与就绪探针。后续可扩充 PDF/DOCX、模型结果和材料下载的浏览器用例，增加更多人工审核过的评估案例及安全措施。当前没有语义级事实核验、一键投递或自动发送功能；投递辅助也不等于自动向招聘平台提交申请。
