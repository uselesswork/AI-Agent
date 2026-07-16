# AI 求职助手

这是一个基于证据分析简历与实习岗位描述匹配度的 AI Agent 项目。

## 本地运行

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000/health`，检查服务是否正常运行。

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

