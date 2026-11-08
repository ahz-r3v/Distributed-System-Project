# Distributed System Project

分布式系统课程报告协作仓库，采用 [USENIX 官方 LaTeX 模板](https://www.usenix.org/conferences/author-resources/paper-templates)（OSDI 使用的论文版式）。
正文为 US Letter、双栏、10 pt，支持中英文草稿；按章节拆分，便于 teammates 并行写作。
目前已完成 CacheWise 复现部分的正文初稿，加入已核对的六策略结果、工作负载图和匹配消融图；重计算与卸载分析及二级存储方法仍为后续工作，作者信息待填写。

## 开始写作

1. 修改 `paper/main.tex` 中的题目、姓名、学校和学号；按人数增删作者块。
2. 在 `notes/README.md` 记录选题、课程要求、章节分工和截止时间。
3. 编辑 `paper/sections/` 中负责的章节，逐步替换 `\draftnote{...}` 占位内容。
4. 将核实过的文献加入 `paper/references.bib`，用 `\cite{citation-key}` 引用。
5. 编译并检查 PDF，通过分支和 Pull Request 合并修改。

共享文献库已加入从原文核实的 [CacheWise 论文](https://arxiv.org/abs/2606.16824v1)。
原论文已评估 GPU–CPU DRAM 卸载；本报告拟分析二级存储（首先考虑本地 SSD）的恢复代价与方法，避免将已有的 DRAM 卸载误写为本文贡献。
正式写作时补充相关文献和实测结果，并清理草稿标记。
报告语言和篇幅按老师的要求确定。

## 论文结构

1. **Introduction**：研究动机、三个研究问题及预期贡献。
2. **Background and Related Work**：KV cache、CacheWise、内存层级及已有卸载系统。
3. **CacheWise Replication: Experiments and Results**：复现范围、实验配置、结果、消融及与原论文的差异。
4. **CacheWise Limitations: Recomputation versus Offloading**：剩余恢复开销、包含写入与读取的代价模型、盈亏平衡点及适用条件。
5. **Proposed Methods for Secondary-Storage KV Offloading**：分块存储与按需恢复、异步传输与预取、基于代价的决策，以及实现范围。
6. **Evaluation of the Proposed Offloading Methods**：端到端结果、消融、敏感性与资源代价。
7. **Discussion and Limitations**：适用范围、失败场景及有效性威胁。
8. **Conclusion**：按复现、代价分析、方法与评估的顺序总结已验证结论。

正文中的蓝色 TODO 是写作提示，不代表已有实现或实验结论。
“卸载更便宜”需说明比较指标与成立条件，不能先写成普遍结论。
已核对的复现结果及独立的未命中请求计时数据保存在 `notes/experiment-evidence/`，来源与校验值见其中的 `manifest.json`。
当前主要实验只覆盖一个 N=10 队列；没有已完成的 DRAM/SSD 卸载对比。

## 目录

```text
paper/
  main.tex             # 报告入口、标题、作者、公共宏包
  usenix2019_v3.sty    # 未修改的 USENIX 官方样式
  TEMPLATE.md          # 官方来源、校验值与课程适配说明
  sections/            # 摘要、引言、背景、复现、代价分析、卸载方法、评估、讨论、结论
  references.bib       # 共享 BibTeX 文献库
  figures/             # 图表及其可编辑源文件
  build/               # 编译产物（不提交）
notes/                 # 选题、分工、阅读笔记与实验记录
.github/workflows/     # 自动编译并保存 PDF
CONTRIBUTING.md         # 分支、审阅与写作约定
```

## 本地编译

安装 [TeX Live](https://tug.org/texlive/)（建议完整安装），确保 `xelatex`、`latexmk`、`bibtex` 在 PATH 中。
在仓库根目录运行，Windows PowerShell、macOS 和 Linux 使用相同命令：

```sh
latexmk -cd -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build paper/main.tex
```

PDF 输出至 `paper/build/main.pdf`。`latexmk` 会自动运行 BibTeX 并解析交叉引用。
使用精简 TeX 安装时，需要 `xecjk`、`fandol`、`tex-gyre`、`koma-script`（含 `scrlfile`）、`amsmath`、`amsfonts`、`graphics`、`booktabs`、`latexmk`，
以及官方样式依赖的 `times`、`pslatex`、`microtype`、`sttools`（含 `flushend`）、`cite`、`url`、`xurl`、`xcolor`、`hyperref` 及其依赖。

清理编译缓存（保留最终 PDF）：

```sh
latexmk -cd -c -outdir=build paper/main.tex
```

VS Code 可安装仓库推荐的 LaTeX Workshop 扩展，打开 `paper/main.tex`，选择 `latexmk (XeLaTeX)` 编译配方。
扩展仍需要本地 TeX 工具链。

## Overleaf

1. 在 GitHub 选择 **Code → Download ZIP**。
2. 在 Overleaf 选择 **New Project → Upload Project**，上传 ZIP。
3. 将 Main document 设为 `paper/main.tex`（如果导入后多了一层目录，则选择该目录内的同一文件）。
4. 将 Compiler 设为 **XeLaTeX**，选择可用的近期 TeX Live 版本，然后 Recompile。

建议以 GitHub 为团队共同版本来源，避免在 Overleaf 和本地同时改动同一段内容后互相覆盖。

## GitHub 自动编译

推送、Pull Request 和手动触发都会运行 [`Build paper`](https://github.com/ahz-r3v/Distributed-System-Project/actions/workflows/build-paper.yml)。
成功后，在该次 Actions 运行的 **Artifacts** 中下载 `paper-pdf`，解压得到 `main.pdf`，默认保存 14 天。
同一次运行还保存 `paper-build-log` 编译日志，失败时可用来排错。
仓库需要允许运行 GitHub Actions。

编译使用 [latex-action](https://github.com/xu-cheng/latex-action) 的 TeX Live 2026 环境。
PDF 不提交到 Git；图表用到的 PDF 文件可以提交。

## 协作

每人从 `main` 创建任务分支，例如 `writing/introduction`，完成后发 PR，由另一位 teammate 审阅正文和 PDF。
完整流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。模板来源及适配说明见 [paper/TEMPLATE.md](paper/TEMPLATE.md)。
