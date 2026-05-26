# 像素证据约束的 VLM 偏好优化：实验大纲

更新日期：2026-05-26

## 0. 核心判断

这个 idea 最值得打的点不是“用 DPO 缓解幻觉”，因为 HA-DPO、V-DPO、CLIP-DPO、OPA-DPO、TPO 等方向已经把回答级偏好、视觉对比偏好、on-policy 数据、任务偏好都做得很热。真正的缺口是：现有偏好信号多数仍然在完整回答层面打分，模型可能学会更顺、更短、更像人类偏好的回答，但没有被强迫回答“这句话由图像里的哪块区域、哪个对象、哪个属性或哪条关系支持”。

建议把论文暂定名写成 **Evidence-Grounded Preference Optimization, EGPO**，避免过泛的 Grounded Preference Optimization 与已有/潜在同名工作冲突。论文主张可以凝练为：

> VLM 后训练不应只优化回答偏好，而应优化“回答-证据”联合偏好；当每个关键视觉断言都被要求绑定可验证证据时，模型会更少依赖语言先验，更少生成无图像依据的幻觉。

## 1. 研究问题与假设

### 1.1 研究问题

1. 标准 DPO 在 VLM 中降低幻觉时，是否主要学到了回答风格、长度、保守性，而不是更精细的视觉证据依赖？
2. 把偏好样本从 `(image, question, chosen_answer, rejected_answer)` 扩展为 `(image, question, chosen_answer, chosen_evidence, rejected_answer, rejected_evidence)` 是否能稳定降低 object/attribute/relation hallucination？
3. 证据约束应当在训练期显式输出，还是只作为隐式训练信号，推理时仍输出自然回答？
4. 一个轻量 visual-evidence critic 能否作为数据筛选器和 reward model，提高自动构造偏好数据的质量？
5. 这种训练是否能泛化到 3D/空间场景理解，而不仅仅是在 COCO/GQA 风格图像上过拟合？

### 1.2 可检验假设

- **H1：回答级 DPO 会改善部分幻觉指标，但对属性、空间关系、遮挡关系的改进有限。**
- **H2：EGPO 在 object/attribute/relation 三类断言上都会优于标准 DPO，其中 relation gain 最大。**
- **H3：训练期要求 evidence、推理期不要求 evidence 的版本会兼顾可读性和 grounding；推理期也输出 evidence 的版本更可解释但可能牺牲用户偏好。**
- **H4：证据标签质量存在阈值效应；低质量 pseudo evidence 会伤害训练，高精度小规模证据比大规模噪声证据更有效。**
- **H5：critic-gated 自训练能在相同人工标注预算下扩大数据规模，带来更好的泛化。**

## 2. 方法设计

### 2.1 数据单元

每条训练样本包含四层信息：

```text
image / 3D scene
question or instruction
answer
claim_evidence[]
```

`claim_evidence` 建议采用统一 JSON schema，方便训练、评估和人工抽查：

```json
{
  "claims": [
    {
      "span": "the red mug is on the left side of the laptop",
      "type": "object|attribute|relation|count|spatial",
      "evidence": [
        {
          "modality": "2d_box",
          "label": "red mug",
          "box": [0.12, 0.35, 0.27, 0.62]
        },
        {
          "modality": "2d_box",
          "label": "laptop",
          "box": [0.38, 0.30, 0.72, 0.66]
        }
      ],
      "relation": "left_of",
      "support": "supported"
    }
  ]
}
```

2D 阶段优先使用 box/mask/object relation；3D 阶段再扩展为 `object_id`、`3d_box`、`scene_graph_edge`。

### 2.2 偏好样本构造

正样本必须同时满足：

- 回答正确或基本正确。
- 关键视觉断言可定位到图像证据。
- evidence 与 claim 类型一致，例如属性 claim 需要属性所在 object，relation claim 至少需要 subject/object 两个实体和关系方向。
- 回答不过度保守，不把可见事实全部拒答。

负样本分为五类：

