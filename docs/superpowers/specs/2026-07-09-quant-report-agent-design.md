# 量化研报分析 Agent + 集成网站 · 设计文档

> **日期**:2026-07-09
> **状态**:待用户评审
> **作者**:brainstorming 会话产出

---

## 1. 概述

### 1.1 背景与目标

用户是量化研究员,已搜集 11 家券商金工团队共 **213 篇**研报(存于 Obsidian vault 的 `Clippings/`,按机构分目录,均为 Markdown,9K–60K 字符/篇)。目标是构建一个 **agent(批处理分析流水线)+ 集成网站**,实现:

1. **读懂每篇报告**:提取核心内容、经济逻辑、因子/模型构造(达到**可复现逻辑**的级别)、超额收益来源、绩效、收益归因状态。
2. **分类与检索**:多维度分类(研究类型/数据频率/因子家族/资产类别/方法),网站可按任意维度筛选。
3. **批判性分析**:每篇给出不足、可复用要素、对自有研究的启发、以及"用相似逻辑/不同构造做得更好"的改进方向。
4. **跨报告视野**:因子·方法注册表、拥挤度全景图、研究空白与差异化机会--支撑"避开已有研究、比友商做得更好"。
5. **高质量呈现**:静态网站,可读性、美观、质量上乘,量化终端深色风格。

### 1.2 与现有知识库的关系

