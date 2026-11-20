# 第十七阶段：AI 评估集扩充

> 核对日期：2026-11-20。20 个虚构案例与离线规则已在本机验证；显式 live 的用量采集与 Hub 调用接口只用假响应验证，案例的人工语义复核和真实模型评估尚未完成。
> [返回项目说明](../README.md) · [第十四阶段基础评估](第十四阶段-评估端到端测试与部署监控.md) · [原待办计划](待办-AI评估集扩充.md)

## 一眼看懂本阶段

评估集从 3 例扩至 20 例：简历画像 9 例、岗位解析 7 例、匹配报告 4 例。所有姓名、学校、企业和经历均为虚构。新增案例分别覆盖联系方式或日期缺失、课程项目与工作经历区分、同词歧义、计划学习、岗位学历/时间/地点硬性条件、加分项与必须项区分，以及匹配条件的满足程度。每例保存构造关注点、预期结果、预置输出和复核状态。

当前复核记录是**编制与规则复跑记录**，不代表真人审核已完成。真实模型没有在本阶段调用；离线 20/20 通过只说明预置输出符合明确写出的规则。

## 文件与职责

| 文件 | 职责 |
| --- | --- |
| `job-agent/evals/cases.json` | 20 个虚构输入、输出、预期条件及逐例构造/复核记录 |
| `job-agent/app/services/evaluation.py` | 原有结构、字面证据和加权分检查；新增不应出现的技能、岗位要求遗漏、匹配条件状态与分数区间检查 |
| `job-agent/scripts/evaluate_outputs.py` | 默认离线运行并汇总规则指标；显式真实模型模式输出模型标识与逐例耗时 |
| `job-agent/app/services/call_metadata.py`、`app/services/llm.py` | live 上下文观察器；在供应商响应处逐次提取实际模型名、耗时、明确返回的 token 和稳定请求 ID |
| `job-agent/scripts/live_usage.py` | 最小 JSONL 追加记录、Hub 上报及失败重试；409 时读取 Hub 已有调用核对内容 |
| `job-agent/tests/test_live_usage.py` | 假 OpenAI/DeepSeek 响应与本机假 HTTP 服务测试 |
| `job-agent/tests/test_evaluation.py` | 检查 20 例可复跑，并用技能编造、硬性条件遗漏、条件误判和分数偏差验证反例 |

## 数据流、指标与运行

在 `D:\Agent\job-agent` 执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_outputs
.\.venv\Scripts\python.exe -m pytest tests/test_evaluation.py -q
```

脚本读取 `evals/cases.json`，对每例的预置输出运行规则检查，只打印案例 ID、失败检查名与汇总。结构通过数以所有案例为分母；字面证据通过数以实际执行的证据检查项为分母；硬性条件漏判检查失败数统计必需技能、加分技能误列、预期岗位要求或匹配状态检查的失败项；评分一致性只统计匹配案例的加权分检查。分母不同，不能把这些比值合并解释成模型准确率。失败项保留案例 ID 和检查名，供后续人工复核与版本对比。

显式添加 `--live --provider openai` 或 `--live --provider deepseek` 才会调用模型；使用同一套虚构输入和规则，逐例显示耗时、最后显示配置的模型标识。此模式为本次评估生成独立运行 ID，在供应商**每次响应**时写入 JSONL。`generate_json()` 对业务调用方仍只返回解析后的 JSON；通过 live 专用上下文观察器把响应元数据交给评估脚本。即使一个案例调用模型多次，也各有不同 `requestId` 和日志行。没有响应的请求不会虚构 token 或模型 ID。

JSONL 默认存于 Git 忽略的 `test-results/live-usage/<评估运行ID>.jsonl`，可用 `--usage-file` 指定新路径。每条调用只含评估运行 ID、案例 ID、provider、requestId，以及供应商响应的 modelId、单次耗时和可用 token；不保存简历、岗位、提示词、模型回答、密钥或完整请求。供应商未返回 usage，或仅返回单侧 token 时，Hub 请求的 `inputTokens` 和 `outputTokens` **同时省略**。若响应没有 modelId，日志仍保留该次调用，暂不向要求 modelId 的 Hub 接口发送。价格由 Hub 独立登记，只有显式传入 `--price-version` 时才上报版本，脚本不估算费用。

只有 live 模式同时传入 `--hub-url` 和 `--hub-run-id` 才会向已存在的 Hub 运行执行 `POST /api/runs/{runId}/calls`，字段为 `requestId`、`modelId`、`latencyMs`、可选成对 token 与可选 `priceVersion`。上传失败时保留 JSONL；运行 `--retry-usage-file <原文件> --hub-url <地址> --hub-run-id <原运行ID>` 显式重试，沿用原 requestId。201 记为成功；409 仅在 `GET /api/runs/{runId}/usage` 中找到同 requestId 且字段一致时记为已送达，冲突或查询失败则保留待重试。默认离线模式不写用量记录也不发网络请求。真实运行可能产生费用及输出波动；脚本不保存或打印原始模型输出，开放式摘要、语义关系、事实真伪和评分公平性仍需人工判断。

Hub 当前只接收运行与调用用量。此处**没有**把 AI 求职助手的评测结果、规则检查明细或 20/20 离线结论接入 Hub。

## 验证与限制

- 本机离线运行：20/20 预置输出通过；结构 20/20、字面证据检查 24/24、硬性条件漏判检查失败 0、评分一致性 4/4。这些是夹具规则结果，不是模型表现。
- 评估专项测试 8 项通过，覆盖故意构造的错误输出及模拟真实模式报告；完整普通套件 91 项通过、7 项按设计跳过，Ruff 通过。本阶段没有访问 MySQL、真实简历或模型服务。
- 2026-11-20 扩展验证：`python -m pytest -q` 为 102 项通过、7 项按设计跳过，`python -m ruff check .` 通过；`python -X utf8 -m scripts.evaluate_outputs` 的离线预置输出仍为 20/20。新增测试仅使用假 OpenAI/DeepSeek 响应和本机假 HTTP Hub 服务，覆盖成对/缺失用量、多次调用、默认离线无上报、失败重试及 409 一致性检查；本轮未调用真实模型、Hub 实例或 MySQL。这些结果不代表真实模型效果或 Hub 生产链路已联调。
- `review.record` 明确写有人工语义复核待完成；本阶段不将 Codex 编制的案例称为人工审核样本。后续真人审核应记录审核人、日期、争议和结论，再用于报告模型质量。
- 字面证据命中不能证明经历真实；目前只针对列出的不应出现技能和预期硬性条件检查遗漏，未覆盖任意隐含条件或开放式建议的语义正确性。