- **对象替换**：把 visible object 换成 absent 或邻近 co-occurring object，例如 dog -> cat。
- **属性错配**：颜色、材质、数量、状态错误，例如 red -> blue、open -> closed。
- **关系反转**：left/right、above/below、in front of/behind、holding/held by 反转。
- **无证据常识补全**：答案加入看似合理但图中不可见的信息，例如“应该是早晨”“他正在去上班”。
- **证据错配**：回答文本正确，但 evidence 指向错误区域，用来验证模型是否真的学证据而不是只学答案。

### 2.3 训练目标

第一版采用 LoRA/QLoRA，避免全参微调带来的成本和不稳定。总体损失：

```text
L = L_dpo(answer) + lambda_e * L_evidence + lambda_c * L_claim_margin + lambda_r * L_refusal
```

- `L_dpo(answer)`：标准 DPO/IPO 类 pairwise preference loss。
- `L_evidence`：box token 的 CE/L1/GIoU，或 evidence JSON 的 token-level CE；如果基础模型不稳定输出 box，先用离散坐标 token。
- `L_claim_margin`：对 claim-level support score 做 margin，让 supported claim 分数高于 unsupported claim。
- `L_refusal`：避免模型通过“看不清/无法判断”虚假降低幻觉；只在证据不足样本上奖励拒答。

论文里可以把 EGPO 写成两种实现：

- **EGPO-Explicit**：训练和推理都输出答案 + evidence。优点是可解释；缺点是回答冗长，用户偏好可能下降。
- **EGPO-Latent**：训练时输出 evidence，推理时用系统 prompt 或 decoding mask 隐藏 evidence，只输出答案。优点是更接近真实产品体验。

### 2.4 Visual-Evidence Critic

critic 输入 `(image, claim, evidence)`，输出：

- `support_score`：0-1 或 1-5。
- `error_type`：object absent、attribute mismatch、relation mismatch、wrong evidence、uncertain。
- `rationale`：短解释，仅用于开发分析，不作为主评测。

critic 用途：

- 自动筛掉 pseudo-label 中 evidence 明显错误的样本。
- 给 rejected sample 标注错误类型，构造更平衡的负样本。
- 在线自训练：主模型生成多个回答，critic 选出 evidence 更可靠的 chosen/rejected。
- 作为额外 baseline：只在推理后 rerank，不改主模型，比较训练式 EGPO 与 test-time rerank 的差异。

## 3. 数据计划

### 3.1 Pilot 数据集

第一阶段只做 2D，目标是 5k-20k preference pairs。

| 数据来源 | 用途 | 规模建议 | 证据来源 |
| --- | --- | ---: | --- |
| GQA | object/attribute/relation QA | 5k-10k | scene graph |
| Visual Genome | relation 与区域描述 | 5k-10k | object/attribute/relation annotations |
| RefCOCO/+/g | 指代表达 grounding | 3k-8k | box/mask |
| COCO caption / LLaVA-style instruction | 开放描述与自然问答 | 5k-10k | detector + strong VLM pseudo evidence |

### 3.2 Main 数据集

第二阶段扩大到 50k-100k preference pairs。

- GQA/Visual Genome 作为主要结构化证据来源。
- RefCOCO/+/g 增强 object localization。
- 加入 5k-10k VisionArena 风格开放问答，测试真实用户问题上的可用性。
- 每类负样本保持大致均衡：object 25%、attribute 25%、relation 25%、commonsense hallucination 15%、wrong evidence 10%。

### 3.3 人工抽查

不建议做大规模人工标注，先做高质量抽查：

- Pilot：人工检查 500 条，估计 pseudo evidence precision。
- Main：人工检查 1,500-2,000 条，按错误类型分层抽样。
- 接受门槛：chosen evidence precision > 90%，rejected error label precision > 85%。低于这个门槛时，先优化数据构造，不进入大规模训练。

### 3.4 3D 扩展

3D 不应作为第一轮主实验，否则数据和工程变量会压过方法贡献。建议作为第三阶段：

- ScanRefer：3D object localization with language。
- ScanQA：3D QA / spatial scene understanding。
- ScanNet：提供 3D scene/object annotations。

3D 目标不是全面打 SOTA，而是验证 EGPO 对空间关系、对象指代、遮挡/方位错误有迁移价值。

## 4. 实验矩阵

### 4.1 模型选择

主线建议使用两个 backbone：