- 新项目作为 vault 的 **sibling** 独立存在(`D:\量化研报分析\`),**不**放进 vault,**不**同步摘要回 `wiki/`。
- 流水线**只读** vault 的 `Clippings/*.md` 与 `raw/pdfs/*.pdf`,不修改 vault 任何内容。

### 1.3 成功标准

- 213 篇报告全部产出结构化分析(精简 + 详述 + 可复现构造 + 批判性四段)。
- 网站可按多维度筛选/搜索,报告详情页可一键查看原文。
- 跨报告层产出因子·方法注册表、拥挤度全景图、≥10 条差异化机会。
- 新增/改动报告可增量重算,无需全量重跑。

---

## 2. 已确认的关键决策

| 维度 | 决策 |
|---|---|
| 运行架构 | 独立 Python 流水线 + Astro 静态站(不依赖 OpenClaw Gateway) |
| 输入与增长 | Markdown + PDF 都支持,增量更新 |
| 交互形态 | 批处理流水线 + 网站浏览(无后端、无交互问答) |
| 跨报告层 | v1 即包含完整跨报告综合层 |
| 技术路线 | 方案 A:Python 流水线 + Astro/Tailwind/React + **火山引擎 Ark**(模型默认 GLM-5.2,config 切换) |
| 项目位置 | sibling `D:\量化研报分析\`,不同步回 wiki |
| 视觉风格 | 量化终端(深色高密度),字体 Plus Jakarta Sans + JetBrains Mono(+ Noto Sans SC) |

---

## 3. 系统架构

四层流水线,前三层 Python,最后一层 Astro 静态站。每层只读上一层产出,可单独重跑。

```
┌───────────────────────────────────────────────────────────────────┐
│  ① Ingest 解析层                                                  │
│  Clippings/*.md + raw/pdfs/*.pdf -> 归一化文档(clean text+表格+元数据)│
│  content-hash manifest 驱动增量                                     │
└──────────────────────────┬────────────────────────────────────────┘
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│  ② Analyze 单篇分析层 (LLM)                                       │
│  每篇文档 -> 结构化分析 JSON + 渲染 MD                              │
│  分类标签 / 核心内容 / 经济逻辑 / 构造细节(可复现) / 超额收益逻辑     │
│  绩效 / 收益归因 / 精简版 / 详述版 / 批判性分析 / 评级 / 实体         │
└──────────────────────────┬────────────────────────────────────────┘
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│  ③ Synthesize 跨报告综合层 (LLM 第二遍)                            │
│  全部单篇分析 -> 因子·方法注册表 -> 全景图/拥挤度/研究空白/同主题对比   │
└──────────────────────────┬────────────────────────────────────────┘
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│  ④ Present 网站层 (Astro 静态站)                                  │
│  消费 data/ 下所有 JSON/MD -> 可筛选/搜索/对比的静态网站             │
└───────────────────────────────────────────────────────────────────┘
```

**端到端数据流**:输入(`Clippings/` + `raw/pdfs/`)→ 归一化文档 + manifest → 单篇分析 JSON/MD → 注册表 + 综合页 → Astro 构建 → `dist/` 静态站。

### 3.1 项目目录布局

```
D:\量化研报分析\
├── pipeline/                  # Python 流水线
│   ├── ingest/                # MD/PDF 解析、归一化、manifest
│   ├── analyze/               # 单篇 LLM 分析、schema、prompts
│   ├── synthesize/            # 跨报告:注册表/全景图/空白/对比
│   ├── llm/                   # provider 抽象(Claude/GLM/OpenClaw)
│   └── config.yaml            # vault 路径、模型、分类体系配置
├── data/                      # 产出(git 追踪、可 diff)
│   ├── analyses/              # 每篇:{slug}.json + {slug}.md
│   ├── registry/              # factor-method-registry.json
│   ├── landscape/             # 全景图/空白/对比页 JSON
│   └── manifest.json          # 增量哈希
├── site/                      # Astro 站点源码
│   ├── src/                   # pages/components/content collections
│   └── astro.config.mjs
├── dist/                      # 构建出的静态站(可部署)
└── docs/superpowers/specs/    # 本设计文档
```

`config.yaml` 中配置 vault 根路径(默认 `D:\知识库\obsidian`),流水线据此读取 `Clippings/` 与 `raw/pdfs/`。

---

## 4. 数据模型

### 4.1 单篇分析 schema(`data/analyses/{slug}.json`)

```json
{
  "schema_version": "1.0",
  "slug": "gf-alphaforge-2025",
  "source": {
    "title": "【广发金工】AlphaForge:基于梯度下降的因子挖掘",
    "institution": "广发",
    "authors": ["安宁宁", "陈原文", "王小康"],
    "published": "2025-04-30",
    "source_type": "wechat",            // wechat | pdf | official | article
    "original_url": "https://mp.weixin.qq.com/s/...",  // 网站"查看原文"按钮指向
    "local_path": "广发/【广发金工】AlphaForge....md",
    "ingested_at": "2026-07-09"
  },
  "classification": { /* 见 4.2,多维度标签 */ },

  "ratings": {
    "quality": 4,          // 1-5 报告整体质量
    "novelty": 4,          // 1-5 新颖性
    "reusability": 3       // 1-5 对自有研究的可复用性
  },

  "concise": {                          // 精简概括版(一屏可读)
    "one_liner": "用可导的生成器+预测器做梯度下降式公式化因子挖掘",
    "core_points": ["…", "…"],
    "key_result": "合成因子 IC 13.85%、多头年化超额 17.33%;中证1000指增 IR 2.27"
  },

  "detailed": {                          // 详述版(逻辑与构造过程,可复现级)
    "core_content": "…",                 // 核心内容(加厚)
    "economic_logic": "…",               // 经济逻辑(加厚)
    "construction": {                    // ★ 构造细节·可复现级(按报告类型自适应)
      "type": "model",                   // factor | model | strategy | config
      "data_inputs": [
        {"field":"开/收/高/低/量","frequency":"日频+逐笔","source":"Level-2","preprocessing":"…"}
      ],
      "backtest_setup": {
        "period":"2017–2024","benchmark":"沪深300/中证500/中证1000",
        "rebalance_freq":"日频","cost":"含交易成本","grouping":"10分位"
      },
      "combination": "LGBM + 等权二次合成",
      "parameters": [{"name":"潜在因子库","value":"100","meaning":"每年挖掘因子数"}],
      // ---- factor 类型专属 ----
      "factor_definition": "…",          // 公式/构造逻辑(逐步,达到可复现)
      "processing_pipeline": ["去极值","标准化","行业中性化","市值中性化"],
      // ---- model 类型专属 ----
      "model_architecture": "生成器=AutoEncoder(DCGAN+Masker);预测器=掩码->IC 映射",
      "inputs": ["基础特征经算子组合的因子表达式(掩码矩阵)"],
      "outputs": "预测器:因子 IC 预测(奖励信号);生成器:新因子表达式",
      "training": "端到端梯度下降;因子 IC 作可微奖励;生成器与预测器交替训练",
      // ---- strategy 类型专属 ----
      "strategy_logic": "…","allocation": "…"
    },
    "excess_return_logic": "…",          // 超额收益来源(加厚)
    "performance": {
      "metrics": [{"name":"合成IC均值","value":"13.85%"},{"name":"多头年化超额","value":"17.33%"},
                  {"name":"超额最大回撤","value":"-5.41%"},{"name":"中证1000指增IR","value":"2.27"}],
      "benchmark": "沪深300/中证500/中证1000",
      "backtest_period": "2017–2024",
      "turnover": null,                  // 有则填,无则 null
      "capacity": null,
      "ic_decay": null,
      "summary": "…"
    },
    "attribution": {                     // 收益归因:做了没(不强调,但明确标记)
      "done": false,
      "method": null,
      "summary": "未做收益归因",
      "gap": "缺行业/风格/因子归因"
    },
    "robustness":        {"subsample_stability":"…","style_bias":"…","turnover":null,"capacity":null,"summary":"…"},
    "data_dependency":   {"data_required":"Level-2 量价","reproducibility":"medium","summary":"…"},
    "prior_art":         [{"method":"遗传规划(GP)","relation":"被替代:无方向性"}, {"method":"AlphaGen","relation":"改进:超参敏感"}],
    "novelty_assessment":{"type":"新方法","summary":"可导的因子生成框架"}
  },

  "critical": {                          // 批判性分析(最高价值,用 Fable/Opus)
    "weaknesses":        ["未做收益归因","容量与换手未讨论","样本外IC衰减未展开"],
    "useful_elements":   ["可导掩码矩阵思路可迁移","掩码->IC映射作通用因子筛选器","二次合成提升IR"],
    "inspirations":      ["把可导奖励用到财务附注因子","加容量/换手约束作多目标","跨频组合增强"],
    "improvement_ideas": [               // 相似逻辑/不同构造 -> 做得更好
      {"idea":"容量感知的 AlphaForge","based_on":"掩码预测器加换手/容量惩罚","expected_gain":"实盘可交易"}
    ],
    "replication_plan":  "复现步骤建议…"
  },

  "entities": [                          // 带类型,供注册表/交叉链接
    {"name":"AlphaForge","type":"method"},
    {"name":"遗传规划","type":"method"},
    {"name":"DCGAN","type":"model"},
    {"name":"Level-2","type":"dataset"}
  ],
  "related_reports": [{"slug":"…","title":"…","relation":"同方法"}],  // 经实体/因子重叠算出
  "confidence": "high",
  "model_used": "GLM-5.2"
}
```

**要点**:
- `detailed.construction.type` 决定渲染哪些字段:因子类→`factor_definition`+`processing_pipeline`;模型类→`model_architecture`+`inputs`+`outputs`+`training`;策略类→`strategy_logic`+`allocation`。目标是**拿到逻辑即可复现**。
- `concise` 仅一句话+要点+关键结果;`detailed` 承载全部细节。网站切换显示。
- `attribution.done` 布尔显式标记"做了没",网站降为小字状态行(不强调)。
- `original_url` 来自报告 frontmatter 的 `source:` 字段,网站详情页与列表均放醒目「查看原文 ↗」按钮。
- 文件 **AI 起草、纯文本可编辑**:用户可直接改 JSON/MD,重跑不覆盖(除非原文内容变了)。

### 4.2 分类体系(多维度,可自定义)

每篇在每维多选,网站可按任意维度筛选/分组。体系写在 `config.yaml`,可随时增删:

| 维度 | 取值示例 |
|---|---|
| 研究类型 `research_type` | 基本面 / 技术面(量价) / 高频·微观结构 / 资产配置·风格轮动 / 行业轮动 / AI·机器学习 / 另类数据 |
| 数据频率 `data_frequency` | 财务(低频) / 日频 / 分钟 / 盘口 / 逐笔(Level-2) / 集合竞价 / 隔夜 |
| 因子家族 `factor_family` | 动量 / 反转 / 波动率 / 资金流(大小单·长短单) / 流动性 / 价值 / 质量 / 分析师 / 情绪 / 红利 |
| 资产类别 `asset_class` | A股 / 港股 / 指数增强 / 行业轮动 / 多资产 / 基金 |
| 方法 `method` | 统计线性 / 树模型 / 深度学习 / 强化学习 / 遗传规划·符号回归 / 知识图谱·RAG / 组合优化 |
| 自由标签 `custom_tags` | LLM 抽取 + 用户可编辑(如"因子挖掘""指增""多模态") |

### 4.3 跨报告注册表(`data/registry/factor-method-registry.json`)

第二遍 LLM 把所有单篇分析里的因子/方法抽成注册表:

```json
{
  "factors": [
    { "id":"size-order-flow","name":"大小单资金流因子","family":"资金流",
      "construction_summary":"按单笔金额划大/小单,净流入…",
      "data_frequency":"逐笔(Level-2)",
      "studied_by": [
        {"institution":"广发","report":"…","performance":"…"},
        {"institution":"开源","report":"…","performance":"…"},
        {"institution":"国信","report":"…","performance":"…"} ],
      "crowdedness":"high",            // 被多少家研究过 -> 拥挤度 high/medium/low
      "gaps":["…"] }
  ],
  "methods": [ /* 同结构 */ ],
  "landscape": {
    "by_factor_family": {"资金流":19,"动量":11,"反转":9,"量价复合":9,"AI/ML":9,"高频微观":9,"分析师":4,"资产配置":4,"红利":1,"财务附注":1},
    "by_research_type": { /* … */ },
    "matrix_family_x_institution": [ /* 热力图数据 */ ]
  },
  "gaps": [                            // 研究空白/差异化机会
    {"area":"财务附注因子","why_underexplored":"仅1篇","opportunity":"低拥挤蓝海","score":5,"related_reports":["…"]},
    {"area":"跨频因子组合","why_underexplored":"无人系统研究","opportunity":"信息增量最大","score":5,"related_reports":["…"]}
  ],
  "comparisons": [                     // 同主题对比
    {"topic":"大小单因子","reports":["…","…"],"comparison_summary":"…"}
  ]
}
```

`crowdedness` = 该方向被多少家研究;`gaps` = 研究空白与机会(带分数与可借鉴报告);`comparisons` = 同主题多家并排。三者合起来即"避开重复、做得更好"的决策依据。

---

## 5. Ingest 解析层

### 5.1 Markdown 解析
- 解析 frontmatter(YAML):`title`/`source`(→`original_url`)/`author`/`published`/`tags`。
- 提取正文 clean text,保留标题层级、表格、公式(文本形式)。
- 机构从所在目录名推断(`Clippings/广发/…` → institution=广发)。

### 5.2 PDF 解析(`raw/pdfs/*.pdf`)
- 文本层:**PyMuPDF(fitz)** 抽文本;**pdfplumber** 抽表格。
- 布局:启发式重建阅读顺序(分栏、页眉页脚剔除)。
- 图表:无法还原图像,提取图注(caption)与上下文文本,标注 `[图:X,已省略]`。
- 扫描件兜底:**PaddleOCR**(中文)做 OCR,再走文本流程。
- 元数据:从首页/页眉抽机构、标题、作者、日期。

### 5.3 归一化文档结构
无论 MD/PDF,统一产出:
```json
{ "slug":"…", "source_path":"…", "source_type":"wechat|pdf",
  "metadata":{institution,title,authors,published,original_url},
  "clean_text":"…", "tables":[…], "sections":[{heading,body}] }
```

### 5.4 增量 manifest(`data/manifest.json`)
```json
{ "files": { "广发/【广发金工】AlphaForge....md": {"hash":"sha256…","analyzed_at":"…","schema_version":"1.0"} } }
```
- 每次运行:计算每个输入文件的 content hash;**跳过** hash 未变且 schema_version 一致的;**只重算**新增/改动/ schema 升级的。
- 跨报告层:任一单篇变动则触发 synthesize 层全量重算(v1,见 §7)。

### 5.5 一键运行(增量更新)
新增/改动报告后,运行单条命令即可全自动更新:

```bash
python -m pipeline run          # 或 ./run.sh
```

该命令依次执行:① 增量扫描输入(MD+PDF),只解析新增/改动;② 只分析新增/改动的报告;③ 全量重算跨报告综合层;④ 重建静态站到 `dist/`。**未变动的报告跳过**(省时省 token)。也支持分步子命令(`ingest`/`analyze`/`synthesize`/`build`)单独跑某一层。

**指定单篇更新**(不依赖全量扫描,适合"加了一篇只想更新这一篇"):
```bash
python -m pipeline run --file "广发/【广发金工】xxx.md"   # 指定 MD 路径
python -m pipeline run --file "raw/pdfs/xxx.pdf"          # 指定 PDF
python -m pipeline run --slug gf-xxx                      # 按已入库 slug
```
只解析 + 分析该篇,再重算跨报告层 + 重建站点。

---

## 6. Analyze 单篇分析层

### 6.1 LLM 调用
- 走 **火山引擎 Ark**(`volcenginesdkarkruntime`),封装为 `ArkProvider`;**模型在 `config.yaml` 里切换**(默认 `GLM-5.2`,换其他模型只需改 model 字符串)。API key 走环境变量 `ARK_API_KEY`。
- 只有 **analyze 与 synthesize 两层调用 LLM API**;ingest(解析)与 present(建站)不调用。
- **两段式调用**(见 6.2):先结构化抽取(轻量、强制 JSON),再深度生成长文本(完整);成本由增量 manifest(未变动报告不重跑)与两段式调用控制。
- 结构化输出:优先用 Ark 的 JSON mode / tool calls 强制 schema;若不可用则 prompt 约束 + 解析 + 重试。

### 6.2 Prompt 策略
- **两段式**:第一段抽取结构化字段(强制 JSON schema,工具调用/structured output);第二段基于抽取结果 + 原文,生成详述/构造/批判性长文本。
- 构造细节 prompt 明确要求"达到可复现级别":因子类必须给公式/算子/处理流程/参数;模型类必须给架构/输入/输出/训练。
- 批判性 prompt 强制四段(不足/可复用/启发/改进方向),改进方向必须有"相似逻辑 + 不同构造"的具体 idea。

### 6.3 输出校验
- JSON schema 校验(pydantic);缺字段或类型错则重试(最多 2 次),仍失败则标记 `status: failed` 并记录,不阻塞其他报告。
- `confidence` 字段沿用 `[EXTRACTED]/[INFERRED]` 语义(高/中/低)。

### 6.4 渲染 MD
- 每个 JSON 同步生成一份可读 MD(供 Obsidian 式阅读与 diff),网站优先用 JSON。

---

## 7. Synthesize 跨报告综合层

1. **构建注册表**:遍历所有单篇 `entities` + `construction`,聚类出因子/方法条目(同名/近义合并),记录每条被哪些机构/报告研究过、绩效、数据频率。
2. **拥挤度**:按因子家族、方法、研究类型统计覆盖数;`crowdedness` = high(≥3 家)/medium/low。
3. **研究空白**:识别覆盖极少(≤1 篇)的家族/方法 + 方法论空白(如收益归因普遍缺失、容量分析缺失、跨频组合缺失);每条给 `score`(1-5)与可借鉴报告。
4. **同主题对比**:对同一因子/方法被多家研究的,生成对比页(构造差异、绩效对比、优劣)。
5. **全景图数据**:产出 `matrix_family_x_institution` 等矩阵供网站热力图。

> 跨报告层在单篇层完成后**整体重算**。单篇增量变动时,v1 采用**全量重算 synthesize 层**(213 篇规模下耗时可接受,且该层仅依赖已产出的单篇 JSON、不重复调用原文 LLM);按受影响条目做细粒度增量优化留作未来。

---

## 8. Present 网站层

### 8.1 信息架构(页面)

| 页面 | 内容 |
|---|---|
| Dashboard 首页 | KPI(报告数/机构/因子家族/研究空白)、因子家族拥挤度图、研究空白 Top、最新分析、机构分布 |
| 报告列表 | 全部报告;左侧 facets 多维筛选 + 全文搜索 + 排序(日期/质量/新颖性/可复用性) |
| 报告详情 | 精简⇄详述切换;「查看原文」按钮;分类标签;绩效指标卡;收益归因状态行;详述四段(含构造细节·可复现);批判性四卡;相关报告;实体 |
| 因子·方法注册表 | 全部因子/方法按家族分组;每条显示拥挤度 + 各机构做法链接 |
| 研究全景图 | 因子家族×机构热力图(可切换 方法×频率 / 家族×资产);拥挤/空白标记;差异化机会卡 |
| 同主题对比 | 多家同一主题并排对比 |
| 机构画像 | 每家机构研究偏好(主题/方法/频率分布) |
| 关于 | 方法论、schema 版本、如何编辑分析文件 |

导航:顶部 `首页 / 报告 / 因子注册表 / 全景图 / 对比 / 机构 / 关于` + 全局搜索(⌘K)。

### 8.2 视觉设计
- **风格**:量化终端(深色高密度)。底色 `#0B0E14`,面板 `#0E1219/#11161F`,边框 `#1E2733`。
- **配色**:强调青 `#22D3EE`、正绿 `#34D399`、拥挤琥珀 `#FBBF24`、不足红 `#F87171`、启发靛 `#818CF8`。
- **字体**:正文/UI/标题统一 **Plus Jakarta Sans**(中文 **Noto Sans SC**);数据/标签/指标用 **JetBrains Mono**。
- **批判性四卡**:彩色左边框(🔴不足/🟢可复用/🔵启发/🟡改进方向),改进方向用 idea 子卡。
- **构造细节**:架构流程图 + 字段卡(数据输入/输入/输出/参数)+ 规格行(架构/训练/合成/回测)。

### 8.3 构建
- **Astro** content collections 消费 `data/`;**Tailwind** 样式;少量 **React 岛屿**(筛选 UI、ECharts 热力图/柱状图)。
- 纯静态输出到 `dist/`,可本地 `astro dev` 预览或部署到 GitHub Pages 等。
- 无后端、无数据库;筛选/搜索为客户端(213 条规模足够)。

---

## 9. LLM 与 Provider 抽象

```python
# pipeline/llm/provider.py —— 封装火山引擎 Ark,模型在 config 切换
from volcenginesdkarkruntime import Ark
import os

class ArkProvider:
    def __init__(self, model: str):
        self.client = Ark(api_key=os.environ["ARK_API_KEY"])
        self.model = model                      # "GLM-5.2" / "DeepSeek-V4-Pro" / …
    def chat(self, messages, **kw):
        return self.client.chat.completions.create(model=self.model, messages=messages, **kw)
    def extract(self, doc, schema) -> dict: ...      # 结构化抽取(JSON mode / tool calls)
    def analyze(self, doc, extracted) -> dict: ...   # 详述+构造+批判
    def synthesize(self, all_analyses) -> dict: ...  # 跨报告综合
```
- 默认 `ArkProvider`,模型由 `config.yaml` 的 `model` 字段决定(默认 `GLM-5.2`);**换模型只改这一处字符串**(如 `DeepSeek-V4-Pro`)。
- 接口统一,后续可扩展其他 OpenAI 兼容 provider。

---

## 10. 质量保证与错误处理

- **Schema 校验**:pydantic 校验每份分析;不符则重试→标记 failed→记录到 `data/_errors.json`,不阻塞。
- **增量一致性**:hash + schema_version 双判;升级 schema 时可强制全量重算。
- **人工编辑不被覆盖**:若 JSON 中存在 `user_edited: true` 标记且原文未变,重跑时保留人工修改(或提示冲突)。
- **置信度**:`confidence` 字段 + 批判性段落默认 `[INFERRED]` 语义,提示用户复核。
- **PDF 解析降级**:OCR 失败的 PDF 标记 `partial: true`,在网站显示"解析不完整"提示。
- **成本控制**:Sonnet 做抽取、Fable/Opus 只用于深度段落;manifest 增量避免重复花费。

---

## 11. 构建里程碑

| 里程碑 | 内容 | 产出 |
|---|---|---|
| **M1 解析+单篇分析骨架** | MD 解析、归一化、provider 抽象(Claude)、单篇 schema(精简+详述+构造细节+批判)、manifest | 对 10 篇样本跑通端到端分析 |
| **M2 网站 MVP** | Astro + Tailwind + 量化终端视觉;报告列表(筛选)+ 报告详情(精简/详述/构造/批判/原文) | 可浏览的静态站 |
| **M3 跨报告层** | 因子·方法注册表、全景图热力图、研究空白/机会、同主题对比 | 全景图页 + 注册表页 |
| **M4 PDF + 增量** | PyMuPDF/pdfplumber/PaddleOCR 解析;manifest 增量全量跑 213 篇 | 全量数据 + 增量能力 |
| **M5 打磨** | 全文搜索、机构画像页、对比页、性能与可读性优化 | 上乘成品 |

每个里程碑独立可验证;M1–M2 即可交付可用网站,M3 起补齐跨报告价值。

---

## 12. 不在范围内 / 未来

- **交互式问答(RAG)**:v1 不做;未来可加向量库 + 后端问答。
- **同步摘要回 wiki**:不做(用户已确认)。
- **自动追踪新研报**:不做;用户手动放入 `Clippings/` 或 `raw/pdfs/`,流水线增量拾取。
- **图表/公式图像还原**:PDF 图表仅取图注,不还原图像。

---

## 13. 待实现阶段确认的细节

1. **同义因子合并**(已确认需要):跨报告注册表需聚类"大小单资金流""大小单资金流因子"等近义命名。做法:维护一份别名表(`config.yaml`)+ LLM 辅助识别近义条目,人工确认后合并。实现时定具体阈值与流程。
2. **机构名**:直接用 `Clippings/` 目录名(广发/国信/国泰海通/国联民生…),不做规范化映射。
3. **Ark 模型可用性**:确认 `ARK_API_KEY` 可用、`GLM-5.2` 模型字符串正确;换模型(如 `DeepSeek-V4-Pro`)只需改 `config.yaml` 的 `model` 字段(前提是该模型在 Ark 可用)。
