# SkillHub 上架草案

## 基本信息

- 名称：魔女缠线
- Skill slug：`mowna-thread`
- 版本：`0.6.0`
- 分类建议：投资教育 / 研究分析
- 关键词：缠中说禅、缠论、A股、历史复盘、量化验证、基金、债券、风险管理
- 一句话：以缠中说禅原典和可复核市场数据为基础，教学、复盘并生成中国A股/基金的研究报告与PDF。

## 简介

魔女缠线是一款面向中国市场学习与研究的 Skill，支持缠论课程、历史决策复盘、A股/基金/债券市场研究，以及个股/公募基金简明或全量PDF报告。报告流程优先核对交易所、监管、公司和基金管理人一手材料，要求标注行情时点、证据来源、缠论结构口径、基本面/产品质量、估值情景、反方风险和概率方法。内容用于教育与研究，不承诺收益；盘中行情是否实时取决于可用及获授权的数据源。

## 包含文件

- `SKILL.md`：入口、模式路由、报告格式和边界
- `references/`：来源地图、理论框架、自定计划与费曼课程、专业研究报告/PDF流程、同类Skill对标、复盘/回测协议、市场研究协议、证据等级、配置风险预算及示例
- `knowledge-base/source-ledger.csv`：种子来源台账（当前15条记录，不是全量书目）
- `knowledge-base/archive-catalog.csv`：13条人工种子记录
- `knowledge-base/archive-catalog-full.csv`：2026-10-19导出的1,139条公开博客目录元数据（标题/链接/日期/访问时点，不含文章正文；尚未逐篇研读或摘要）
- `knowledge-base/chan108-course-index.csv`：从标题及URL slug核对出的1–108课索引；当前为元数据索引，逐课摘要仍未完成
- `knowledge-base/coverage.md`：覆盖率和遗漏声明
- `scripts/`：报告校验/PDF渲染、CSV及HTTPS JSON行情入口、OHLCV/复权审计、候选缠论标注、学习进度记录和博客目录导出工具。行情连接器尚未绑定某个已授权供应商；自动标注仅合成数据验证
- `knowledge-base/reports/`：脱敏/公开来源研究样例和校验负例；样例PDF在 `output/pdf/`
- `TEST-CASES.md`：学习、报告及研究行为验收规格
- `TEST-RUN-0.5.0.md`：课程与REPORT-01至REPORT-05实际运行记录、部分通过限制与工具测试结果
- `TEST-RUN-0.6.0.md`：10项工具回归、全量目录计数及真实数据/课程验证边界
- `TEST-OUTPUTS.md` 与 `验收运行记录.md`：0.2.1 的8项已运行答复和判定；0.5.0课程/报告用例见专项记录
- `references/07-feynman-curriculum.md`：用户自定节奏、分层课程、费曼闭环、间隔复测与结业标准
- `references/08-research-report.md`：个股/基金报告工作流、数据源优先级、图表/概率约束、PDF标准
- `references/09-report-sources.md`：专业报告与A股/基金官方来源索引
- `references/10-skill-benchmark.md`：相近金融分析 Skill 对标、吸收项和后续路线
- `VERSION.md`：维护和发布门槛
- `REVIEW-评分与优化建议.md`：评审分数、相近 Skill 对标和后续路线
- PDF运行依赖：Python、ReportLab、pypdf、Poppler及可授权中文字体；详见报告工作流的可移植性说明
- `LICENSE.md`：仅对本项目原创说明与流程授权；不授权第三方原文

## 发布核验

当前公开产品名称可能与“SkillHub”同名；确认用户所指具体平台、登录态、命名空间及其上架流程后再发布。通用 SkillHub 格式通常要求 Skill 目录根部含 `SKILL.md`，但不同站点和自托管实例流程不同。不得把含第三方受版权保护全文的语料打包公开；本包仅含书目/链接、原创摘要和研究流程。当前8.7/10为内部流程复评，不是外部认证或投资绩效评级；没有行情API，样例中的行情截止时间、第三方来源和结构分析缺项均需保留。
