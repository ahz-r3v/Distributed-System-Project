# OSDI / USENIX 模板来源

本仓库用于分布式系统课程报告，采用 USENIX 官方通用论文样式。
OSDI 的官方征稿页指向 USENIX 的作者模板资源。

- [官方模板入口](https://www.usenix.org/conferences/author-resources/paper-templates)
- [官方 LaTeX 示例](https://www.usenix.org/sites/default/files/usenix2019_v3.2.tex)
- [官方样式文件](https://www.usenix.org/sites/default/files/usenix2019_v3.sty)
- [官方示例 PDF](https://www.usenix.org/sites/default/files/usenix2019_v3.2.pdf)
- [OSDI '27 格式要求](https://www.usenix.org/conference/osdi27/call-for-papers)

## 来源记录

- 获取日期：2026-11-08。
- 本地文件：`usenix2019_v3.sty`，从上述官方地址下载，未经修改。
- 原始文件 SHA-256：`4ed9aa9d0c5daec54ce3b4188a4bf6d3bef3462c79ff65551d567511d3c45ff6`。
- 文件名中的 `2019` 是官方当前下载文件的名称，不表示本项目在使用 OSDI 2019 的投稿规则。
- 保留上游文件的原始注释与来源信息；本仓库不对该第三方文件另行声明许可证。

## 本项目的适配

- 使用 US Letter、双栏、10 pt 正文以及官方样式设置的 7 × 9 英寸正文区域。
- 使用 XeLaTeX、TeX Gyre Termes（Times 兼容字体）及 Fandol 中文字体，方便团队写中英文草稿。
- 使用官方示例中的 BibTeX `plain` 文献样式；共享文献库位于 `references.bib`。
- 将正文拆到 `sections/`，保留真实作者信息位置、页码和醒目的草稿标记。
- 不改写官方样式中的页边距、栏宽或标题布局。

这是课程报告的起点。题目、作者、学号、写作语言和篇幅按课程要求填写；
若以后正式投稿，应重新核对当届会议的匿名、页数和其他要求。
