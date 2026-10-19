# 行情数据接入、校验与候选标注

本参考说明在用户本机使用 CSV 或已获授权的供应商接口，建立可复核数据证据包。它不附带行情账号、API Key、供应商许可或实时行情服务。

## 1. 接入入口

### CSV

准备 UTF-8/UTF-8 BOM CSV，至少包括：

`symbol,date,open,high,low,close,volume`

可以增加 `amount,adj_open,adj_high,adj_low,adj_close,adj_factor`。日期用 `YYYY-MM-DD`。若要检验前复权或后复权，应提供原始OHLCV和同源、同时间快照的完整复权OHLC及因子。

```powershell
python scripts/market_data.py --csv market-data/600000.csv --source "用户授权供应商名称" --authorized --adjustment raw --out market-data/600000-audit.json
```

`--authorized` 是用户授权/许可声明，不是工具对许可证的独立法律核实。未经许可、来源不明的数据不得作为获授权数据使用。

### HTTPS JSON 接口

复制 `providers.example.json` 到本地 `providers.json`，替换 HTTPS endpoint、供应商字段映射及行数组路径。将凭据保存在环境变量，不将密钥写进配置、命令记录或仓库。

```powershell
$env:MARKET_DATA_API_KEY = "本机环境变量中已配置的密钥"
python scripts/market_data.py --provider-config providers.json --authorized --adjustment raw --out market-data/audit.json
```

入口当前只支持单次 HTTPS GET、Bearer token 和 JSON 对象行；如供应商要求 POST 签名、分页、验证码、SDK或专有二进制格式，须实现专用适配器并按该供应商文档验证。不要绕过其权限、限频或许可要求。遇到限流/字段不全要停止或降级，不将搜索引擎摘要充当价格数据。

## 2. 审计闸门

`scripts/market_data.py` 检查字段、数值有限性、正价格、非负成交量、同一标的日期唯一/递增、OHLC关系、复权OHLC完整性、调整模式对应字段、因子比例与调整收盘价比例一致性，并输出机器可读审计 JSON。

复权因子的绝对基准可能因供应商快照不同而不同。工具仅比较因子归一化后的逐日比例与 `adj_close/raw_close` 归一化比例；这是一项内部一致性检查，不证明供应商算法正确，也不证明复权字段代表前复权还是后复权。需在旁边保存供应商定义、基准日、分红送转更新方式及抓取时间。

日期不连续不自动等于缺行情：交易日历、停牌、上市/退市和供应商缺失需用交易所日历、证券状态和第二个来源另核。长期回测必须保留退市样本、公司行动、成交额/停牌和成本字段。审计通过也不代表数据已和交易所逐笔/官方日线独立比对。

最低运行：

```powershell
python scripts/market_data.py --csv path/to/ohlcv.csv --source provider --authorized --adjustment backward --out path/to/audit.json
```

只有 `passed=true` 且所有必要来源、授权、时间和复权信息符合当前分析任务，才可进入自动标注。审计失败应修复/隔离数据，而不是忽略错误。

## 3. 自动缠论候选标注

```powershell
python scripts/chan_annotate.py --csv path/to/ohlcv.csv --source provider --authorized --minimum-stroke-bars 4 --out path/to/chan-candidates.json
```

当前实现只是一套明确写出的示范口径：K线包含关系合并、三根合并K线严格顶/底分型、同类极值替换、交替分型、最小笔跨度、连续三笔区间重叠候选。分型只有在右侧K线出现后确认，笔只有在端点分型确认后进入报告。不是所有缠论版本的权威算法；线段、走势类型、中枢延伸/扩张、多义性与区间套尚未实现，任何候选需要图表复核。

交付至少保存：原始数据哈希/来源/日期、复权方式、算法版本与参数、时间周期、分型 pivot 与 confirmed_at、笔端点和 confirmed_at、不同合法参数口径的分歧、人工审阅人/日期/判定。不能把端点 pivot 日误写成当时即可知道的信号日。未经历史点时回测和样本外验证，不报告“正确率/胜率”或据此给确定交易建议。

## 4. 可选大模型分析接口

`scripts/llm_analysis.py` 接受 OpenAI-compatible HTTPS chat/completions 接口和模型名。证据包须有 `validation_passed: true`，用户主动运行命令前应确认所选供应商的数据保留、训练、地域、费用和隐私条款。仅发送分析所需的脱敏研究材料；不得上传账号、持仓明细、个人身份信息或私密学习记录。模型输出需逐项回到来源和审计结果核查，不能因为调用成功就称为事实、概率校准或投资建议。

接口示例：

```powershell
$env:LLM_API_BASE_URL = "https://your-authorized-endpoint/v1/chat/completions"
$env:LLM_MODEL = "your-model-id"
$env:LLM_API_KEY = "在本机安全配置"
python scripts/llm_analysis.py --evidence market-data/validated-evidence.json --out output/user-reports/draft.md
```

本工具没有捆绑模型 API，也不在本次版本中验证任何特定供应商。

## 5. 目前覆盖限制

- 没有用户已连通的行情源、真实历史OHLCV/复权样本、交易所级对账或行情授权证明。
- 没有自动分页/限频调度、交易日历对账、分钟线、债券行情或基金净值专用适配器。
- 候选标注只由合成数据回归检查；没有缠论专家双标或真实历史盲测。
- 连接器是研究数据入口，不构成交易终端、投资咨询牌照或代客交易服务。

## 6. 可选来源参考

若用户持有 Tushare Pro 账户，可将其官方 API 导出的数据整理为上述标准CSV。官方文档说明 A 股 `daily` 接口提供未复权日线（OHLC、成交量/额），`adj_factor` 是单独接口且有积分门槛；其 HTTP 接口使用 POST JSON，并返回 `fields` 与二维 `items`。本版 HTTPS JSON 连接器目前只支持 GET、Bearer 和对象数组，因此不能直接称为 Tushare 适配器；应使用用户本机SDK导出CSV或编写专用适配并测试。每次使用前还须确认本人账户接口权限、数据许可和对外展示/再分发条件。

- [Tushare A股日线接口说明](https://tushare.pro/document/1?doc_id=27)
- [Tushare 复权因子接口说明](https://tushare.pro/document/2?doc_id=28)
- [Tushare HTTP API格式](https://tushare.pro/document/2?doc_id=40)
