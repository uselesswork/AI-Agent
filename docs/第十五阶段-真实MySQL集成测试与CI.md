# 第十五阶段：真实 MySQL 集成测试与 CI

> 核对日期：2026-11-13；2026-11-18 补充第十六阶段对测试夹具及 CI 步骤的复用说明。代码、本机隔离 MySQL 用例和补齐字体后的 GitHub Actions 远端运行均已验证。
> [返回项目说明](../README.md) · [原待办计划](待办-真实MySQL集成测试与CI.md) · [数据库设计](数据库设计与字段说明.md)

## 一眼看懂本阶段

本阶段给原有临时 SQLite 测试增加一个**显式启用**的真实 MySQL 集成用例，并添加 Python CI 工作流。用例每次生成随机命名的 `job_agent_test_...` 数据库，在其中建表、创建虚构账号、经 FastAPI TestClient 走真实会话和业务接口，结束时只删除该测试库。日常 `job_agent` 库不作为用例目标。CI 使用作业自带的临时 MySQL 8.4 服务，不依赖本机 `.env` 或真实模型 Key。

## 文件与职责

| 文件 | 本阶段职责 |
| --- | --- |
| `job-agent/tests/test_mysql_integration.py` | 双账号登录、CSRF、投递写入/状态事件、跨账号拒绝、事务回滚、删除级联及登出检查 |
| `job-agent/tests/conftest.py` | `--run-mysql-integration` 开关和随机测试库的创建/清理夹具；普通测试默认跳过 MySQL 用例，浏览器用例继续独立开关 |
| `job-agent/pyproject.toml` | 注册 MySQL 用例标记，并明确 Ruff 的基础错误规则 `E4`、`E7`、`E9`、`F` |
| `.github/workflows/python-ci.yml` | 提交和 PR 时安装开发依赖及中文 PDF 字体，运行 Ruff、普通 pytest 与独立 MySQL 用例；第十六阶段起同一步骤还运行迁移用例 |

## 数据流和运行方式

普通 `pytest` 仍以临时 SQLite 为主；MySQL 用例必须同时传入 `--run-mysql-integration` 和环境变量 `MYSQL_TEST_ADMIN_URL`。该 URL 必须使用 `mysql+pymysql` 且指向服务器的 `mysql` 系统库；测试不会从项目 `DATABASE_URL` 自动取测试目标。执行前需确认连接的是允许创建/删除随机测试库的**测试 MySQL 实例**。不要把日常库或生产实例的管理凭据写进仓库、命令行参数或文档。

```powershell
cd D:\Agent\job-agent
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
# 在独立测试 MySQL 实例配置 MYSQL_TEST_ADMIN_URL 后，再显式运行：
.\.venv\Scripts\python.exe -m pytest tests/test_mysql_integration.py --run-mysql-integration -q
```

CI 的 MySQL 服务仅在该次作业存在。工作流内的 `ci-only-password` 是临时测试服务的固定占位凭据，不用于用户数据库。普通套件默认跳过浏览器和 MySQL 两类显式用例；MySQL 集成测试在 CI 的独立步骤中运行。CI 失败会返回非零退出码，阻止将失败的测试结果误写为通过。

2026-11-18 起，随机库夹具移至 `tests/conftest.py` 供[第十六阶段迁移测试](第十六阶段-数据库迁移管理.md)共用；CI 的 MySQL 步骤同时运行 `test_mysql_integration.py` 和 `test_migrations_mysql.py`。本阶段下列 2026-11-13 结果是当时的历史验证，新增迁移用例的本机结果见第十六阶段说明。

## 实际验证与限制

- 本机 `ruff check .` 通过；配置的基础错误规则是本阶段明确的自动门槛，尚未把旧代码中所有新版 Ruff 可选规则纳入门槛。
- 普通测试 **88 项通过、2 项按设计跳过**（浏览器和 MySQL）；1 项独立 MySQL 集成用例通过。用例使用虚构账号和投递，不调用真实模型。
- 用例验证登录、CSRF、两账号隔离、状态变更事件、事务中断后投递数不增加、删除事件及归属记录、登出失效。执行后只读确认随机测试库为 0 个，日常库仍是 1 个账号、0 条投递。
- 2026-11-13 [首次 Actions 运行](https://github.com/uselesswork/AI-Agent/actions/runs/43392574742)中服务、依赖安装与 Ruff 成功，普通 `pytest` 失败，后续 MySQL 用例跳过。公开注释只给出退出码，未取得具体失败堆栈。代码中的 PDF 导出依赖系统中文字体，而原 Ubuntu 工作流未安装；增加 `fonts-noto-cjk` 和路径检查后，[第二次运行](https://github.com/uselesswork/AI-Agent/actions/runs/43394810237)的字体安装、Ruff、普通测试及 MySQL 用例全部通过。据前后结果推断，缺少字体导致首次失败；这一推断不等于已看到首次测试堆栈。单个集成用例仍不覆盖所有十四张表的每条业务路径，也没有验证真实模型或浏览器。
- 测试创建和删除的是随机命名的独立数据库；需要测试实例账号具备创建/删除数据库权限。MySQL DDL 不可整体事务回滚，异常时夹具会尽力清理；若进程被强制终止，需人工检查并仅清理确认属于本次测试的 `job_agent_test_...` 库。
