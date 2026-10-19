# 相近金融研究 Skill 对标与吸收记录

检索日期：2026-10-19。检索范围：公开 GitHub/Skill 仓库、Skill 目录和 CFA Institute 官方材料。开源 Skill 的存在、下载量或作者自述不等于专业有效性；将其作为工作流样例，优先验证可审计的过程设计。以下只吸收原创方法结构，不复制受版权保护的报告正文。

## 对标与取舍

| 项目 | 可借鉴做法 | 纳入本 Skill 的修改 | 不照搬的部分 |
|---|---|---|---|
| [evilhill/equity-research-skill](https://github.com/evilhill/equity-research-skill) | 证据/报告数据结构化；计算模型与报告渲染分开；报告校验器；保留输入、输出便于复现；审计模式 | 增加逐指标证据包、阶段依赖、摘要/图表/估值数值一致性闸门，并把真实标的 PDF 样例与验证器列为 P0 | 该仓库声明研究还需工具/用户文件，不是行情馈送器；其估值模块和脚本输出不能未经中国市场适配直接用 |
| [GrantDeng/trading-analysis-skill](https://github.com/GrantDeng/trading-analysis-skill) | 统一证据准备，记录时间、来源、单位；清楚分开研究、交易、风险和组合层；显式冲突处理和分阶段产物 | 采用 fresh-data block、单位/期间标准化、冲突摘要和反方/风险质询；允许薄弱证据时降级结论或停止 | 不强制10轮辩论、多个Agent或 BUY/SELL/HOLD评级；角色质询是同一分析者的自检，除非系统真运行独立评审，不能宣称独立 |
| [himself65/finance-skills](https://github.com/himself65/finance-skills) | 任务拆分成独立技能，覆盖估值、流动性、ETF和策略验证；数据工具和分析提示分离 | 主入口渐进披露，各任务引用专用参考；报告里的基础数据与判断分层 | yfinance 等美国市场接口不自动适用于A股，第三方聚合字段必须回到交易所/发行人披露 |
| [yennanliu/InvestSkill](https://github.com/yennanliu/InvestSkill) | 学习与研究框架模块化；可在不同Agent中复用 | 保持当前纯Markdown兼容，同时在数据能力存在时逐步加入结构化数据和可复现渲染 | “institutional-quality”等产品自述不作为质量证据；评分模型和买入信号需审计 |
| [wshobson/agents — Backtesting Frameworks](https://github.com/wshobson/agents/tree/main/plugins/quantitative-trading/skills/backtesting-frameworks) | 点时数据、前视/幸存者偏差、成本、walk-forward、样本外和多策略试验 | 保留策略试验日志、交易成本、样本外和稳健性门槛；结果少时降低结论强度 | 不把Sharpe或回测收益单独视为可交易边际；A股要补涨跌停、停牌、ST、退市、T+1等制度 |
| [LLMQuant initiating-coverage workflow](https://github.com/LLMQuant/docs/blob/main/en/equity-research/skills/initiating-coverage.mdx) | 公司研究/模型/估值/图表/报告间的先修关系；估值数据与报告数字交叉对账；行业适配估值 | 吸收阶段门、模型与报告数字审计、同一已核证据驱动所有图表和表格 | 其美国公司模型、固定长篇页数/图表数量不适用于所有中国公司；不因图表多或页数长宣称专业 |
| [TradingAgents-Skill](https://github.com/ruoyouz/TradingAgents-skill) | 多角度事实收集、牛熊分析、新闻/基本面/技术面分工 | 用模块化反方质询测试论点并记录证据，而非单一路径先入为主 | 不依赖付费API、社交媒体情绪或带有强操作性的固定指令；不要把多角色模拟包装为真实多人共识 |

## 来自专业报告标准的共同要求

[CFA Institute Equity Research Report Essentials](https://www.cfainstitute.org/sites/default/files/-/media/documents/support/research-challenge/challenge/rc-equity-research-report-essentials.pdf)、[估值课程](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/equity-valuation-applications-and-processes)、[Standard V(A)](https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-v-a) 和 [Standard V(B)](https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-v-b)共同支持以下原则：

1. 研究结论要基于充分证据，能由读者沿来源和假设质疑。
2. 明确区分事实、估算和意见；说明方法、关键限制和重要风险。
3. 对公司盈利质量阅读附注；对预测解释驱动因子，不线性外推历史增速。
4. 估值方法需适合业务类型；多种估值用于相互校验，不能机械平均。
5. 讨论可能推翻论点的情景，并对模型输入做敏感性/压力测试。
6. 报告长度、评级标签和目标价不是质量替代指标。公开获奖报告是写作范例，不是专业机构报告或投资业绩保证。

## 本轮已经纳入的改动

- SKILL入口统一成“课程、答疑、复盘、研究/报告”四类请求，不再称“四模式”后又标“三模式”。
- 报告采用阶段式工作流，先建数据证据包，统一单位/时期和来源时间，再做公司/基金/结构分析、估值、反方质询、数字对账。
- 加入银行/保险/周期行业的估值方法适配闸门；债券报告提高信用、条款、偿债现金流和压力流动性权重。
- 概率台账建议使用事件定义、预测时点、时域、结果规则和校准样本；小样本不做精确校准宣称。
- 清楚标出当前仍是研究指导 Skill：没有自动行情馈送、确定性数据抓取器、估值模型实现或PDF渲染验证脚本；只有真实接入后才能宣称这些能力已运行。

## 后续优先级

1. **P0**：增加结构化 report-data.json 和证据源清单；同一数据对象供估值、图表和报告使用。
2. **P0**：制作一份有真实来源和明确数据截点的A股全量报告 PDF，逐页检查；测试估值与摘要数字对账。
3. **P1**：开发纯本地报告渲染器/校验器；校验缺失来源、无时点数字、链接、PDF页数/提取文字和图表说明，不联网发送用户材料。
4. **P1**：获准的数据提供方/监管公开数据适配；区分获取授权、延迟级别、历史覆盖和字段口径。
5. **P1**：做单一股票的概率预测台账试运行，达到预先设定样本量前只给定性可信度。
6. **P2**：独立评审完整报告，并用真实学习者记录验证费曼课程的前测/后测和延迟回忆。

