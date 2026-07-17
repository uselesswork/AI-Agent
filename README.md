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

## 解析简历

### 使用前端页面

打开 `http://127.0.0.1:8000/upload`，点击或拖拽上传 PDF、DOCX、TXT 简历，然后点击“开始解析”。页面会显示：

- 文件格式
- 提取字符数量
- 文件处理状态
- 完整简历正文
- 复制正文按钮

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
app/services/document_parser.py   PDF、DOCX、TXT 文本解析
app/static/index.html             前端测试页面结构
app/static/styles.css             前端页面样式与响应式布局
app/static/app.js                 上传、解析、复制等交互逻辑
tests/test_document_parser.py     文档解析单元测试
tests/test_resume_api.py          简历上传接口测试
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

下一步将把简历正文转换为结构化候选人画像，包括教育经历、技能、项目经历、实习经历和求职方向。
