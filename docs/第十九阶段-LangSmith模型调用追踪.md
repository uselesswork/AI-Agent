# 第十九阶段：LangSmith 模型调用追踪

> 核对日期：2026-11-20。此阶段新增可选追踪；本机普通测试、Ruff、虚构远端摘要及一次真实模型调用已验证。
> [返回项目说明](../README.md) · [第二阶段模型接入](第二阶段-候选人画像与模型接入.md) · [第十四阶段本机监控](第十四阶段-评估端到端测试与部署监控.md)

## 一眼看懂本阶段

简历画像、岗位解析和匹配报告都通过 `OpenAICompatibleClient` 调用 OpenAI 兼容接口。本阶段在统一客户端外层接入 LangSmith SDK，按次记录服务商、模型、成功状态或异常类型，以及可取得的 token 用量。LangSmith 的运行记录自动带有开始和结束时间，可用于查看调用耗时。追踪默认关闭；本机 `job-agent/.env` 已配置独立项目，真实密钥不会进入仓库。

## 文件职责

| 文件 | 职责 |
| --- | --- |
| `job-agent/app/core/config.py` | 从环境读取追踪开关、密钥、项目名和端点；密钥使用 `SecretStr` |
| `job-agent/app/observability/langsmith.py` | 构造 LangSmith 客户端、生成调用摘要、隔离追踪异常 |
| `job-agent/app/services/llm.py` | 统一模型调用、提取响应中的 token 用量并交给追踪层 |
| `job-agent/app/services/resume_analyzer.py`、`job_analyzer.py`、`match_analyzer.py` | 给三个业务分析器注入同一个追踪器 |
| `job-agent/pyproject.toml` | 声明 LangSmith SDK 依赖 |
| `job-agent/.env.example`、`.env.docker.example` | 提供默认关闭的占位配置 |
| `job-agent/tests/test_langsmith.py` | 验证追踪字段、隐私边界及失败时的模型调用次数 |

## 数据流与隐私边界

```text
业务分析器 → 统一模型客户端 → OpenAI / DeepSeek
                      ↓
             LangSmith 调用摘要（启用时）
```

模型请求本身仍向选定服务商发送业务提示词。LangSmith 只接收 `provider`、`model`、`status`、异常类名和 SDK 可用的 `prompt_tokens`、`completion_tokens`、`total_tokens`。追踪代码不会把简历原文、岗位描述、完整提示词、模型响应正文、API Key、账号标识或数据库内容作为输入、输出或元数据上报。异常只记录类型，不记录可能包含敏感文本的异常消息。由于不上传业务正文，LangSmith 页面不能回放提示词或检查模型回答质量；这类质量评估仍由独立的离线评估流程负责。

追踪服务故障时，应用继续执行模型调用，不会因追踪失败重发已完成的模型请求。若开启追踪却缺少 LangSmith 密钥或项目名，构造分析器时会明确报配置错误。修改 `.env` 后须重启应用，缓存的设置和追踪器才会更新。

## 配置与使用

在 `job-agent/.env` 中配置：

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=你的_LangSmith_API_Key
LANGSMITH_PROJECT=job-agent
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

本机配置复用了 `qa-system/.env` 中的 LangSmith 凭据和端点，但 `LANGSMITH_PROJECT` 使用独立的 `job-agent`，避免与问答项目混合。`.env` 被 Git 忽略；容器部署时需要单独在 `.env.docker` 中设置，示例文件默认关闭。关闭追踪只需把 `LANGSMITH_TRACING` 改为 `false` 并重启应用。无需数据库迁移，也没有新增 HTTP 接口或前端控件。

## 验证与限制

- 自动化测试通过模拟模型操作和追踪上下文检查摘要字段及异常隔离；针对性测试 10 项通过，完整普通套件 95 项通过、7 项按设计跳过，Ruff 通过。测试未调用真实模型或 MySQL。
- 使用虚构模型名和虚构 token 数量向独立 `job-agent` LangSmith 项目发送一条摘要，远端读回一条 `job-agent.model-call`，输入仅含 `model`、`provider`，输出仅含 `status` 和三个 token 字段。该连通性检查未调用 OpenAI/DeepSeek，也不能证明三条业务路径已与远端真实模型联调。
- 2026-11-20 通过 `OpenAICompatibleClient` 向本机配置的真实 OpenAI 模型 `gpt-6-luna` 发送无个人信息的虚构 JSON 请求；模型返回合法 JSON，LangSmith 中读回同次 `job-agent.model-call`，状态为 `ok`，输入字段只有 `model`、`provider`，输出字段为 `status` 和三个 token 数量。这验证统一客户端的真实模型与远端追踪链路，未经过完整简历、岗位或匹配业务接口，也未使用真实简历、JD 或 MySQL。
- token 用量依赖模型服务商在响应中返回 `usage`；没有返回时记录中不包含相应数字。
- 当前仅追踪统一客户端中的模型调用；文件解析、数据库、浏览器和公开招聘板请求不进入 LangSmith。尚无告警、在线评估、追踪采样配置或仪表盘。
