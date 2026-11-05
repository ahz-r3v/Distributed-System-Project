# 图表

存放论文实际使用的图表，以及可编辑源文件或生成脚本。
优先使用 PDF 矢量图；截图可使用 PNG。
生成论文的 `paper/build/main.pdf` 不提交，作为图表的 PDF 可以提交。

正文中通过 `\includegraphics{system-architecture.pdf}` 引用文件，并配上 `\caption{...}` 和 `\label{fig:architecture}`。

每张实验图应记录输入数据位置、版本、生成命令及运行环境，确保其他作者能够复现。
