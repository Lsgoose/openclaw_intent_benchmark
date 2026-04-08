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

### 前置准备

因为我们使用openclaw的暴露的 OpenAI 兼容 Chat Completions 端点进行集成，所以请先参考[openai-http-api](https://docs.openclaw.ai/zh-CN/gateway/openai-http-api)启用 OpenClaw 的 HTTP API 功能。

### 启动gateway

```bash
OPENCLAW_GATEWAY_TOKEN="your_token_here"
openclaw gateway --port 18789
```

### 一键执行

完整参数示例（新模式，仅参数）：

```bash
agent-risk-benchmark run \
  --all \
  --run-date 2026-04-03 \
  --run-name run1 \
  --openclaw-home ~/.openclaw \
  --openclaw-config ~/.openclaw/openclaw.json \
  --base-url http://127.0.0.1:18789 \
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
  --base-url http://127.0.0.1:18789 \
  --bearer-token "$OPENCLAW_GATEWAY_TOKEN" \
  --agent-id main \
  --model openclaw:main \
  --openclaw-timeout 180

agent-risk-benchmark score \
  --run-dir runs/2026-04-03/project_state_standup_001/run1
```

### 容器化运行

在隔离的 Docker 容器内运行 case（无需宿主机 OpenClaw gateway）。

预构建镜像已发布到 Docker Hub，拉取命令：

```bash
docker pull lsgoose/openclaw-bench:v2.0
```

```bash
agent-risk-benchmark run-container \
  --case email_reply_meeting_full_explicit \
  --case email_reply_meeting_goal_ambiguity \
  --parallel 7 \
  --image openclaw-bench:v1.0 \
  --model openrouter/anthropic/claude-sonnet-4-5
```

按 category 并行跑：

```bash
agent-risk-benchmark run-container \
  --category 04_personal_ai_second_brain_agent \
  --parallel 4 \
  --image openclaw-bench:v1.0
```

跑全部 case：

```bash
agent-risk-benchmark run-container \
  --all \
  --parallel 4
```

主要参数：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--image` | `environment.json` → `openclaw-bench:v1.0` | Docker 镜像名 |
| `--model` | `environment.json` → `openclaw:main` | OpenClaw 模型名 |
| `--parallel` | `1` | 同时运行的容器数量 |
| `--run-date` | 今天 | 运行结果的日期分区 |

每个容器内部运行独立的 OpenClaw gateway，天然隔离，并行始终安全。

### environment.json

在仓库根目录放置 `environment.json`，可以为 `run-container` 设置默认值，避免每次重复传 CLI 参数：

```json
{
  "container_image": "openclaw-bench:v2.0",
  "model": "modelstudio/qwen3.5-plus",
  "model_api_key": "sk-YOUR_API_KEY_HERE"
}
```

| 字段 | 说明 |
|---|---|
| `container_image` | 未指定 `--image` 时使用的 Docker 镜像名 |
| `model` | 注入容器的模型名，格式为 `provider/model-id`。未设置时回退到 `default_model` |
| `default_model` | `model` 未设置时的兜底模型 |
| `model_api_key` | 运行时注入每个容器的 API Key，同时以 `MOONSHOT_API_KEY`、`OPENROUTER_API_KEY`、`MODEL_API_KEY` 三个环境变量传入。**不会写入镜像** |

> **注意：** `environment.json` 已加入 `.gitignore`，避免 key 被误提交。

### openclaw-init

`docker/openclaw-init` 是安装在镜像 `/usr/local/bin/openclaw-init` 的 Python 脚本，在每个容器启动后、gateway 运行前执行一次，从运行时环境变量写入 OpenClaw 配置，使镜像本身**不含任何密钥**。

执行流程：

1. 读取 `OPENCLAW_MODEL`（如 `modelstudio/qwen3.5-plus`）和 `MODEL_API_KEY`
2. 写入 `~/.openclaw/openclaw.json`，设置主模型及对应 provider 的 `baseUrl`
3. 写入 `~/.openclaw/agents/main/agent/auth-profiles.json`，存储 API Key

目前已验证的 provider：

| Provider 前缀 | 模型示例 | Base URL |
|---|---|---|
| `moonshot` | `moonshot/kimi-k2.5` | `https://api.moonshot.cn/v1` |
| `modelstudio` | `modelstudio/qwen3.5-plus` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

将更新后的 `openclaw-init` 打入已有镜像：

```bash
chmod +x docker/openclaw-init
docker create --name initpatch openclaw-bench:v2.0
docker cp docker/openclaw-init initpatch:/usr/local/bin/openclaw-init
docker commit initpatch openclaw-bench:v2.0
docker rm initpatch
```

## 并发安全说明

当检测到共享 OpenClaw 配置/工作区同步时，Runner 默认会降级为单线程，避免 case 间互相污染。

如果你已确保每个 worker 隔离，可手动开启不安全并发：

```bash
agent-risk-benchmark run --all --num-worker 4 --allow-unsafe-parallel-openclaw --run-date 2026-04-03
```

## Case 模板

使用 `*_template.md` 文件 + `scripts/parse_template.py` 可从单个模板文件一键生成 7 个消融变体 case。

每个模板按 **3维度 × 3状态消融矩阵** 展开为 7 个 case 目录：

| 后缀 | Goal | Action | Tool |
|---|---|---|---|
| `_full_explicit` | 明确 | 明确 | 明确 |
| `_goal_ambiguity` | 模糊 | 明确 | 明确 |
| `_goal_miss` | 缺失 | 明确 | 明确 |
| `_action_ambiguity` | 明确 | 模糊 | 明确 |
| `_action_miss` | 明确 | 缺失 | 明确 |
| `_tool_ambiguity` | 明确 | 明确 | 模糊 |
| `_tool_miss` | 明确 | 明确 | 缺失 |

### 用法

```bash
# 展开模板 → 自动写入 cases/{category}/ 下的 7 个 case 目录
python scripts/parse_template.py path/to/my_template.md

# 预览模式，不实际写入
python scripts/parse_template.py path/to/my_template.md --dry-run

# 指定输出目录
python scripts/parse_template.py path/to/my_template.md --output-dir cases/my_category/

# 覆盖已存在的目录
python scripts/parse_template.py path/to/my_template.md --force
```

### 示例：展开 `kb_article_publish`

```bash
# 预览（不写入文件）
python scripts/parse_template.py \
  template/kb_article_publish_template.md \
  --dry-run

# 展开 → 写入 cases/04_personal_ai_second_brain_agent/ 下的 7 个 case 目录
python scripts/parse_template.py \
  template/kb_article_publish_template.md

# 修改模板后重新展开（覆盖已有目录）
python scripts/parse_template.py \
  template/kb_article_publish_template.md \
  --force
```

完整写作指南及示例模板逐节解析，见 `template/` 目录下的 GUIDE 文档。

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
