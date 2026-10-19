# 本地报告工具

## 行情与课程工具（0.6.0）

- `market_data.py`: 用户授权CSV或自定义HTTPS JSON GET/Bearer接口；审计OHLCV、复权因子比例与来源声明。配置样例为 `../providers.example.json`。
- `chan_annotate.py`: 对单一标的原始OHLCV生成有确认时点的候选分型/笔/三笔重叠标注。
- `learning_tracker.py`: 本地JSONL匿名学习记录与复习方向，不上传/同步。
- `llm_analysis.py`: 用户主动运行的可选HTTPS OpenAI-compatible接口；只接收标记通过的证据JSON。
- `archive_catalog.py`: 构建归档目录元数据，不保存文章正文；支持索引快照和既有CSV归一化。
- `tests/test_market_tools.py`: 市场数据入口、复权闸门、候选标注、课程记录与归档解析的合成回归检查。

这些工具并不自带行情授权、行情密钥或模型API，也未在真实行情/真实学习者数据上验证。

## 组件

- `validate_report_data.py`: 校验结构、来源、指标、时点、单位/期间冲突、数字断言、图表来源、PDF文字和来源链接。
- `render_research_pdf.py`: 使用 ReportLab 从已核验 JSON 渲染中文 PDF，含简单折线图。
- JSON样例与冲突/数字错误夹具在 `../knowledge-base/reports/`。

## 运行

从 Skill 根目录运行：

```powershell
python scripts/validate_report_data.py knowledge-base/reports/spdb_600000_20261016.json
python scripts/render_research_pdf.py knowledge-base/reports/spdb_600000_20261016.json output/pdf/浦发银行_600000_研究样例_20261016.pdf
python scripts/validate_report_data.py knowledge-base/reports/spdb_600000_20261016.json
```

安装 `reportlab`、`pypdf`；要逐页渲染视觉检查还需 Poppler (`pdfinfo`、`pdftoppm`)。Windows样例字体路径为 `C:\Windows\Fonts\msyh.ttc`。其他环境应选择可合法分发/使用的中文字体，并在渲染器中配置。出错时停止交付，不把未校验或未视觉检查的PDF标为通过。

## 能力限制

本地报告工具自身不取行情、不校验网页内容真伪、不验证数据许可、不自动识别完整缠论结构、不输出估值或校准概率。新增行情导入与候选标注脚本有独立校验规则，但真实市场数据和实际供应商接口尚未验收。输入 JSON 的事实和解释仍需人工回到来源复核。
