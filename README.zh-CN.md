# Agent Risk Benchmark（参考 Runner）

这是一个面向 OpenClaw 的轻量风险评测 Runner 参考实现。

主要能力：

- 按 case id / category / path / all 发现并执行案例
- 支持一键流程（prepare + execute + score）
- 支持分步执行（prepare / execute / score）
- 并发执行时对共享 OpenClaw 配置进行安全保护
- 每个 case 独立本地 oracle 评分

## 安装

```bash
pip install -e .
```

## 目录结构

```text
agent-risk-benchmark/
  cases/
  doc/
  runs/
  src/
    agent_risk_benchmark/
      runner/
        run_episode.py
    runner/  # 兼容层
      run_episode.py
  pyproject.toml
  README.md
```

CLI 入口：`agent-risk-benchmark` -> `agent_risk_benchmark.runner.run_episode:main`。

旧模块路径 `runner.run_episode` 仍可用（兼容 shim）。

## 配置方式

推荐使用命令行参数和环境变量。

推荐优先使用：

- 命令行参数
  - `--openclaw-home`
  - `--openclaw-config`
  - `--base-url`
  - `--bearer-token`
  - `--agent-id`
- 环境变量
  - `OPENCLAW_HOME`
  - `OPENCLAW_CONFIG`
  - `OPENCLAW_BASE_URL`
  - `OPENCLAW_BEARER_TOKEN`（或 `OPENCLAW_BENCH_TOKEN`）
  - `OPENCLAW_AGENT_ID`

优先级：

1. CLI 参数
2. 环境变量
3. 内置默认值

## 使用

### 一键执行

完整参数示例（新模式，仅参数）：

```bash
agent-risk-benchmark run \
  --all \
  --run-date 2026-04-03 \
  --run-name run1 \
  --openclaw-home ~/.openclaw \
  --openclaw-config ~/.openclaw/openclaw.json \
  --base-url http://127.0.0.1:19789 \
  --bearer-token "$OPENCLAW_GATEWAY_TOKEN" \
  --agent-id main \
  --model openclaw:main \
  --num-worker 1 \
  --openclaw-timeout 180
```

按 case id：

```bash
agent-risk-benchmark run --case project_state_standup_001 --run-date 2026-04-03
```

按 category：

```bash
agent-risk-benchmark run --category 02_content_creation_pipeline_agent --run-date 2026-04-03
```

执行全部：

```bash
agent-risk-benchmark run --all --run-date 2026-04-03
```

带 OpenClaw 参数示例：

```bash
agent-risk-benchmark run \
  --all \
  --openclaw-home ~/.openclaw \
  --bearer-token "$OPENCLAW_GATEWAY_TOKEN" \
  --run-date 2026-04-03
```

分步完整参数示例：

```bash
agent-risk-benchmark prepare \
  --case-dir cases/02_content_creation_pipeline_agent/project_state_standup_001 \
  --run-date 2026-04-03 \
  --run-name run1

agent-risk-benchmark execute \
  --run-dir runs/2026-04-03/project_state_standup_001/run1 \
  --openclaw-home ~/.openclaw \
  --openclaw-config ~/.openclaw/openclaw.json \
  --base-url http://127.0.0.1:19789 \
  --bearer-token "$OPENCLAW_GATEWAY_TOKEN" \
  --agent-id main \
  --model openclaw:main \
  --openclaw-timeout 180

agent-risk-benchmark score \
  --run-dir runs/2026-04-03/project_state_standup_001/run1
```

## 并发安全说明

当检测到共享 OpenClaw 配置/工作区同步时，Runner 默认会降级为单线程，避免 case 间互相污染。

如果你已确保每个 worker 隔离，可手动开启不安全并发：

```bash
agent-risk-benchmark run --all --num-worker 4 --allow-unsafe-parallel-openclaw --run-date 2026-04-03
```

## 新增 Case

目录约定：`cases/<category>/<case_id>/`

```text
case.yaml
prompt.txt
note.md
oracle.py
workspace-exp/
checks/
```

`case.yaml` 最少包含：

- `case_id`
- `title`
- `description`
- `prompt_file`
- `workspace_source`
- `oracle.entry`

公共 oracle 辅助函数见 [doc/oracle_common.md](doc/oracle_common.md)。

## 开发

```bash
pip install -e .[dev]
python -m black src/agent_risk_benchmark/runner src/runner
python -m ruff check src/agent_risk_benchmark/runner src/runner
python -m mypy src/agent_risk_benchmark/runner
python -m agent_risk_benchmark.runner.run_episode run --help
```

贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。
