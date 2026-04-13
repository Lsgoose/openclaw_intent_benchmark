# Agent Risk Benchmark（参考 Runner）

这是一个面向 OpenClaw 的轻量风险评测 Runner 参考实现。

主要能力：

- 按 case id / category / path / all 发现并执行案例
- 支持一键流程（prepare + execute + score）
- 支持分步执行（prepare / execute / score）
- 并发执行时对共享 OpenClaw 配置进行安全保护
- 每个 case 独立本地 oracle 评分
- **`pass-at-k` 子命令**：对每 case 的 k 次打分结果汇总 **pass@k** 与 **pass_all_k**

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

`run`（批量或单个 case）以及 `run-container` 可附加 `--summary`，将汇总（分类统计 + 逐 case 结果）写入文件；路径以 `.md` 结尾则输出 Markdown。只写 `--summary` 时默认落到 `runs/<run-date>/summary_<模式>_<utc>.json`。

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

### pass-at-k（pass@k 与 pass_all_k）

在同一 **`--run-date`** 下，**`runs/<日期>/` 下每个一级子目录名 = 一个独立 case**（与 `case.yaml` 里的 `case_id` 一致），彼此不合并。例如 `cases/04_personal_ai_second_brain_agent/email_reply_meeting_action_ambiguity/` 对应 **`runs/<日期>/email_reply_meeting_action_ambiguity/`**；`email_reply_meeting_goal_ambiguity` 等同级目录各算 **另一个** case。对每个 case 已有 **k 次**已打分的运行目录（`runs/<日期>/<case_id>/<RUN_NAME>/score.json`）时，可用 **`pass-at-k`** 汇总指标。终端默认只打印 **全体 case** 的通过率；**每个 case** 的 pass@k / pass_all_k 见 **`--json`** → **`per_case`**。

| 指标 | 含义 |
|------|------|
| **pass@k** | 该 case 的 k 次里 **至少一次** 按 `--metric` 判定成功，则该 case 算通过。 |
| **pass_all_k**（口语里有时写作 pass^k） | **k 次全部** 成功才算该 case 通过；缺少 `score.json` 的试次视为失败。 |

成功判定由 **`--metric`** 控制：默认 **`full`**（`task_success` 且 `safety_success`），也可 **`task` / `safety` / `score`**（`score` 时需 **`--score-threshold`**，默认 `1.0`）。

**只填数字：** **`-k N`** 会自动使用目录名 **`run1` … `runN`**（与仓库里 `run1` 命名习惯一致）。若目录名不是 `run1`…`runN`，请用 **`--replicate`** 逐个写出。

```bash
# 等价于 --replicate run1 run2 run3
agent-risk-benchmark pass-at-k --run-date 2026-04-12 -k 3

# 手写目录名
agent-risk-benchmark pass-at-k --run-date 2026-04-12 --replicate run1 run2 run3

# 输出完整 JSON（每个 case 的 pass@k / pass_all_k 及各次 trial）
agent-risk-benchmark pass-at-k --run-date 2026-04-12 -k 3 --json

# 不写默认落盘的总结文件
agent-risk-benchmark pass-at-k --run-date 2026-04-12 -k 3 --no-summary
```

**总结文件（默认开启）：** 每次运行会在 **`runs/<日期>/pass_at_k_summary_<utc>.json`** 写入完整 JSON：除 pass@k / pass_all_k 外，还有 **`rollup`**（所有 trial 的 **token** `input` / `output` / `cache_read` / `cache_write` / `total` 求和；存在 **`openclaw_response.json`** 时的 **`http_duration_sec`** 均值等），以及 **`per_case[].trials[]`** 里每次试次的 **`task_success`**、**`safety_success`**、**`score`**、**`token_usage`**（从 trace **JSONL** 汇总，与 `run` 一致）、**`http_duration_sec`**。容器跑次常见为 **`bench-run.jsonl`**。自定义路径用 **`--summary PATH`**；扩展名 **`.md`** 会写 Markdown 简报。**`--no-summary`** 关闭写文件。**`--json`** 只影响标准输出，可与写文件同时存在。

**`-k`** 与 **`--replicate`** 不要同时使用。更多参数见：`agent-risk-benchmark pass-at-k --help`。

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
  --image openclaw-bench:v2.0 \
  --model openrouter/anthropic/claude-sonnet-4-5
```

按 category 并行跑：

```bash
agent-risk-benchmark run-container \
  --category 04_personal_ai_second_brain_agent \
  --parallel 4 \
  --image openclaw-bench:v2.0
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
| `--image` | `environment.json` → `openclaw-bench:v2.0` | Docker 镜像名 |
| `--model` | `environment.json` → `openclaw:main` | OpenClaw 模型名 |
| `--parallel` | `1` | 同时运行的容器数量 |
| `--run-date` | 今天 | 运行结果的日期分区 |
| `--summary` | 不写文件 | 写入 JSON/Markdown 汇总；仅 `--summary` 时默认 `runs/<run-date>/summary_run_container_<utc>.json` |

每个容器内部运行独立的 OpenClaw gateway，天然隔离，并行始终安全。

### environment.json

**`docker/openclaw-init`**（镜像内为 `/usr/local/bin/openclaw-init`）：在 gateway 启动前根据 `OPENCLAW_MODEL` / `MODEL_API_KEY` 生成 OpenClaw 配置，避免把密钥打进镜像。

在仓库根目录放 `environment.json`，给 `run-container` 提供默认配置。**`model`** 填下表中的完整模型 id；**`model_api_key`** 填对应平台的密钥（Ofox 下列模型共用一个 key 即可）。

```json
{
  "container_image": "openclaw-bench:v2.0",
  "model": "openai/gpt-5.4",
  "model_api_key": "sk-YOUR_KEY"
}
```

| 字段 | 作用 |
|---|---|
| `container_image` | 未传 `--image` 时使用的镜像 |
| `model` | 传入容器作为 `OPENCLAW_MODEL`（须与下表一致，或为 `前缀/model-id` 的 legacy 写法） |
| `default_model` | 未设置 `model` 时的兜底 |
| `model_api_key` | 运行时注入为 `MODEL_API_KEY` 等，**不会写入镜像** |

**模型 id 与 Base URL 对应**（与 `docker/openclaw-init` 保持一致）：

| `model` | Base URL |
|---|---|
| `openai/gpt-5.4` | `https://api.ofox.ai/v1` |
| `z-ai/glm-5-turbo` | `https://api.ofox.ai/v1` |
| `volcengine/doubao-seed-2.0-pro` | `https://api.ofox.ai/v1` |
| `minimax/minimax-m2.7` | `https://api.ofox.ai/v1` |
| `deepseek/deepseek-v3.2` | `https://api.ofox.ai/v1` |
| `anthropic/claude-sonnet-4.6` | `https://api.ofox.ai/anthropic` |
| `anthropic/claude-opus-4.6` | `https://api.ofox.ai/anthropic` |
| `moonshot/kimi-k2.5` | `https://api.moonshot.cn/v1` |
| `modelstudio/qwen3.5-plus` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

> **注意：** `environment.json` 已 gitignore；下表须与 `docker/openclaw-init` 保持同步。

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
