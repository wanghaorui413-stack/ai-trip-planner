# Evaluation Framework

## 1. 评测目标

本评测体系用于衡量 AI Trip Planner RAG 在 MVP mock data 阶段的结构化行程生成质量。它关注产品可用性，而不是评估真实世界价格、库存或路线准确性。

评测数据全部为合成旅行规划场景，不包含真实用户数据、个人身份信息、真实订单、真实支付或真实出行记录。

## 2. 评测资产

| 文件 | 作用 |
| --- | --- |
| `evals/test_cases.json` | 合成旅行规划测试集，覆盖目的地、预算、偏好、天数和同行类型 |
| `evals/evaluate_plans.py` | 离线评测脚本，可直接调用本地 planner 或读取 predictions JSON |
| `docs/EVALUATION.md` | 指标定义、运行方式、Bad Case 分析模板 |

## 3. 核心指标

| 指标 | 类型 | 定义 | MVP 通过建议 |
| --- | --- | --- | --- |
| `budget_fit` | 0-1 score + pass/fail | 选中方案 `total_budget` 是否不超过用户预算；无预算时默认通过 | 单 case 必须通过，平均 >= 0.90 |
| `preference_match` | 0-1 score | 方案 POI category、tags、theme、strategy 是否覆盖期望偏好 | 平均 >= 0.75 |
| `plan_completeness` | 0-1 score | 顶层、候选、每日行程、POI、酒店、交通、预算拆分字段是否完整 | 平均 >= 0.95 |
| `daily_load` | 0-1 score | 每天 POI 数量和预计时长是否符合同行类型与 case expectation | 平均 >= 0.85 |
| `warning_count` | integer | validator 或评测选中方案中的 warning 数量 | 核心 case <= 1 |

## 4. 指标解释

### budget_fit

预算适配检查用户输入预算与候选方案 `total_budget`。如果 case 设置 `max_budget_overrun_pct`，评测允许轻微超预算；默认不允许超预算。当前预算来自 mock 估算规则，不代表真实世界成本。

### preference_match

偏好匹配检查方案内容是否覆盖合成 case 中的 `expected_preferences`。评测优先匹配 POI 的 `category`、`tags`、每日 `theme` 和候选 `strategy`，避免只因为模型复述用户输入就获得高分。

### plan_completeness

完整性检查结构化输出 contract，包括：

- 顶层：目的地、天数、币种。
- 候选：ID、标题、每日行程、酒店、交通、预算、评分、warnings。
- 每日：day、theme、pois、meal_suggestion、daily_transport、estimated_day_cost。
- POI：name、category、duration_hours、estimated_cost、reason、tags。
- 预算：poi、hotel、transport、food、contingency、total。

### daily_load

每日负载衡量行程是否“可走”。不同同行类型使用不同 POI 上限：亲子、长辈、商务更低，朋友和独行可稍高。评测同时考虑 POI 数量和 `duration_hours` 总和。

### warning_count

warning 是产品质量信号，也是用户提示信号。过多 warning 说明方案可能字段缺失、超预算或行程过载。MVP 阶段 warning 不一定代表不可用，但必须被记录和分析。

## 5. 如何运行

默认模式会直接调用本地 `planner.plan_trip`：

```bash
python evals/evaluate_plans.py
```

写出完整报告：

```bash
python evals/evaluate_plans.py --output evals/latest_report.json
```

评测外部预测结果：

```bash
python evals/evaluate_plans.py --predictions evals/predictions.json --output evals/latest_report.json
```

探索模式下不让失败 case 影响退出码：

```bash
python evals/evaluate_plans.py --no-fail
```

## 6. Predictions JSON 兼容格式

评测脚本支持以下常见结构：

```json
{
  "tc_001_shanghai_solo_citywalk_budget": {
    "destination": "shanghai",
    "days": 2,
    "candidates": []
  }
}
```

或按 test case 顺序排列：

```json
[
  {
    "destination": "shanghai",
    "days": 2,
    "candidates": []
  }
]
```

也支持 API 常见的 `{ "data": ... }` 包裹。

## 7. 发布门槛建议

| 场景 | 门槛 |
| --- | --- |
| 修改 UI 展示 | 至少运行 evaluator，确认 plan_completeness 未下降 |
| 修改 planner | 全量 test cases 通过，重点看 daily_load 和 preference_match |
| 修改 budget_estimator | budget_fit 不下降，超预算 warning 可解释 |
| 修改 ranker | Top-1 候选的 preference_match 和 budget_fit 不下降 |
| 修改 validator | warning_count 变化必须有文档说明 |

## 8. Bad Case 分类

| 类型 | 表现 | 常见原因 | 优先级 |
| --- | --- | --- | --- |
| Budget Overrun | Top-1 方案超预算 | 排序权重不足、预算估算过高、预算解析错误 | P0 |
| Preference Miss | 用户偏好未被实际 POI 覆盖 | tags 不全、alias 缺失、排序未重视偏好 | P0 |
| Incomplete Schema | 缺少字段或字段为空 | planner contract 漂移、API 包装变化 | P0 |
| Overloaded Day | 每日 POI 或时长过多 | 同行类型未生效、profile poi_count 过高 | P1 |
| Excess Warnings | warning 过多 | 预算/字段/天数校验失败 | P1 |
| Generic Plan | 方案过于模板化 | 城市 POI 不足、RAG source 不足 | P2 |
| Misleading Certainty | 把 mock 估算写成确定事实 | 文案或 reason 缺少阶段声明 | P0 |

## 9. Bad Case 分析模板

```markdown
## Bad Case: <case_id>

### 1. 基本信息
- 发现日期：
- 评测版本：
- 相关模块：planner / ranker / budget_estimator / validator / RAG / UI
- 当前阶段：MVP mock data

### 2. 输入
- destination：
- days：
- budget：
- preferences：
- traveler_type：

### 3. 失败指标
- budget_fit：
- preference_match：
- plan_completeness：
- daily_load：
- warning_count：

### 4. 现象
描述用户会看到什么问题。不要使用真实用户信息；如需举例，使用合成场景。

### 5. 期望行为
说明在 MVP mock data 约束下，系统应该如何输出。

### 6. 初步原因
- 数据问题：
- 规则问题：
- 排序问题：
- 文案/解释问题：
- 评测 case 或指标问题：

### 7. 修复方案
- 短期修复：
- 长期方案：
- 是否需要新增回归 case：

### 8. 验证结果
- 修复前报告：
- 修复后报告：
- 指标变化：
```

## 10. 人工评审补充

自动评测无法完全判断旅行体验。重要 demo 前建议人工抽查：

- 推荐是否符合常识和目的地语境。
- 文案是否明确 mock estimate，不制造确定性误导。
- 每日行程是否有合理主题，不只是 POI 堆叠。
- 亲子、长辈、商务场景是否明显降负载。
- 预算拆分是否容易理解。

## 11. 评测路线图

| 阶段 | 增强方向 |
| --- | --- |
| MVP | 合成 test cases + 规则指标 + bad case 模板 |
| Alpha | 引入人工标注偏好匹配、路线合理性和文案可信度 |
| Beta | 接入真实 source freshness、营业时间和地图距离校验 |
| GA | 建立线上反馈、A/B 实验、用户满意度和转化指标 |
