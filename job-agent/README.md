# AI 求职助手

这是一个基于证据分析简历与实习岗位描述匹配度的 AI Agent 项目。

## 当前进度

第一阶段的简历上传与文本解析功能已经完成：

- 支持 PDF、DOCX 和 TXT 文件
- 单个文件最大 10 MB
- 能够读取 DOCX 段落与表格内容
- TXT 支持 UTF-8 和 GB18030 编码
- 对空文件、损坏文件、不支持格式和无文字 PDF 返回明确错误
- 扫描版 PDF 暂不进行 OCR，会提示用户先完成文字识别

## 本地运行

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000/health`，检查服务是否正常运行。

## 解析简历

启动服务后打开 `http://127.0.0.1:8000/docs`，在 Swagger 页面中调用：

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

先激活虚拟环境，再通过 Python 模块方式运行测试：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest
```

推荐使用 `python -m pytest`，这样可以确保调用的是当前虚拟环境中安装的 pytest。如果提示缺少测试依赖，请重新执行：

```powershell
python -m pip install -e ".[dev]"
```

## 项目结构

```text
app/api/resumes.py                 简历上传接口与请求校验
app/services/document_parser.py   PDF、DOCX、TXT 文本解析
tests/test_document_parser.py     文档解析单元测试
tests/test_resume_api.py          简历上传接口测试
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
