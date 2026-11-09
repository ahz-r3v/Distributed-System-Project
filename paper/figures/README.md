# 图表

存放论文实际使用的图表，以及可编辑源文件或生成脚本。
优先使用 PDF 矢量图；截图可使用 PNG。
生成论文的 `paper/build/main.pdf` 不提交，作为图表的 PDF 可以提交。

正文中通过 `\includegraphics{system-architecture.pdf}` 引用文件，并配上 `\caption{...}` 和 `\label{fig:architecture}`。

每张实验图应记录输入数据位置、版本、生成命令及运行环境，确保其他作者能够复现。

## 计划图表

| 章节 | 图表 | 需要的证据 |
| --- | --- | --- |
| CacheWise 复现 | 原论文与复现实验的配置及结果对照表 | 原文位置、实际配置、原始结果与不确定性 |
| CacheWise 复现 | 会话服务时间、淘汰与重计算开销随并发变化 | 各策略在相同负载下的重复实验 |
| 代价分析 | 重计算、DRAM 与 SSD 恢复时间曲线及盈亏平衡区域 | 相同缺失前缀、完整写入/读取、受控文件缓存 |
| 卸载方法 | GPU–DRAM–SSD 架构与块生命周期 | 与实际实现一致的数据路径和状态转换 |
| 方法评估 | 端到端效果、消融与敏感性图 | 固定策略下各存储方法的结果、I/O 与资源开销 |

正文已加入六策略结果表和独立的未命中计时表，来源快照及校验值在 `notes/experiment-evidence/`。
Part 1 已加入四幅有数据来源和生成脚本的图：

- `replication-workload.pdf`：去重后的输入/输出长度、消息数和常见工具时长。
- `replication-serving.pdf`：历史六策略会话时间及每轮匹配的策略效果。
- `replication-coverage-serving.pdf`：新增覆盖实验的并发曲线，以及五种设置下每轮匹配的预测淘汰效果。
- `replication-coverage-accounting.pdf`：五种设置下的完整分配淘汰事件、已完成请求的未命中 prompt usage，以及每轮 P99 请求时延。

`prepare_replication_data.py` 从实验仓库生成紧凑数值证据；`plot_replication.py` 可仅凭本仓库内的证据重建图。
具体命令、图表取舍及剩余实验见 `notes/README.md` 的 Part 1 记录。
`replication-figure-provenance.json` 记录输入与绘图脚本校验值；`replication-paired-effects.csv` 保存图中每轮对比的数值。
已有的 job-10807 图对应早期五策略实验，不能直接用作最新六策略统一实验的图。
其他拟议图表仍待生成，不使用虚构数据填充。

## Completed coverage study

Run `python paper/figures/plot_coverage.py` from the repository root with NumPy
and Matplotlib installed. It uses only archived evidence in this repository;
no cluster access or inference job is required.

The generator verifies comparison/completion/CSV/amendment hashes, all 60
registered setting/repeat/policy rows, the 6,384-request total, workload/token
accounting, and the retained single preemption. It produces vector PDFs, PNG
previews, the workload/results LaTeX tables used by the paper, a numeric summary,
and a CSV of matched effects. `replication-coverage-provenance.json` records input,
script, and output hashes plus library versions.

All points are equal-weight three-repeat means unless individual repeats are
shown. Whiskers span observed minima and maxima; they are not confidence
intervals. Percentage changes in the matched-effects CSV compare policies in
the same GPU block; prose/table comparisons use ratios of the corresponding
three-repeat means. First-use marks count prompt growth once per segment,
excluding prior output already counted as generated tokens.

The coverage study remains separate from the historical six-policy study.
Its final status is `complete_with_protocol_deviation`: A20 repeat 0 has one
preemption under prefix-aware/predictive eviction. The original rejection is
preserved. Uncached usage is not all executed prefill, additional preemption
work is unknown, and eviction-event counts are not bytes transferred.
