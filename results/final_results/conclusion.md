# full98 结果解读（与热力图一致）

本文档基于 `full98_by_ablation_dimension_model.csv`。其中 **§1–§3** 侧重 **`task` / `progress`（任务完成与过程进度）**；**§6–§7** 补充 **`safe`（安全）** 与 **`mean_steps` / `tokens_total`（步数与 token 开销）**。对应热力图均由 `plot_ablation_dimension_heatmaps.py` 生成，位于 **`figures/`**（含 `heatmap_safe_*`、`heatmap_mean_steps_*`、`heatmap_tokens_total_*` 等）。**结论仅反映本 benchmark 的设定与 case 集合，不宜无依据外推。**

以下 **「11 模型在某一维度上的简单平均」** 用于概括「哪类维度最伤安全/最费开销」（不替代逐模型细读）。

---

## 1. 「基模能力」分层（以 `full_explicit` 为参照）

在信息最完整、扰动最小的 **`full_explicit`** 下，按 `task` 可粗分三档：

| 档位 | 表现 | 代表模型（本表中） |
|------|------|----------------------|
| 第一档 | `task` 约 **1.0** | `anthropic/claude-opus-4.6`、`anthropic/claude-sonnet-4.6`、`bailian/qwen3.6-plus`、`google/gemini-3.1-pro-preview`、`openai/gpt-5.4` |
| 次强 | `task` 约 **0.95–0.98** | `openai/gpt-5.4-mini`、`minimax/minimax-m2.7`、`volcengine/doubao-seed-2.0-pro`、`z-ai/glm-5-turbo` 等 |
| 基线明显偏弱 | `task` 明显低于上述 | `moonshotai/kimi-k2.5`（约 **0.83**）、`deepseek/deepseek-v3.2`（约 **0.60**） |

说明：第一档在「干净设定」下于本套 case 上已接近打满；后两者在 **同一 `full_explicit` 列** 上即存在可见缺口，讨论「跨维度鲁棒性」时需与 **整体水平** 区分，避免只谈维度效应。

---

## 2. 不同模糊 / 消融维度对任务完成（`task`）的影响

跨模型规律较一致：

1. **伤害最大**：**`action_miss`**、**`action_ambiguity`**。多数模型的 `task` 在此出现 **断崖式下降**（常见落在约 **0.3–0.65**，更差可至 **0.2** 以下）。含义：当 **动作空间不清** 或 **关键动作信息缺失** 时，**完不成任务** 的现象最突出，而非仅分数略降。

2. **中等压力**：**`tool_miss`**、**`tool_ambiguity`**。多数仍能保持中等偏上完成率，但弱模型更吃力。

3. **相对温和**：**`goal_miss`**、**`goal_ambiguity`**。一线模型往往仍能维持较高 `task`；在本 benchmark 中，**目标层扰动** 比 **动作 / 工具层扰动** 更容易被纠偏或补救。

**一句话**：同一批模型上，**与「动作」相关的消融** 通常比 **与「目标」相关的消融** 更致命；热力图中 **中间几行（`action_*`）** 往往比 **上下部（`full_explicit` / `goal_*` / 部分 `tool_*`）** 更浅（`task` 更低）。

---

## 3. `progress` 与 `task` 的关系

许多格子里 **`progress` 高于 `task`**，尤其在 **`action_*`** 维度：说明智能体 **仍能推进部分步骤或子目标**，但 **最终任务判负**（`task` 低）。这对应常见现象：**有过程进展、无交付成功** —— 对动作 / 工具设定不清的场景尤其典型。

因此：**progress 热力图更「绿」、task 更「蓝 / 浅」** 的区域，往往表示 **半吊子进展** 而非「完全无进展」。

---

## 4. 阅读图表时的注意点

- **`deepseek/deepseek-v3.2`**：全表往往整体偏浅，既含 **`full_explicit` 基线就不高**，也在各维度上一并偏低；解读时需区分 **「维度效应」** 与 **「该模型在本套评测上的整体弱势」**。
- **`openai/gpt-5.4-mini` 在 `action_miss` 上**：`task` 可极低（约 **0.21** 量级），与同列 **`gpt-5.4`** 对比反差大，更接近 **该维度上的极端脆弱点**，而非轻微波动。

---

## 5. 同族模型能否对比出差别

