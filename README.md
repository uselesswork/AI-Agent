# AI 求职助手

这是一个基于证据分析简历与实习岗位描述匹配度的 AI Agent 项目。

## 阶段文档索引

根目录 `README.md` 是项目总入口，持续维护当前进度、启动配置、接口索引、测试方法和下一步计划。详细实施说明放在 `docs` 目录，便于快速了解各阶段的成果、文件职责和实现边界。

| 阶段 | 核心成果 | 详细说明 |
| --- | --- | --- |
| 第一阶段 | 三种格式简历上传、文本提取和中文页面 | [简历上传与文本解析](docs/第一阶段-简历上传与文本解析.md) |
| 第二阶段 | 两家模型接入、候选人画像和原文证据 | [候选人画像与模型接入](docs/第二阶段-候选人画像与模型接入.md) |
| 第三阶段 | 岗位结构化、五维匹配报告和独立模型选择 | [岗位解析与匹配报告](docs/第三阶段-岗位解析与匹配报告.md) |
| 第四阶段 | 岗位记录保存、投递看板和 MySQL | [求职看板与 MySQL 持久化](docs/第四阶段-求职看板与MySQL持久化.md) |
| 第五阶段 | 定制简历与求职信预览、DOCX/PDF 导出 | [定制简历与求职信](docs/第五阶段-定制简历与求职信.md) |
| 第六阶段 | 人工编辑、草稿版本保存与核对后导出 | [人工编辑与草稿版本](docs/第六阶段-人工编辑与草稿版本.md) |
| 第七阶段 | 授权留存原文、草稿字面证据与版本差异 | [原文留存与证据核对](docs/第七阶段-原文留存与证据核对.md) |

每份说明包含成果总览、文件归属与作用、数据流、接口、测试、限制和维护事项。文件归属按阶段功能梳理，共享文件持续扩展，不等同于某一次提交的精确新增清单。

数据库专题：[七张表的职责、字段字典、主外键与初始化说明](docs/数据库设计与字段说明.md)。

### 文档维护约定

- 后续功能、接口、配置、依赖或目录变化时，在同一次工作中更新本 README 和对应阶段说明，统一使用中文。
- README 保持总览和运行入口，实现细节与阶段边界放在阶段文档。
- 新增阶段时创建独立说明并补充索引；修改已有阶段时更新文档核对日期。
- 明确区分已实现、提示词约束、待完善和验证范围；不能将模拟测试通过写成真实模型或 MySQL 联调成功。
- 示例只使用占位密钥和密码，不复制 `.env` 中的真实信息。
- 本轮文档核对日期：2026-10-26；第七阶段的验证范围见下方及独立阶段说明。

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
- 扫描版 PDF 暂不进行 OCR，会提示用户先完成文字识别

第二阶段的候选人画像功能已经完成：

- 使用 Pydantic 定义严格的候选人画像结构
- 提取基本信息、求职方向、教育、技能、项目、实践、证书与荣誉
- 每项经历和技能可以保留简历原文证据
- 缺失或无法确认的信息通过 `warnings` 返回，不允许模型自行补全
- 提供 `POST /api/resumes/analyze` 结构化分析接口
- 前端页面可以生成并分区展示候选人画像
- 前端分析前可选择使用 OpenAI 或 DeepSeek，选择仅影响当前请求
- 通过同一套 OpenAI Python SDK 支持 OpenAI 和 DeepSeek

第三阶段的岗位匹配功能已经完成：

- 前端支持粘贴并解析实习岗位描述
- 提取岗位名称、职责、必备技能、加分技能、学历、经验、地点和实习时间要求
- 基于候选人画像和岗位画像生成 0～100 匹配分
- 从技能、项目、教育、实习经历、基本条件五个维度解释评分
- 逐项展示满足、部分满足、不满足或无法确认的岗位要求
- 输出简历证据、匹配优势、关键差距、投递建议和简历优化建议
- 生成匹配报告前可单独选择 OpenAI 或 DeepSeek，不受前面画像分析选择限制
- 优化建议只能调整真实内容的表达与顺序，不允许编造经历
- 提供 `POST /api/jobs/parse` 和 `POST /api/matches/analyze` 接口

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
- 保存新投递时同步建立画像、岗位、报告关联；修改状态时追加事件，保留旧接口快照兼容

