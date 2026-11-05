# Distributed System Project

分布式系统论文协作仓库。使用 LaTeX 分章节写作，统一管理文献、图表和研究记录。
目前是写作骨架；题目、作者、研究问题和投稿模板均待团队确定。

## 目录

```text
paper/
  main.tex             # 论文入口、作者信息、公共宏包
  sections/            # 摘要与各章节，按章节分工
  references.bib       # 共享文献库
  figures/             # 图表及其可编辑源文件
  build/               # 编译产物（不提交）
notes/                 # 选题、文献阅读、讨论与实验记录
.github/workflows/     # 自动编译并保存 PDF
CONTRIBUTING.md         # 分支、审阅与写作约定
```

## 开始写作

1. 修改 `paper/main.tex` 中的论文题目和作者。
2. 在 `notes/README.md` 中记录研究问题、分工及关键决定。
3. 编辑 `paper/sections/` 中对应章节，逐步替换 `\draftnote{...}` 占位内容。
4. 将核实过的文献加入 `paper/references.bib`，使用 `\cite{citation-key}` 引用。

当前使用通用 `article` 草稿版式，支持中英文输入；确定会议或期刊后再适配官方模板。
中文采用 TeX Live 自带的 Fandol 字体，以减少不同操作系统的字体差异。

## 本地编译

安装 [TeX Live](https://tug.org/texlive/)（建议完整安装），并确保以下命令在 PATH 中可用：

```text
xelatex --version
latexmk --version
biber --version
```

在仓库根目录运行，Windows PowerShell、macOS 和 Linux 使用相同命令：

```text
latexmk -cd -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build paper/main.tex
```

PDF 输出至 `paper/build/main.pdf`。`latexmk` 会在需要时调用 Biber 并处理交叉引用。
初始文献库为空，尚未插入引用时可能出现空参考文献警告；开始引用真实文献后应消除该警告。

如使用精简 TeX 安装，需要补齐 `ctex`、`fandol`、`geometry`、`amsmath`、`amsfonts`、
`graphics`、`booktabs`、`biblatex`、`hyperref`、`latexmk` 和 `biber` 及其依赖。

VS Code 可安装仓库推荐的 LaTeX Workshop 扩展，选择 `latexmk (XeLaTeX)` 编译配方。
扩展仍需要本地 TeX 工具链。

## GitHub 编译

推送后，`Build paper` 工作流会在分支推送、Pull Request 和手动触发时编译论文。
成功后可在该次 Actions 运行的 Artifacts 中下载 `paper-pdf`，默认保存 14 天。
仓库需允许运行 GitHub Actions；工作流配置本身不代表编译已通过。

编译使用 [latex-action](https://github.com/xu-cheng/latex-action) 的 TeX Live 2026 环境，
PDF 通过 [upload-artifact](https://github.com/actions/upload-artifact) 保存。

## 协作

每项写作任务使用独立分支与 PR，尽量由另一位作者审阅后合并。
完整流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。
编译产物不进入 Git；图表用到的 PDF 文件可以提交。