**可以。** `full98_by_ablation_dimension_model.csv` 里 **同一供应商、同一命名系列** 的行，就是在 **相同维度、相同 case 集合** 下的并列结果，直接对比同一格里的 `task` / `progress` 即可看出「同族」差别。

### 5.1 对比前提

- 每一行是 **模型 × 维度** 的汇总；**维度一致** 时，横向对比两行就是在比「同扰动设定下谁更稳」。
- 本表中 **明显的同族成对** 主要是：
  - **`openai/gpt-5.4`** vs **`openai/gpt-5.4-mini`**
  - **`anthropic/claude-opus-4.6`** vs **`anthropic/claude-sonnet-4.6`**
- 其他多为「一家一个型号」（如 Kimi、DeepSeek、Gemini 等各一条），**没有第二颗同族模型**，就无法做族内对比，只能做跨族对比或 **同模型跨维度** 分析。

### 5.2 族内能看出什么（本 CSV 中的例子）

**OpenAI（gpt-5.4 vs gpt-5.4-mini）**

- **`full_explicit`**：二者 `task` 都处于「接近满分」档（5.4 为 1.0，mini 约 0.98），**基线差距不大**。
- 差别主要在 **难维度**：例如 **`action_miss`**，`gpt-5.4` 的 `task` 约 **0.38**，`gpt-5.4-mini` 约 **0.21** —— 在本评测里 **「动作信息缺失」对 mini 伤害更大**，族内差距被 **动作类消融** 放大。
- **`progress`** 上 mini 在部分维度仍不算极低，但 **`task` 更低**，仍是典型的 **有进展、难收尾**。

**Anthropic（claude-opus-4.6 vs claude-sonnet-4.6）**

- **`full_explicit`**：二者 `task` 均可到 **1.0**，基线都强。
- 同样在 **`action_*`**：**opus** 的 `task` 明显高于 **sonnet**（例如 **`action_miss`** 约 **0.60 vs 0.38**），说明在本套 case 上 **同族更强的一款对动作类扰动更扛得住**。
- **`goal_*` / `tool_*`** 上二者差距通常 **小于 `action_*`**。

**同族在安全与开销上（与 `task` 一起看更有信息量）**

- **OpenAI `gpt-5.4` vs `gpt-5.4-mini`**：在 **`action_miss`** 上，mini 的 **`safe` 更低**（约 **0.74 vs 0.81**），**`tokens_total` 反而更高**（约 **5.7M vs 4.7M**），呈现 **更不安全、更费 token、任务完成更差** 的叠加；**`action_ambiguity`** 上也有类似 **费 token 上升 + `safe` 略紧** 的倾向。说明族内「小杯」不仅是 **能力落差**，在难维度上还可能 **多烧资源仍换不来安全与完成**。
- **Anthropic `opus` vs `sonnet`**：在 **`action_miss`** 上 **sonnet** 的 **`safe` 明显更低**（约 **0.71 vs 0.81**），与 **`task` 更大滑落** 一致；**`tokens_total`** 在 **`full_explicit`** 上 **sonnet 高于 opus**（约 **7.0M vs 5.9M**），基线成本结构不同，解读「开销」时不宜只看步数，还需结合 **token 统计口径（含 cache 等）**。

### 5.3 建议的量化方式

1. **固定维度**，比较 `task`（以及可选 `progress`）：同一格里谁更高，谁在该维度上更鲁棒。
2. **算相对基线的跌落**：同一模型用 **`task(full_explicit) − task(某维度)`**（或比值），比绝对分更能看出「哪种扰动对该族伤害最大」。
3. **可视化**：只对两颗模型各保留一行热力条带，或做 **差分热力图（模型 A − 模型 B）**，族内差异会很直观。

---

## 6. 安全（`safe`）：基模、维度与同族

### 6.1 基线（`full_explicit`）

本表中 **绝大多数模型在 `full_explicit` 上 `safe` 为 1.0 或非常接近**；**`kimi-k2.5`** 在基线即约 **0.98**，略低于「满分安全」档。**`deepseek-v3.2`** 基线 **`task` 偏低但 `safe` 仍为 1.0** —— 说明在本 oracle 定义下，**「不安全」与「未完成」可分离**，不能单靠 `task` 推断 `safe`。

### 6.2 哪类模糊维度对 `safe` 影响最大？

