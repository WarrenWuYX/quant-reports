# M3 · 全景图 & 注册表 & 对比 设计文档

## 概述

在 M1（Pipeline）和 M2（Website MVP）基础上，新增四个功能：
1. 因子·方法注册表 — 跨报告实体聚合索引
2. 全景图热力图 — 研究覆盖可视化
3. 研究空白/机会 — 覆盖缺口 + 改进方向
4. 同主题对比页 — 两篇报告并排对比

## 架构

```
pipeline/registry/
  aggregator.py          # 实体聚合 + 覆盖矩阵计算

data/
  registry/entities.json  # 聚合实体索引
  landscape/coverage.json # 维度覆盖矩阵

site/src/pages/
  registry/index.astro    # 因子·方法注册表
  landscape/index.astro   # 全景图热力图 + 研究空白
  compare/[a]-[b].astro   # 同主题对比页
```

Python 预处理生成 JSON → Astro 构建时读取 → 纯静态站点。

## 数据模型

### entities.json

```json
{
  "factors": [
    {
      "name": "APM因子",
      "reports": [
        {"slug": "a834ae9c2e1e", "title": "APM因子模型的进阶版", "institution": "开源"}
      ],
      "tags": ["高频·微观结构", "技术面(量价)", "反转", "动量"],
      "report_count": 1
    }
  ],
  "methods": [
    {
      "name": "AlphaForge",
      "reports": [
        {"slug": "5cbd0055280b", "title": "AlphaForge：基于梯度下降的因子挖掘", "institution": "广发"}
      ],
      "tags": ["AI·机器学习", "技术面(量价)"],
      "report_count": 1
    }
  ]
}
```

### coverage.json

```json
{
  "dimensions": [
    {
      "id": "factor_family_x_research_type",
      "label": "因子家族 × 研究类型",
      "x_axis": "research_type",
      "y_axis": "factor_family",
      "matrix": [
        {"x": "技术面(量价)", "y": "动量", "count": 1, "slugs": ["b0af7c5f7305"]},
        {"x": "技术面(量价)", "y": "反转", "count": 2, "slugs": ["a834ae9c2e1e", "b0af7c5f7305"]}
      ]
    },
    {
      "id": "asset_class_x_method",
      "label": "资产类别 × 方法",
      "x_axis": "method",
      "y_axis": "asset_class",
      "matrix": [...]
    }
  ],
  "gaps": [
    {"dimension": "factor_family_x_research_type", "x": "基本面", "y": "动量", "count": 0}
  ]
}
```

## 页面设计

### 1. 注册表 `/registry`

- 顶部切换：因子 / 方法 / 全部
- 搜索框 + 标签筛选（factor_family、method 分类）
- 实体卡片列表：
  - 名称（大字）、类型标签（factor/method）
  - 关联报告数 badge
  - 关联分类标签
  - 点击展开 → 列出所有引用该实体的报告链接
- 与报告列表页类似的 facet 侧边栏

### 2. 全景图 `/landscape`

- 顶部：维度切换 tabs（`因子家族×研究类型` | `资产类别×方法` | `因子家族×资产类别`）
- Chart.js 热力图（React 岛屿）：
  - Y 轴 = 维度1，X 轴 = 维度2
  - 颜色深浅 = 覆盖报告数
  - 空白格 = 灰色（研究空白）
  - tooltip 显示具体报告名
- 热力图下方：
  - "研究空白" 列表：列出 count=0 的组合
  - "改进机会" 卡片：汇总 critical.improvement_ideas

### 3. 对比页 `/compare/[a]-[b]`

- 顶部：标题并排显示
- 对比表格：
  - 分类标签（行 = 维度，列 = 报告A / 报告B）
  - 评分对比（Q/N/R 数字）
  - 实体对比（因子列表、方法列表）
  - 构造细节（type、data_inputs、parameters）
  - 绩效指标（metrics 表格）
  - 批判性四卡（不足/可复用/启发/改进，左右并排）
- 底部：相似度分数 + 其他可对比的报告推荐

### 4. 导航更新

BaseLayout 导航栏新增：
- 注册表 (`/registry`)
- 全景图 (`/landscape`)

## 相似度计算

两篇报告的相似度基于 classification 字段的 Jaccard 相似度：

```
similarity = |A ∩ B| / |A ∪ B|
```

其中 A、B 为两个报告所有 classification 标签的并集（research_type + factor_family + method + asset_class + data_frequency）。

## 实现依赖

1. `pipeline/registry/aggregator.py` — 聚合脚本
2. `pipeline/cli.py` — 新增 `registry` 子命令
3. `pipeline build` — 更新为包含 registry 步骤
4. Astro 页面 — 3 个新页面 + 导航更新
5. Chart.js React 组件 — 热力图岛屿

## 非目标

- 全文搜索（M5）
- 机构画像页（M5）
- 热力图动画 / 高级交互
- 多于 2 篇的对比