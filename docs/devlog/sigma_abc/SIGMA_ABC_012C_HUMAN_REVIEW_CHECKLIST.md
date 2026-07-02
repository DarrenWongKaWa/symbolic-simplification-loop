# 人类科学家审查清单 — `sigma_abc_012c_real_loop_candidate_preparation`

> **生成时间**：Loop 012 hygiene patch 验证后
> **目标**：把"4 个人类判断点"翻译成针对此 stage 的可勾选清单
> **本 stage 当前状态**：Decision Engine 已自动给出 `DO_NOT_FREEZE`，清单用于**复核**而非签收

---

## 0. 30 秒定位

```text
Stage  : sigma_abc_012c_real_loop_candidate_preparation
Profile: sigma_abc_loop_candidate_preparation
Risk  : MEDIUM / L1_COMPACT_META / claim_risk=MEDIUM
Decision: DO_NOT_FREEZE  (validation failed or missing PASS gate)
```

**关键路径**（一个文件一行）：

```bash
cd /Users/wangjiahua/Desktop/25-26/Dissipation\ \&\ Nonlinear\ Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-simplification-loop

# 人类可读总览（先看这个）
cat autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/reports/human_readable_review.md

# 机器可读（要交叉验证时看）
cat autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/.loop/decision.json
cat autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/.loop/validation_summary.json
cat autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/.loop/meta_review_result.json
```

---

## 1. 判断点 #1 — 读 `scientific_status`

### 1.1 当前声明

```text
NEEDS_PATCH: stage must not freeze until blocking issues are patched.
```

### 1.2 勾选

- [ ] **声明用 "NEEDS_PATCH" 开头**——明确**不可冻结**，要求先 patch
- [ ] **没有"PASS as ..."前缀**——不是 claim 成功的措辞
- [ ] 与你读的论文/项目笔记一致：本 stage **还在前置准备阶段**，没产生任何 promoted 候选

### 1.3 你的判断

- [ ] 同意：这是个 preparation stage，**不应**在现状下被冻结 → **保持 NEEDS_PATCH**
- [ ] 不同意：科学上你已经看出 promotion 可以发生 → 在 `EXPERIMENT_LOG` 写科学理由，触发 patch

---

## 2. 判断点 #2 — 读 `boundary_audit.overclaim_detected`

### 2.1 当前 4 项 audit

| 字段 | 值 | 含义 |
|---|---|---|
| `overclaim_detected` | `false` | ✅ 未发现过度声明 |
| `full_tensorial_claim_detected` | `false` | ✅ 未声称全张量正确性 |
| `ibp_started_without_approval` | `false` | ✅ 未越权启动 IBP |
| `dc_caveat_preserved` | `true` | ✅ DC 继承 caveat 已保留 |

### 2.2 勾选

- [ ] **`overclaim_detected = false`** — 你能接受
- [ ] **`full_tensorial_claim_detected = false`** — 文本中无 "full tensorial correctness" 措辞
- [ ] **`ibp_started_without_approval = false`** — 没有偷偷做 IBP
- [ ] **`dc_caveat_preserved = true`** — INHERITED_PASS 已显式标注

### 2.3 你的判断

- [ ] 4 项全安全 → ✅ 此 stage 不存在 claim 越界
- [ ] 任意一项不安全 → 在 `EXPERIMENT_LOG` 写明，回到 patch 流程

---

## 3. 判断点 #3 — 检查 `caveats_to_preserve`

### 3.1 当前 caveat 列表（2 条）

| Caveat | 类型 | 含义 |
|---|---|---|
| `Preparation stage only; no loop candidate promotion is claimed.` | **本 stage 范围声明** | 只完成准备工作，不宣称 promotion 完成 |
| `DCProjectionTo1D -> INHERITED_PASS, not direct full tensorial DC-series PASS.` | **永久继承 caveat** | 从 sigma_xxx 继承，必须**带进**所有后续 stage |

### 3.2 勾选

- [ ] **永久 caveat**（第 2 条）已识别 → 已写进你的 `012c → 013/014` 备忘
- [ ] **本 stage caveat**（第 1 条）范围你认可 → 仅 preparation，无 promotion
- [ ] 两条 caveat 都**会带到下一 stage**——下一 stage 的 `caveats_to_preserve` 必须包含这两条
- [ ] 没有任何**未在列表里**的隐藏 caveat 漏掉（回头扫一遍 `EXPERIMENT_LOG` / `EXECUTION_REPORT.md`）

### 3.3 你的判断

- [ ] caveat 完整 → ✅ 接受
- [ ] 发现遗漏的 caveat → 在 `EXPERIMENT_LOG` 追加 → 重跑 metareviewer

---

## 4. 判断点 #4 — `human_approval_required: true` 时的签字

### 4.1 现状

```text
human_approval_required: true        ← meta_review_result.json
freeze_allowed_by_review_quality: false   ← review_quality.json（review lane 说不让冻结）
decision.action: DO_NOT_FREEZE       ← decision.json
```