对 **11 个模型、按维度取平均 `safe`**，从低到高大致为：

**`action_miss` ≈ 0.79 → `action_ambiguity` ≈ 0.83 → `goal_miss` ≈ 0.90 → … → `full_explicit` ≈ 1.00**（`tool_*` 介于中间）。

与 **`task` 的结论高度同向**：**`action_*` 不仅最伤完成率，也最拉低平均安全分**；**`goal_*`** 次之；**`tool_*`** 相对温和。热力图 **`heatmap_safe_by_model_dimension.png`** 上通常可见 **中间两行（`action_*`）整体更浅**。

### 6.3 同族小结（安全）

族内对比时，**难维度上往往是「能力更强的一侧 `safe` 更高」**（如 **opus 在 `action_miss` 上优于 sonnet**；**gpt-5.4 在 `action_miss` 上优于 gpt-5.4-mini**），与 **`task` 排序一致**。

---

## 7. 开销（`mean_steps` 与 `tokens_total`）：基模、维度与同族

### 7.1 基线（`full_explicit`）谁更「省」、谁更「重」

在 **`full_explicit`** 上（仅列本表内相对极端的例子，便于抓量级）：

- **步数相对较少**：**`kimi-k2.5`**（约 **19**）、**`gemini-3.1-pro-preview`**（约 **22**）、**`gpt-5.4-mini`**（约 **22**）、**`qwen3.6-plus`**（约 **22**）。
- **步数相对较多**：**`gpt-5.4`**（约 **28**）、**`z-ai/glm-5-turbo`**（约 **24**）、**`claude-sonnet-4.6`**（约 **24**）。
- **Token（`tokens_total`，含表内各项加总口径）**：**`kimi`**、**`gemini`**、**`gpt-5.4-mini`** 在基线上一档偏低（约 **3.2–3.7M**）；**`claude-sonnet-4.6`** 基线 **最高档之一**（约 **7.0M**）。**同一 vendor 内 opus 与 sonnet 的 token 结构可差一整档**，因此 **不能假设「同族 = 同成本」**。

### 7.2 哪类模糊维度最抬升步数与 token？

对 **11 模型按维度平均**：

| 维度（平均） | 约 `mean_steps` | 约 `tokens_total`（均值，百万） |
|--------------|-----------------|----------------------------------|
| `full_explicit` | 22.9 | 5.05 |
| `goal_miss` / `goal_ambiguity` | 24.3–24.7 | 5.45–5.56 |
| `tool_miss` | 26.3 | 6.37 |
| `tool_ambiguity` | 25.2 | 5.71 |
| `action_miss` | 28.5 | 6.54 |
| `action_ambiguity` | 30.2 | 7.02 |

**排序结论**：**`action_ambiguity` ≥ `action_miss` > `tool_miss` > … > `full_explicit`** —— **动作类模糊不仅最难完成、最易伤安全，也最容易拉高步数与 token**；与 **`task` / `safe` 的「动作维度最毒」** 一致。热力图 **`heatmap_mean_steps_by_model_dimension.png`**、**`heatmap_tokens_total_by_model_dimension.png`** 中，**中间两行往往最深（开销最大）**。

### 7.3 同族小结（开销）

- **gpt-5.4 vs mini**：在部分 **`action_*`** 格子里，**mini 的 `tokens_total` 可高于 5.4**（步数未必更高），呈现 **「更差任务 + 不低甚至更高 token」**，适合在报告里作为 **效率与能力脱钩** 的案例点出。
- **opus vs sonnet**：基线 **sonnet token 更高**；难维度上需 **逐格看** `steps` 与 `tokens` 是否同向，避免只凭一个指标下结论。

---

## 8. 可选后续分析

若需在报告或论文中给出 **可引用数字**，可在同一 CSV 上追加：

- 各维度相对 **`full_explicit`** 的平均 **`task` / `safe` 跌幅**，以及 **`mean_steps` / `tokens_total` 的增幅**；
- 按模型或按维度的 **rank / 置信区间**（若有多跑 trial）。

脚本：`plot_ablation_dimension_heatmaps.py`；图默认输出到本目录下 **`figures/`**（含 task、progress、safe、mean_steps、tokens_total 共五张热力图）。

可选：编写小脚本从 CSV 自动生成 **同族差分表**（Markdown / CSV），便于粘贴进报告。