| 角色 | 模型 | 理由 |
| --- | --- | --- |
| 开发/快速迭代 | Qwen2.5-VL-3B-Instruct | 支持定位能力，单卡可跑，适合调数据和 loss |
| 主结果 | Qwen2.5-VL-7B-Instruct 或 LLaVA-OneVision/LLaVA-1.5-7B | 7B/8B 是 CVPR 论文常见甜点位，能与已有 DPO hallucination work 对齐 |
| 可选增强 | LLaVA-OneVision-1.5-8B | 若代码和权重可用，适合做更强开源基线 |

若时间紧，主结果只保留一个强 backbone + 一个弱 backbone sanity check。

### 4.2 Baselines

必须比较：

- **Base Instruct**：原始模型。
- **SFT**：只学 answer + evidence 格式，不做偏好优化。
- **Answer-DPO**：标准回答级 DPO。
- **EGPO-Explicit**：答案和 evidence 联合偏好优化。
- **EGPO-Latent**：训练期证据，推理期自然回答。
- **Critic Rerank**：主模型不训练，critic 从多个候选中 rerank。

可选比较：

- HA-DPO 风格 hallucination-aware pairs。
- V-DPO / image-contrast preference。
- CLIP-DPO 风格 CLIP similarity preference。
- OPA-DPO 风格 on-policy correction。

### 4.3 主实验

| 编号 | 实验 | 目的 | 成功标准 |
| --- | --- | --- | --- |
| E0 | 数据质量审计 | 验证 pseudo evidence 可用 | chosen evidence precision > 90% |
| E1 | SFT vs Answer-DPO | 复现回答级偏好对幻觉的基础收益 | DPO 优于 SFT，但 relation/attribute 仍有明显错误 |
| E2 | Answer-DPO vs EGPO | 验证核心 claim | EGPO 在 AMBER/POPE/CHAIR 与 grounding 指标同时提升 |
| E3 | Explicit vs Latent | 判断论文主推版本 | Latent 保持用户偏好，Explicit 提供可解释性 |
| E4 | 负样本类型 ablation | 找出最关键的数据构造 | relation/wrong-evidence ablation 后性能下降明显 |
| E5 | 证据质量 ablation | 证明不是单纯数据量 | 高质量小数据 > 低质量大数据 |
| E6 | critic-gated self-training | 验证扩展能力 | 同等人工预算下提升 hallucination 与 evidence F1 |
| E7 | general benchmark regression | 防止模型变笨或过度保守 | MMMU/MMBench/GQA 不明显下降，拒答率不过高 |
| E8 | 3D transfer | 验证空间场景价值 | ScanQA/ScanRefer 空间关系子集有增益 |

### 4.4 Ablation 细节

- 去掉 `L_evidence`，只保留 DPO。
- 去掉 wrong-evidence negatives。
- 去掉 relation negatives。
- chosen/rejected 使用 off-policy outputs vs on-policy outputs。
- evidence 只用 box vs box + relation edge。
- 推理时强制输出 evidence vs 不输出 evidence。
- critic 用 BCE 训练 vs DPO 训练。
- LoRA rank：16/32/64。
- 数据规模：5k/20k/50k/100k。

## 5. 评测指标

### 5.1 幻觉与事实一致性

- **POPE**：object hallucination yes/no probing。
- **AMBER**：existence、attribute、relation hallucination，适合本方法主张。
- **CHAIRs / CHAIRi**：caption 中句子级/实例级 object hallucination。
- **MMHal-Bench / HallusionBench**：开放式 hallucination 与视觉错觉/语言先验压力测试。

### 5.2 证据定位

- RefCOCO/+/g：Acc@0.5、mIoU。
- GQA/Visual Genome 自建 claim-evidence set：claim support F1、relation direction accuracy。
- Wrong-evidence detection：文本正确但 evidence 错误时，模型/critic 能否识别。

### 5.3 有用性与通用能力

- GQA、VQAv2、MMBench、MMMU 或 MMMU-Pro：检查能力回退。
- VisionArena-style pairwise judge：比较自然回答偏好。
- VL-RewardBench：检查 reward/judge 是否真的看图，而不是奖励漂亮文本。
- 人工 pairwise evaluation：200-500 例，至少统计 helpfulness、visual correctness、evidence correctness、over-refusal。