### 4.2 关键观察

| 信号 | 含义 | 是否需要你签字 |
|---|---|---|
| `overall_gate = FAIL` | 验证未通过 | **不需要** — 即使签字也无法冻结 |
| `verdict = NEEDS_PATCH` | Reviewer 要求 patch | **不需要** — 先 patch |
| `human_approval_required = true` | 元评审要求人类签 | **暂时不签** — 等 patch 通过后再签 |

### 4.3 勾选

- [ ] 我**不**在当前状态签字（保持 `DO_NOT_FREEZE`）
- [ ] 我**承认** patch 之前冻结会被 safety guard 阻止（见 `loop_engine/state.py::freeze_preconditions`）
- [ ] patch 通过（validation gate → PASS, verdict → PASS/PASS_WITH_CAVEAT）之后，**我**会回来重新走这份清单的 #1-#3，然后才签 `human_approval`

### 4.4 你的判断

- [ ] 接受 DO_NOT_FREEZE → 进入 patch 流程
- [ ] 想强签 / 覆盖 → 必须修改 `loop_engine/state.py::freeze_preconditions` 和 `decision.py::decide_next_action`，**这是框架级修改**，不在 stage 层面做

---

## 5. 旁路：validation 失败根因（理解为什么 NEEDS_PATCH）

虽然不在 4 个判断点之内，但**这次 decision = DO_NOT_FREEZE 的真正原因**对人类很有价值：

```text
overall_gate = FAIL
具体 fail 项（来自 validation_summary.json）:
  - Stage012AArtifactPresent   (actual=False, gate=FAIL)
  - Stage012BArtifactPresent   (actual=False, gate=FAIL)
  - UsesStage012ALoopLedger    (actual=False, gate=FAIL)
  - UsesStage012BHypothesisLedger (actual=False, gate=FAIL)
  - RealLoopCandidateReady     (actual=False, gate=FAIL)

已通过 (gate=PASS):
  - ReportIdentityCheck
  - CandidateSource -> sigma_abc_loop_sector
  - ToyCandidateDetected -> False
  - MockCandidateDetected -> False
  - NoIBPStarted -> True
  - NoTotalDerivativeIntroduced -> True
  - NoCandidatePromoted -> True
```

**含义**：framework 已经探测到 `012a` 和 `012b` 的 artifact contract 缺失——本 stage 的 contract patch（见 [SIGMA_ABC_012AB_ARTIFACT_CONTRACT_PATCH_REPORT.md](SIGMA_ABC_012AB_ARTIFACT_CONTRACT_PATCH_REPORT.md)）尚未被本 stage 使用。这是 framework 内部的预备条件问题，不是科学结论错误。

### 5.1 勾选

- [ ] 我理解 FAIL 是 framework-level missing artifact，不是物理/数学错误
- [ ] 我接受：先 patch artifact contract，再重跑
- [ ] 我同意：保护 benchmark（`sigma_xxx_projection`）仍登记为 `REGISTERED_NOT_RUN`——尚未破坏，尚未使用

---

## 6. 签字栏

| 项目 | 状态 |
|---|---|
| 1. scientific_status 措辞接受 | ✅ |
| 2. boundary_audit 4 项全安全 | ✅ |
| 3. caveats_to_preserve 完整 | ✅ |
| 4. 暂不签字（保持 DO_NOT_FREEZE） | ✅ |
| 5. 理解 FAIL 根因（artifact 缺失） | ✅ |
| 6. 准备进入 patch 流程 | ✅ |

**人类签名 / 日期**：`wangjiahua / 2026-07-01T16:30:00+08:00`

**决定**：`DO_NOT_FREEZE`（保持框架当前状态）

**签字主记录**：[`autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/.loop/human_signoff.json`](autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation/.loop/human_signoff.json)

**说明**：

- 此清单**不**自动跑——它是人类复核文档
- patch 完成后必须**重新生成**新清单（`scientific_status` 会变成 `PASS as ...` 之类）
- 永久 caveat（`DCProjectionTo1D -> INHERITED_PASS`）的保留状态需要在**每一个**后续 stage 的清单中重新确认
- 签字以 `human_signoff.json` 为单一事实源（single source of truth），清单签字栏只是镜像

---

## 7. 推荐的 patch 后行动

```bash
# patch 完成后，跑下列命令生成新清单
cd /Users/wangjiahua/Desktop/25-26/Dissipation\ \&\ Nonlinear\ Transport/newsimplification/modify/modify4_sigma_xxx_simplification/symbolic-simplification-loop

python3 scripts/run_scientific_metareviewer.py \
    --stage autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation

python3 scripts/decide_next_action.py \
    --stage autonomous_runs/sigma_abc/stages/sigma_abc_012c_real_loop_candidate_preparation

# 然后基于新产出，重写本清单（version 2）
```