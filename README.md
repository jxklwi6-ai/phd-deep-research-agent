# PhD Deep Research Agent v3.1

**An evidence-first research skill for high-recall literature discovery, citation tracing, and Chinese DOCX reviews.**

Created by [@jxklwi6-ai](https://github.com/jxklwi6-ai). This repository publishes the reusable ChatGPT skill, its source files, the V3.1 report contract, and a ready-to-upload ZIP.

[中文说明](#中文说明)

## What it does

The skill supports six connected research capabilities: literature discovery, citation tracing, literature mapping, anchor-paper auditing, claim-directed evidence review, and scientific synthesis/reporting. It carries Discovery through evidence synthesis in one run and records search routes, access levels, screening decisions, and limitations for later review.

The report contract specifies a Chinese DOCX review with an unnumbered TL;DR, introduction, 3–6 coherent body chapters, conclusion and outlook, and ACS-like references. It favors connected synthesis and inline bracket citations. It can also produce an auditable literature map and retrieval log. The report format is documented in `references/report-output-spec-v3.1.md`.

The skill uses ChatGPT's available host search and page browsing. It reads publicly available full text when accessible; for closed or blocked papers it uses only abstracts and other information actually visible through those tools. It does not attempt to bypass paywalls or claim exhaustive coverage when search access is limited.

## Install in ChatGPT

1. Download `PhD-Deep-Research-Agent-v3.1.0-ChatGPT-Skill.zip` from this repository.
2. In ChatGPT, open **Skills** and choose **Add skill** → **Upload skill**.
3. Upload the ZIP. It contains a single installable skill folder and an MIT license.
4. Start a research request with `@PhD Deep Research Agent v3.1` or `$phd-deep-research-agent-v3-1`.

The ZIP is also available as a standalone artifact in the repository root. The unpacked files here are provided for inspection, reuse, and contributions.

## Repository layout

- `SKILL.md` — workflow and operating boundaries
- `references/` — report specification, discovery workflow, evidence policy, and record schemas
- `scripts/` — research-store, DOCX rendering, citation mapping, and quality checks
- `assets/` — report contract, blank draft scaffold, and editable Word template
- `tests/` — regression tests for the report contract, citations, and evidence records
- `PhD-Deep-Research-Agent-v3.1.0-ChatGPT-Skill.zip` — ready-to-upload ChatGPT skill

## Run checks locally

Python 3.10 or later is recommended.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## License and attribution

The skill source and helper code are released under the MIT License; see `LICENSE`. The V3.1 report specification was supplied by the project author and is included as the format contract. The four sample reading reports used while developing that contract are not included.

## 中文说明

PhD Deep Research Agent v3.1 是面向 ChatGPT 的科研文献调研 Skill，重点是高召回发现、引文追踪、锚点论文审查、证据核查和中文综述写作。它把 Discovery 与 Deep Evidence 连续完成，并记录检索路径、论文阅读层级、筛选判断及覆盖限制，便于复核文献地图和检索过程。

报告按 V3.1 规范生成中文 DOCX：太长不看版、引言、3–6 个连贯正文章节、结论与展望、ACS 风格参考文献。Skill 使用 ChatGPT 可用的网页搜索和浏览能力；开放全文可读时访问全文，闭源或受限论文只依据实际可见的摘要和相关信息，不绕过付费访问限制。

**安装：**下载仓库根目录的 `PhD-Deep-Research-Agent-v3.1.0-ChatGPT-Skill.zip`，在 ChatGPT 的 **Skills → Add skill → Upload skill** 中上传。解压后的源码、报告规范、DOCX 模板和测试也同时公开，便于同行检查和参考设计。

源码与辅助程序采用 MIT License。完整 V3.1 输出规范作为本项目作者提供的格式契约随项目发布；用于制定规范的四份样例报告未随仓库发布。
