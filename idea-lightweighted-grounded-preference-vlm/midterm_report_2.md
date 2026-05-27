# 第二次中期进展报告

更新日期：2026-05-27

## 1. 当前总体状态

项目已经从“验证轻量 evidence hint 是否带来稳定正收益”进入收口阶段。5k mixed COCO/GQA 主实验、Hard COCO、evidence-style prompt、Base-error-mined diagnostic、10k mixed scale-up、POPE/AMBER 外部评测，以及 Phase-2 第一轮三组方法变体均已完成。当前没有必须继续排队的新训练或大规模评测任务。

论文路线已确定为 controlled diagnostic study，而不是强正向方法论文。核心结论是：模板化 evidence hint 能在若干对象存在评测上小幅降低 false-positive rate，但不能稳定超过普通 Answer-DPO 的 Acc/F1；10k scale-up 与 Phase-2 方法变体都没有改变这个判断。

## 2. 已完成实验

5k mixed 主实验使用 Qwen2.5-VL-7B-Instruct、LoRA-DPO、1 epoch、DPO beta 0.1。训练数据为 3,500 条 COCO object-existence pairs 和 1,500 条 GQA simple attribute/relation pairs。主比较仍保持三组：Base Instruct、Answer-DPO、Evidence-Hint DPO。

主评测结果已经完整：COCO held-out 上 Base/Answer-DPO/Evidence-Hint Acc 为 0.959/0.961/0.961；GQA simple 为 0.764/0.768/0.766；Hard COCO 为 0.944/0.950/0.946。Evidence-Hint 在 COCO 与 Hard COCO 上有更低或相同的 FPR，但 Acc/F1 没有稳定超过 Answer-DPO。

Base-error-mined diagnostic 也支持同一判断。Locked set 共 527 条 Base 错误样本，Answer-DPO recovery 为 0.063，Evidence-Hint recovery 为 0.030。Evidence-Hint 仅在 false-positive recovery 上有 2/123 vs. 1/123 的微小优势，不足以支撑强正向结论。

10k mixed scale-up 已完成：6,000 COCO + 4,000 GQA，独立数据、adapter 与 `mixed10k` 评测输出。结果没有翻转趋势：COCO/GQA/Hard COCO Acc 上 Answer-DPO 为 0.965/0.769/0.948，Evidence-Hint 为 0.961/0.766/0.944；Evidence-Hint 仍降低 FPR，但 Acc/F1 均未超过 Answer-DPO。

官方外部评测链路也已补齐并跑完。POPE random/popular/adversarial 和 AMBER discriminative 均未显示 Evidence-Hint 的一致优势；Answer-DPO 通常有很小的 Acc/F1 边际优势，Evidence-Hint 更接近 Base。

## 3. Phase-2 方法变体

Phase-2 第一轮只改变 preference 格式，不扩大主实验组数。三组低成本变体均复用 5k mixed split、Qwen2.5-VL-7B、LoRA-DPO 和 ZeRO-2：

- Evidence-Only DPO：chosen/rejected 答案文本相同，只改变 evidence consistency。
- Input-Side Evidence DPO：把 supported evidence 放入用户输入，response 保持普通短回答。
- Chosen-Only Evidence DPO：只在 chosen response 后追加 supported evidence。

训练 jobs 64302-64304 与 after-ok 评测 jobs 64305-64316 均已完成。Input-Side Evidence 是三组里最稳的一种：COCO/GQA/Hard COCO Acc 为 0.961/0.768/0.947，Base-error recovery 为 0.044。但它仍低于或接近 Answer-DPO 主线结果，不能作为新的强结论。Evidence-Only 和 Chosen-Only 也没有明显改善，尤其 Evidence-Only 在 Base-error recovery 上只有 0.015。

Phase-2 的价值主要是解释性：简单地移动 evidence 位置或只训练 evidence consistency，并不足以解决当前问题；后续若继续推进，需要更强的 evidence 生成、人工验证或区域级 grounding 信号，而不是继续堆同类模板变体。

## 4. 论文状态

`paper/main.tex` 已改成诊断型 CVPR 草稿，并纳入真实 mixed 主结果、Hard COCO、Base-error-mined diagnostic、evidence-style prompt 和 10k scale-up 结论。当前 review PDF 已编译通过，`paper/build/main.pdf` 为 5 页；带 appendix 的 `paper/build/main_full.pdf` 为 7 页。正文仍满足“不超过 6 页”的项目约束。

当前写作应坚持三点：

- 主实验只保留 Base、Answer-DPO、Evidence-Hint DPO 三组。
- 10k、POPE/AMBER、Base-error-mined 和 Phase-2 都作为诊断/补充证据，不把论文改成多方法大比较。
- 结论不声称 evidence hint 解决 hallucination，只声称本仓库构造了一个可复现的小规模边界测试，并显示模板级 hint 的作用有限。

## 5. 风险与后续安排

主要风险不再是实验缺失，而是叙事过度。结果本身偏负向，如果论文口吻仍像方法增益论文，会显得证据不足。因此后续写作要主动解释 ceiling effect、yes/no bias、FPR/FNR trade-off 和模板 evidence 的弱监督属性。

下一步优先级：

1. 通读 `paper/main.tex`，把所有强正向措辞改成边界诊断措辞。
2. 将 Phase-2 结果只放入 appendix 或项目报告，不进入三组主表。
3. 从已有 generation JSONL 中挑少量 case study，服务于 failure analysis，而不是强行展示胜例。
4. 最后再跑一次轻量 LaTeX 编译，确认正文仍为 5-6 页且无表格溢出。

当前不建议继续提交新的 7B 训练或大规模评测，除非明确改变研究问题。