第五阶段的定制材料草稿已经完成：

- 在求职看板为已保存岗位生成简历建议稿和求职信草稿，并在页面预览
- 按岗位技能相关度重排已有技能和项目，只引用已保存的候选人画像事实
- 匹配报告的修改建议与正式草稿分开展示，避免把建议写成既有经历
- 两类草稿均可分别下载 DOCX 或 PDF；生成时不调用大模型、不新增数据库表
- 返回原画像警告及投递前核对提示；完整边界见[第五阶段说明](docs/第五阶段-定制简历与求职信.md)

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

### 当前实现边界

- 匹配分由大模型生成；后端检查范围、五个维度和权重总和，但尚未重新计算总分或逐字核验引用证据。
- 第四阶段详情接口可以读取完整历史报告；前端“查看与编辑”目前仅展开链接和备注，尚未实现完整历史报告回看。
- 当前持久化使用 SQLAlchemy Core 和 MySQL，没有 Alembic 迁移；数据库自动化测试使用临时 SQLite。
- 第五阶段自动生成稿只使用数据库里的结构化画像，不含原始简历/JD 全文；第六阶段允许人工编辑和保存，但系统不会核验人工填写的事实。确认时间只代表人工操作，不代表内容已被机器验证。
- 当前是无登录的单用户本地应用，不应将含个人信息的接口直接暴露公网。PDF 导出需要本机可用的中文字体。
- 第七阶段证据检查仅是去空白、忽略英文大小写的字面片段查找：简历原文命中、岗位原文命中和未命中都不代表自动事实核验。原始简历文件字节仍不保存。
- 各阶段说明中列出了更完整的实现限制与后续完善事项。

## 本地运行

推荐直接调用虚拟环境中的 Python，不依赖 PowerShell 激活脚本：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

启动后可以访问：

- 前端测试页面：`http://127.0.0.1:8000/upload`
- 接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

看板已保存记录可调用 `GET /api/applications/{id}/draft` 预览草稿；下载接口为 `GET /api/applications/{id}/draft/{resume|letter}.{docx|pdf}`。若 PDF 导出返回 503，可设置 `PDF_CJK_FONT_PATH` 指向中文 TTF/TTC 字体后重启应用；Windows 默认尝试系统自带中文字体。

人工版本使用 `POST/GET /api/applications/{id}/draft-versions` 保存和列出；`GET /api/applications/{id}/draft-versions/{version}` 读取；`PATCH .../{version}/review` 提交 `{"confirmed": true}` 后，才能通过 `GET .../{version}/{resume|letter}.{docx|pdf}` 下载该版本。未核对下载返回 409。

第七阶段：保存投递时可显式提交 `retain_source_text: true` 与两份原文；`GET /api/applications/{id}/sources/status` 查看留存状态，`DELETE /api/applications/{id}/sources` 撤回留存。`GET /api/applications/{id}/draft-versions/{version}/evidence` 查看字面证据，`GET /api/applications/{id}/draft-versions/compare?from_version=1&to_version=2` 比较版本。无原文时证据接口返回 409。

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

如果密码包含 `@`、`:`、`/`、`#` 等特殊字符，需要先进行 URL 编码。数据库和账号需要提前创建。项目支持 MySQL 旧单表升级为第四阶段五表，并在第六阶段新增草稿版本表；尚无旧 SQLite 到 MySQL 的跨库迁移脚本。生产环境应使用权限受限的独立账号，不建议直接使用 `root`。

### 完整初始化、旧数据回填与第六阶段升级

旧 MySQL 库升级或新库初始化时，在暂停应用写入后执行：

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

该命令只创建缺失的 `draft_versions` 表并回读现有版本数量，可串行重复执行。完成后重启后端。完整初始化脚本现在会创建全部七张表，但仍包含旧数据回填和测试数据导入步骤。