### 5.4 过度保守与风格偏移

必须单独统计：

- refusal rate。
- “无法判断/看不清”比例。
- 平均回答长度。
- claim density：每 100 token 中视觉断言数量。
- supported claim ratio：有证据支持的 claim / 全部视觉 claim。

## 6. 算力需求与时间估计

以下估计默认 LoRA/QLoRA、bf16、sequence length 2048、图像分辨率不超过 1024、global batch 64-128、训练 1-2 epoch。不包含商业 API 标注费用。全参微调成本会显著更高，第一篇论文不建议走全参路线。

### 6.1 Pilot

| 项目 | 配置 | 规模 | 预计时间 |
| --- | --- | ---: | --- |
| 数据生成 | 1x A100 40/80GB 或 1x RTX 4090 | 5k-20k prompts，2-4 candidates | 3-10 小时 |
| SFT | 1x A100 40/80GB 或 1x RTX 4090 | 5k-20k examples | 1-4 小时 |
| DPO/EGPO | 1-2x A100 80GB | 5k-20k pairs | 3-8 小时 |
| critic | 1x A100 40/80GB | 10k-30k claim pairs | 2-6 小时 |
| 评测 | 1x A100 40/80GB | POPE/AMBER/GQA/RefCOCO 子集 | 4-12 小时 |

Pilot 墙钟时间：**1-2 天**。GPU 消耗：约 **2-5 A100 GPU-days**。

### 6.2 Main

| 项目 | 配置 | 规模 | 预计时间 |
| --- | --- | ---: | --- |
| 数据生成与筛选 | 2-4x A100 80GB | 50k-100k prompts，2-4 candidates | 0.5-1.5 天 |
| SFT warmup | 4x A100 80GB | 50k-100k examples | 4-10 小时 |
| Answer-DPO | 4x A100 80GB | 50k-100k pairs | 8-18 小时 |
| EGPO | 4x A100 80GB | 50k-100k pairs | 12-30 小时 |
| critic training | 2x A100 80GB | 100k-300k claim pairs | 6-16 小时 |
| 全量评测 | 2-4x A100 80GB | 5-8 个 benchmark | 1-2 天 |

Main 墙钟时间：**4-7 天**。GPU 消耗：约 **20-45 A100 GPU-days**。如果只有 2 张 A100，墙钟时间大概翻倍；如果有 8 张 H100，可压到 2-4 天。

### 6.3 Full / 3D 扩展

| 项目 | 配置 | 规模 | 预计时间 |
| --- | --- | ---: | --- |
| 3D 数据整理 | CPU + 1x GPU | ScanQA/ScanRefer 子集 | 2-5 天工程时间 |
| 3D adapter 或 scene-token preprocessing | 2-4x A100 80GB | 10k-50k 3D samples | 1-3 天 |
| 3D EGPO | 4-8x A100/H100 | 20k-80k pairs | 2-5 天 |
| 3D eval | 1-2x A100 80GB | ScanQA/ScanRefer | 0.5-1 天 |

3D 扩展 GPU 消耗：约 **20-60 A100 GPU-days**，更大的风险是数据/工程时间，而不是训练本身。

## 7. 预期结果

合理的目标不是所有 benchmark 暴涨，而是出现一致、可解释的局部收益：

- 相对 Answer-DPO，EGPO 在 AMBER relation/attribute 子项上提升 **3-8 points**，在 POPE F1 或 accuracy 上提升 **1-4 points**。
- 在 CHAIRs/CHAIRi 上相对降低 **10%-25%** hallucination，尤其是长 caption 和开放描述。
- RefCOCO/Visual Genome claim-evidence set 上 evidence Acc@0.5 提升 **5-15 points**。
- EGPO-Latent 的自然回答 win rate 与 Answer-DPO 接近，EGPO-Explicit 的 evidence correctness 更高但 helpfulness 可能略低。
- critic rerank 能带来一部分收益，但不如训练式 EGPO；这能支撑“证据偏好应进入模型参数，而不只是后处理”。
- 3D 子实验中，空间关系和对象指代问题应比普通 QA 更受益；若 ScanQA 总分提升不明显，可以报告 spatial subset gain。

