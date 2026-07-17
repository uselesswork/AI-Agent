# AI 求职助手

这是一个基于证据分析简历与实习岗位描述匹配度的 AI Agent 项目。

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

接口可能返回的状态码：

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

```text
app/api/resumes.py                 简历上传接口与请求校验
app/core/config.py                 OpenAI、DeepSeek 环境配置
app/models/candidate.py            候选人画像数据模型
app/prompts/resume_analysis.py     简历结构化提示词
app/services/document_parser.py   PDF、DOCX、TXT 文本解析
app/services/llm.py               OpenAI 兼容模型客户端
app/services/resume_analyzer.py   候选人画像分析服务
app/static/index.html             前端测试页面结构
app/static/styles.css             前端页面样式与响应式布局
app/static/app.js                 上传、解析、复制等交互逻辑
tests/test_document_parser.py     文档解析单元测试
tests/test_resume_api.py          简历上传接口测试
tests/test_resume_analysis_api.py 候选人画像接口测试
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

## 下一阶段

下一步将实现岗位 JD 结构化，把岗位要求拆分为硬性要求、加分项、职责、技能和经验要求，为后续简历匹配分析做准备。