已有六表库启用第七阶段时，在备份并暂停写入后执行；此命令只增加空的原文留存表，不会替旧记录推断或补填原文：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -X utf8 -m scripts.upgrade_application_sources
```

| 表 | 职责 |
| --- | --- |
| `resumes` | 候选人画像，按内容复用 |
| `jobs` | 岗位信息与链接 |
| `match_reports` | 简历与岗位之间的评分报告 |
| `applications` | 当前投递状态、备注与所采用报告，兼容旧快照 |
| `application_events` | 创建、状态变化、迁移时状态快照 |
| `draft_versions` | 人工编辑的简历/求职信版本与核对时间 |
| `application_sources` | 用户明确同意留存的单条投递简历/JD 原文 |

详细字段类型、是否可空、字段用途、关系与删除规则见[数据库设计与字段说明](docs/数据库设计与字段说明.md)。已有结构和兼容写入，不代表独立简历管理、报告历史或事件时间线页面已实现。

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

## 项目结构

下面的应用和测试路径相对 `job-agent`；各阶段完整文件职责清单见上方文档索引。

```text
app/api/resumes.py                 简历上传接口与请求校验
app/api/applications.py           投递、草稿、版本、原文状态与字面证据接口
app/models/draft.py              定制材料预览结构
app/models/draft_version.py      人工版本输入、摘要、详情与确认模型
app/models/evidence.py           留存状态、逐行命中和版本对比模型
app/api/jobs.py                    岗位描述解析接口
app/api/matches.py                 简历与岗位匹配接口
app/core/config.py                 OpenAI、DeepSeek 和 MySQL 环境配置
app/core/database_schema.py        七张表、外键与索引定义
app/models/candidate.py            候选人画像数据模型
app/models/application.py         投递记录数据模型
app/models/job.py                  岗位画像数据模型
app/models/match.py                匹配评分数据模型
app/prompts/resume_analysis.py     简历结构化提示词
app/prompts/job_analysis.py        岗位结构化提示词
app/prompts/match_analysis.py      匹配评分提示词
app/services/document_parser.py   PDF、DOCX、TXT 文本解析
app/services/application_repository.py MySQL 持久化服务
app/services/application_relations.py 画像复用、报告关联、状态事件
app/services/draft_composer.py    根据保存事实组织简历和求职信草稿
app/services/draft_exporter.py    DOCX/PDF 导出及中文 PDF 字体处理
app/services/draft_version_repository.py 人工版本保存、历史查询与确认
app/services/evidence_checker.py  保守字面证据查找与版本文本差异
app/services/llm.py               OpenAI 兼容模型客户端
app/services/resume_analyzer.py   候选人画像分析服务
app/services/job_analyzer.py      岗位描述分析服务
app/services/match_analyzer.py    简历与岗位匹配服务
app/static/index.html             前端测试页面结构
app/static/styles.css             前端页面样式与响应式布局
app/static/app.js                 上传、画像、匹配、看板与定制材料交互
tests/test_document_parser.py     文档解析单元测试
tests/test_applications_api.py    求职看板接口与数据库测试
tests/test_database_relations.py  关联、旧数据回填与事件测试
tests/test_application_drafts.py  第五阶段草稿与四种文件导出测试
tests/test_draft_versions_api.py  第六阶段版本接口与级联测试
tests/test_evidence_api.py        第七阶段同意留存、证据和差异测试
scripts/init_database.py         MySQL 完整增量初始化、回填及检查
scripts/upgrade_draft_versions.py MySQL 只新增草稿版本表
scripts/upgrade_application_sources.py MySQL 只新增原文留存表
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

新增 `job-agent/scripts/seed_applications.py`，读取项目 `.env` 的 MySQL 连接信息，向 `applications` 添加六条虚构记录，包含完整候选人画像、岗位画像和匹配报告。

五表版本的测试导入会同时写入关联表和创建事件；旧库应先运行 `scripts.init_database`。2026-10-21 本次已保留原有六条测试投递并回填：`resumes` 1 条、`jobs` 6 条、`match_reports` 6 条、`applications` 6 条、`application_events` 6 条。六条投递共享相同候选人画像，不再为每个岗位新增相同画像。