可能的负结果也值得提前设计：

- 如果 EGPO 只提升 grounding，不提升 hallucination，说明模型学会了输出 box 但没有减少无证据断言，需要加 wrong-evidence negatives 和 claim support margin。
- 如果 hallucination 降低但通用能力下降，说明模型过度保守，需要加入 refusal penalty 与 helpfulness reward。
- 如果 pseudo evidence 噪声导致不稳定，论文可以转向“高质量小证据集 + critic 筛选”的数据效率主张。

## 8. Related Work

### 8.1 VLM 偏好与奖励

- [VisionArena: 230k Real World User-VLM Conversations with Preference Labels](https://openaccess.thecvf.com/content/CVPR2025/html/Chou_VisionArena_230k_Real_World_User-VLM_Conversations_with_Preference_Labels_CVPR_2025_paper.html), CVPR 2025。提供真实用户 VLM 对话与偏好票，是说明“VLM preference data 正在主流化”的关键来源，但它的偏好多数是对完整回答/对话的整体偏好。
- [VL-RewardBench: A Challenging Benchmark for Vision-Language Generative Reward Models](https://openaccess.thecvf.com/content/CVPR2025/html/Li_VL-RewardBench_A_Challenging_Benchmark_for_Vision-Language_Generative_Reward_Models_CVPR_2025_paper.html), CVPR 2025。强调 VL reward model 评测仍困难，强模型也会在视觉判断上失效；可作为 reward/judge 泛化评测。
- [Task Preference Optimization](https://openaccess.thecvf.com/content/CVPR2025/html/Yan_Task_Preference_Optimization_Improving_Multimodal_Large_Language_Models_with_Vision_CVPR_2025_paper.html), CVPR 2025。把视觉任务标签转成 differentiable task preferences，说明细粒度视觉任务能帮助 MLLM；与 EGPO 的区别是 TPO 偏 task-head/task-token，而 EGPO 偏 claim-level evidence。

### 8.2 幻觉缓解与 VLM-DPO

- [Direct Preference Optimization](https://papers.neurips.cc/paper_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7-Abstract-Conference.html), NeurIPS 2023。DPO 是基础优化框架，优点是实现简单、训练稳定。
- [HA-DPO](https://arxiv.org/abs/2311.16839), arXiv 2023/2024。将幻觉缓解重写为偏好选择任务，构造 hallucination vs non-hallucination pairs。
- [V-DPO](https://aclanthology.org/2024.findings-emnlp.775/), EMNLP Findings 2024。强调用视觉引导偏好减弱语言先验，包含 response-contrast 和 image-contrast preferences。
- [CLIP-DPO](https://arxiv.org/abs/2408.10433), ECCV 2024。用 CLIP image-text similarity 自动排序生成候选，降低对付费 API 和外部 LVLM 的依赖。
- [Multi-Modal Hallucination Control by Visual Information Grounding](https://arxiv.org/abs/2403.14003), CVPR 2024。指出生成越长越依赖语言先验，并提出 M3ID；也展示了 M3ID+DPO 能减少 hallucination。
- [OPA-DPO / On-Policy Data Hold the Key](https://openaccess.thecvf.com/content/CVPR2025/html/Yang_Mitigating_Hallucinations_in_Large_Vision-Language_Models_via_DPO_On-Policy_Data_CVPR_2025_paper.html), CVPR 2025。说明 on-policy preference construction 对 DPO 效果非常关键。EGPO 需要吸收这个结论，优先用当前 reference model 自己生成 rejected answers。
- [Fine-Grained Preference Optimization Improves Spatial Reasoning in VLMs](https://arxiv.org/abs/2506.21656), arXiv 2025/2026。是最接近的风险点之一，提出 segment-specific preference granularity 和 spatial reward。EGPO 必须明确差异：我们的 evidence 是 claim-level 可验证视觉证据，覆盖 object/attribute/relation/wrong-evidence，并把 evidence correctness 作为核心训练与评测对象。

### 8.3 Critic / Judge

- [Critic-V](https://openaccess.thecvf.com/content/CVPR2025/html/Zhang_Critic-V_VLM_Critics_Help_Catch_VLM_Errors_in_Multimodal_Reasoning_CVPR_2025_paper.html), CVPR 2025。用偏好优化训练 VLM critic 给 reasoning path 提供自然语言 critique。EGPO 的 critic 更窄：判断 claim-evidence 是否被图像支持，可用于数据筛选与 rerank。

### 8.4 Grounding 与评测数据

- [GQA](https://cs.stanford.edu/people/dorarad/gqa/about.html)。包含基于 Visual Genome 的 scene graph、objects、attributes、relations，适合构造 claim/evidence。
- [Visual Genome](https://homes.cs.washington.edu/~ranjay/visualgenome/index.html)。包含 region descriptions、objects、attributes、relationships，是构造关系型 evidence 的基础。
- [RefCOCO/+/g](https://flageval.baai.ac.cn/docs/en/multimodal/Visual-Grounding/RefCOCO_RefCOCO%2B_RefCOCOg-Visual_Grounding.html)。适合 grounding Acc@0.5/mIoU 评估。
- [POPE](https://arxiv.org/abs/2305.10355) 与 [AMBER](https://arxiv.org/abs/2311.07397)。分别覆盖 object hallucination probing 和多维 hallucination，适合作为主评测。
- [ScanQA](https://arxiv.org/abs/2112.10482)、[ScanRefer](https://daveredrum.github.io/ScanRefer/)、[ScanNet](https://www.scan-net.org/)。用于 3D 场景理解扩展。

### 8.5 Backbone 相关

- [Qwen2.5-VL](https://arxiv.org/abs/2502.13923)。具备定位框/点、文档/图表/长视频能力，是 EGPO 的强候选 backbone。
- [LLaVA-OneVision-1.5](https://arxiv.org/abs/2509.23661)。提供开放训练框架与强 8B/4B baseline，可作为更贴近 LLaVA 系生态的对照。

## 9. 论文结构建议

1. **Introduction**：回答级偏好让模型更会“说”，但不一定更会“看”；提出 answer-evidence joint preference。
2. **Problem Formulation**：定义 claim、evidence、support，以及 EGPO preference pair。
3. **Data Construction**：从 scene graph/grounding dataset/strong VLM 生成正负证据样本，重点解释 wrong-evidence negatives。
4. **Method**：EGPO loss、Explicit/Latent 两种推理模式、visual-evidence critic。
5. **Experiments**：主表比较 Base/SFT/DPO/EGPO；ablation；critic；generalization；3D optional。
6. **Analysis**：错误类型、证据质量、over-refusal、case study。
7. **Limitations**：证据标注成本、box 对抽象视觉属性不够、3D 工程复杂、critic bias。

## 10. 里程碑

| 周期 | 目标 | 交付物 |
| --- | --- | --- |
| Week 1 | 数据 schema、GQA/RefCOCO 子集、负样本构造 | 5k clean pairs + 100 人工审计 |
| Week 2 | Qwen2.5-VL-3B pilot：SFT/DPO/EGPO | pilot 主表 + 20 个 case study |
| Week 3 | 数据扩大到 20k-50k，训练 critic | critic accuracy + gated dataset |
| Week 4 | 7B main experiments | AMBER/POPE/RefCOCO/GQA 主结果 |
| Week 5 | ablations 与 human eval | ablation tables + 500 人工偏好 |
| Week 6 | 3D 或 VL-RewardBench 泛化 | optional section |
| Week 7 | 论文写作与图表 | full draft |

## 11. 最小可行版本

如果只剩 2-3 周，建议做一个收敛版：

- Backbone：Qwen2.5-VL-3B + Qwen2.5-VL-7B。
- 数据：GQA + RefCOCO + Visual Genome，共 20k pairs。
- 方法：SFT、Answer-DPO、EGPO-Latent。
- 评测：AMBER、POPE、RefCOCO Acc@0.5、GQA subset、人评 200 条。
- Ablation：去掉 evidence loss、去掉 wrong-evidence negatives、数据规模 5k/20k。

这个版本已经能验证核心主张：**回答级偏好不够，claim-level evidence preference 能带来更可靠的视觉对齐。**