| 虚构岗位 | 初始状态 | 测试匹配分 |
| --- | --- | --- |
| Python 后端实习生 | 待投递 | 86 |
| 数据工程实习生 | 已投递 | 72 |
| 测试开发实习生 | 笔试 | 78 |
| AI 应用开发实习生 | 面试 | 90 |
| 平台开发实习生 | Offer | 94 |
| Java 后端实习生 | 已拒绝 | 48 |

在项目目录执行：

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -m scripts.seed_applications
```

岗位标题带 `【测试】`，备注带 `[board-demo-v1]`，文件名为 `board-demo-v1-01.txt` 等。分数为人工测试值，模型字段为 `manual-test-fixture`，不会调用大模型。按固定文件名跳过已存在记录，单次串行重复运行不重复插入，也不覆盖手动修改；请勿并发运行。删除某条后重跑会补回该条。

成功后刷新求职看板即可验证六种状态与分数排序；可在页面逐条删除带标记的测试记录。脚本仅插入缺失的测试记录，不清空业务表。

2026-10-21 验证记录：临时 SQLite 测试验证了插入、重复跳过和已有数据保留，Ruff 检查通过。首次真实 MySQL 连接出现 `1045`，原因是连接用户名与所填密码所属账号不匹配。确认后修正本地连接账号，已向真实 MySQL 插入六条测试记录（本次 ID 为 1～6），回读及完整数据结构校验通过；使用 FastAPI TestClient 连接真实数据库验证了列表、六种状态筛选、匹配分降序和记录详情。此次未调用大模型、未进行浏览器交互测试。

连接字符串中 `://` 后、冒号前是 MySQL 登录用户名，端口后 `/` 后是数据库名，两者可以不同。通过某个账号创建数据库，并不意味着自动创建同名数据库账号；请为连接用户名填写该账号对应的密码。修改 `.env` 后需重启正在运行的应用，使缓存配置生效。

五表升级验证：真实 MySQL 建表、旧记录回填、关系完整性和完整报告回读通过；再次执行初始化没有新增或重复回填。实测五张表共六个外键，现有看板接口的列表、分数排序和详情兼容性通过。应用回归测试 37 项通过，追加的旧快照保留测试及关联重点测试共 6 项通过（临时 SQLite）；Ruff 与文档链接检查通过。此次没有调用大模型，也未进行浏览器操作测试。

2026-10-22 第六阶段验证：完整自动化测试 46 项通过，Ruff 与前端 JavaScript 语法检查通过；版本保存、核对门槛、编辑内容导出和删除级联由临时 SQLite 测试覆盖。真实 MySQL 仅执行了 `scripts.upgrade_draft_versions` 的增量建表和只读检查：原五表计数为 1/6/6/6/6，新表 0 条；确认七个字段、`CASCADE` 外键及 `(application_id, version)` 唯一约束。FastAPI TestClient 读取真实库的投递列表为 200（六条）、版本列表为 200（零条）。没有对真实库写入或确认测试草稿版本，也未调用大模型或进行浏览器操作测试。

2026-10-26 第七阶段验证：完整自动化测试 50 项通过，Ruff、前端脚本语法及差异空白检查通过。真实 MySQL 仅增建 `application_sources` 空表，原六表计数保持 1/6/6/6/6/0，新表 0 条；只读检查确认 `LONGTEXT` 字段和 `CASCADE` 外键。FastAPI TestClient 读取旧投递列表返回 200（六条），原文状态返回 200（未留存）。自动化的同意校验、逐行字面结果、投递隔离、删除留存和版本差异均使用临时 SQLite 与人工文本；没有在真实库保存个人原文，没有调用大模型，也未进行浏览器端到端操作。

## 下一阶段

下一步可完善第七阶段的人工证据标注与浏览器端到端测试，再考虑第八阶段的搜索和管理体验。当前没有语义级事实核验、一键投递或自动发送功能。
