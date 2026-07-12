# M3 · 全景图 & 注册表 & 对比 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增因子·方法注册表、全景图热力图、研究空白、同主题对比页四个功能，基于 Python 预处理 + Astro 静态渲染。

**Architecture:** Python `pipeline/registry/aggregator.py` 聚合分析 JSON 生成 `entities.json` 和 `coverage.json`；Astro 页面读取这些 JSON 渲染注册表、热力图（Chart.js React 岛屿）、对比页。

**Tech Stack:** Python 3.13 (pydantic v2, stdlib json/pathlib), Astro 5, Tailwind CSS 3, React 19, Chart.js 4 + react-chartjs-2 + chartjs-chart-matrix

## Global Constraints

- 保持与现有 CLI 模式一致：`python -m pipeline <subcommand>`
- 保持与现有 Astro 页面一致的视觉风格（深色量化终端主题）
- 所有数据预处理在 Python 侧完成，Astro 只做渲染
- 导航栏更新为 BaseLayout.astro 的统一修改
- `pipeline build` 命令需包含 registry 步骤
- 26 个现有测试必须继续通过

---

## File Structure

```
pipeline/registry/
  __init__.py              # 空文件，标记为 package
  aggregator.py            # build_entities() + build_coverage() + save_all()

data/
  registry/entities.json   # 聚合实体索引（构建时生成）
  landscape/coverage.json  # 维度覆盖矩阵（构建时生成）

site/src/
  data/                    # 构建时从 data/ 复制而来
    entities.json
    coverage.json
  components/
    HeatmapChart.tsx        # Chart.js 热力图 React 岛屿
  pages/
    registry/index.astro    # 因子·方法注册表页
    landscape/index.astro   # 全景图热力图 + 研究空白页
    compare/[a]-[b].astro   # 同主题对比页

tests/
  test_registry.py          # aggregator 单元测试
```

修改的文件：
- `pipeline/cli.py` — 新增 `registry` 子命令，更新 `build`
- `pipeline/io_paths.py` — 新增 registry/landscape 路径
- `site/src/layouts/BaseLayout.astro` — 导航栏新增链接
- `site/package.json` — 新增 chart.js + react-chartjs-2 依赖

---

### Task 1: Python Aggregator — 实体聚合 + 覆盖矩阵

**Files:**
- Create: `pipeline/registry/__init__.py`
- Create: `pipeline/registry/aggregator.py`
- Create: `tests/test_registry.py`
- Modify: `pipeline/io_paths.py` (新增路径)

**Interfaces:**
- Consumes: `io_paths.paths.analyses` (Path, 已有), `io_paths.paths.root` (Path, 已有)
- Produces:
  - `build_entities(analyses_dir: Path) -> dict` — 返回 `{"factors": [...], "methods": [...]}`
  - `build_coverage(analyses_dir: Path) -> dict` — 返回 `{"dimensions": [...], "gaps": [...]}`
  - `save_all(analyses_dir: Path, registry_dir: Path, landscape_dir: Path) -> None` — 调用上面两个并写 JSON

- [ ] **Step 1: 新增 io_paths 路径**

在 `pipeline/io_paths.py` 末尾添加：

```python
REGISTRY = DATA / "registry" / "entities.json"
LANDSCAPE = DATA / "landscape" / "coverage.json"
```

并在 `_Paths.__init__` 中添加：

```python
self.registry = REGISTRY
self.landscape = LANDSCAPE
```

- [ ] **Step 2: 编写 aggregator 测试**

创建 `tests/test_registry.py`：

```python
import json
from pathlib import Path
from pipeline.registry.aggregator import build_entities, build_coverage


def _make_analyses_dir(tmp_path):
    d = tmp_path / "analyses"
    d.mkdir()
    a = {
        "schema_version": "1.0", "slug": "abc", "status": "ok",
        "source": {"title": "动量因子研究", "institution": "国信", "authors": [], "published": None, "source_type": "wechat", "original_url": None, "local_path": "", "ingested_at": "2026-01-01"},
        "classification": {"research_type": ["技术面(量价)"], "factor_family": ["动量", "反转"], "asset_class": ["A股"], "method": ["统计回归"], "data_frequency": ["日频"]},
        "ratings": {"quality": 4, "novelty": 4, "reusability": 4},
        "concise": {"one_liner": "x", "key_result": "y"},
        "detailed": {"core_content": "c", "economic_logic": "e", "construction": {"type": "factor"}, "excess_return_logic": "ex", "performance": {"metrics": []}, "attribution": {"done": False, "summary": "未做"}, "novelty_assessment": {"type": "改进", "summary": "s"}},
        "critical": {"weaknesses": ["w1"], "improvement_ideas": [{"idea": "改进1", "based_on": "x", "expected_gain": "y"}]},
        "entities": [{"name": "动量因子", "type": "factor"}, {"name": "统计回归", "type": "method"}],
        "model_used": "GLM-5.2", "confidence": "high",
    }
    (d / "abc.json").write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
    return d


def test_build_entities(tmp_path):
    d = _make_analyses_dir(tmp_path)
    result = build_entities(d)
    assert len(result["factors"]) == 1
    assert result["factors"][0]["name"] == "动量因子"
    assert result["factors"][0]["report_count"] == 1
    assert len(result["factors"][0]["reports"]) == 1
    assert result["factors"][0]["reports"][0]["slug"] == "abc"
    assert len(result["methods"]) == 1
    assert result["methods"][0]["name"] == "统计回归"


def test_build_coverage(tmp_path):
    d = _make_analyses_dir(tmp_path)
    result = build_coverage(d)
    dims = {dim["id"]: dim for dim in result["dimensions"]}
    assert "factor_family_x_research_type" in dims
    assert "asset_class_x_method" in dims
    assert "factor_family_x_asset_class" in dims
    # 检查第一个维度的矩阵
    m = dims["factor_family_x_research_type"]["matrix"]
    assert any(cell["x"] == "技术面(量价)" and cell["y"] == "动量" and cell["count"] == 1 for cell in m)
    # gaps: count=0 的条目
    assert any(g["count"] == 0 for g in result["gaps"])


def test_entities_skip_non_ok(tmp_path):
    d = _make_analyses_dir(tmp_path)
    # 添加一个 status 不为 ok 的
    bad = json.loads((d / "abc.json").read_text("utf-8"))
    bad["status"] = "failed"
    bad["slug"] = "bad"
    (d / "bad.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    result = build_entities(d)
    assert len(result["factors"]) == 1  # 只有 abc 的
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd /d/量化研报分析 && python -m pytest tests/test_registry.py -v
```
期望：FAIL (module not found)

- [ ] **Step 4: 创建 package 文件**

创建 `pipeline/registry/__init__.py`（空文件）。

- [ ] **Step 5: 实现 aggregator**

创建 `pipeline/registry/aggregator.py`：

```python
import json
from collections import defaultdict
from pathlib import Path


def _load_analyses(analyses_dir: Path) -> list[dict]:
    """Load all OK analysis JSONs from analyses_dir."""
    results = []
    for f in sorted(analyses_dir.glob("*.json")):
        d = json.loads(f.read_text("utf-8"))
        if d.get("status") == "ok":
            results.append(d)
    return results


def build_entities(analyses_dir: Path) -> dict:
    """Aggregate all factor and method entities across reports."""
    analyses = _load_analyses(analyses_dir)
    factor_map: dict[str, list[dict]] = defaultdict(list)
    method_map: dict[str, list[dict]] = defaultdict(list)

    for a in analyses:
        slug = a["slug"]
        title = a["source"]["title"]
        inst = a["source"]["institution"]
        tags = (
            a["classification"].get("research_type", [])
            + a["classification"].get("factor_family", [])
            + a["classification"].get("method", [])
        )
        for e in a.get("entities", []):
            ref = {"slug": slug, "title": title, "institution": inst}
            if e["type"] == "factor":
                factor_map[e["name"]].append(ref)
            elif e["type"] == "method":
                method_map[e["name"]].append(ref)

    factors = sorted(
        [{"name": k, "reports": v, "tags": _collect_tags(k, v, analyses), "report_count": len(v)}
         for k, v in factor_map.items()],
        key=lambda x: (-x["report_count"], x["name"])
    )
    methods = sorted(
        [{"name": k, "reports": v, "tags": _collect_tags(k, v, analyses), "report_count": len(v)}
         for k, v in method_map.items()],
        key=lambda x: (-x["report_count"], x["name"])
    )
    return {"factors": factors, "methods": methods}


def _collect_tags(name: str, refs: list[dict], analyses: list[dict]) -> list[str]:
    """Collect classification tags from all source reports of this entity."""
    slugs = {r["slug"] for r in refs}
    tags = set()
    for a in analyses:
        if a["slug"] in slugs:
            for key in ("research_type", "factor_family", "method", "asset_class"):
                for t in a["classification"].get(key, []):
                    tags.add(t)
    return sorted(tags)


def build_coverage(analyses_dir: Path) -> dict:
    """Build coverage matrices for landscape heatmap."""
    analyses = _load_analyses(analyses_dir)

    dimensions = [
        {"id": "factor_family_x_research_type", "label": "因子家族 × 研究类型",
         "x_axis": "research_type", "y_axis": "factor_family"},
        {"id": "asset_class_x_method", "label": "资产类别 × 方法",
         "x_axis": "method", "y_axis": "asset_class"},
        {"id": "factor_family_x_asset_class", "label": "因子家族 × 资产类别",
         "x_axis": "asset_class", "y_axis": "factor_family"},
    ]

    all_x_values: dict[str, set[str]] = {}
    all_y_values: dict[str, set[str]] = {}
    for dim in dimensions:
        xk, yk = dim["x_axis"], dim["y_axis"]
        all_x_values[xk] = set()
        all_y_values[yk] = set()
        for a in analyses:
            for v in a["classification"].get(xk, []):
                all_x_values[xk].add(v)
            for v in a["classification"].get(yk, []):
                all_y_values[yk].add(v)

    result_dims = []
    all_gaps = []

    for dim in dimensions:
        xk, yk = dim["x_axis"], dim["y_axis"]
        x_vals = sorted(all_x_values[xk])
        y_vals = sorted(all_y_values[yk])
        matrix = []
        for y in y_vals:
            for x in x_vals:
                slugs = []
                for a in analyses:
                    cls = a["classification"]
                    x_has = x in cls.get(xk, [])
                    y_has = y in cls.get(yk, [])
                    if x_has and y_has:
                        slugs.append(a["slug"])
                entry = {"x": x, "y": y, "count": len(slugs), "slugs": slugs}
                matrix.append(entry)
                if len(slugs) == 0:
                    all_gaps.append({"dimension": dim["id"], "x": x, "y": y, "count": 0})
        result_dims.append({"id": dim["id"], "label": dim["label"],
                           "x_axis": xk, "y_axis": yk,
                           "x_labels": x_vals, "y_labels": y_vals,
                           "matrix": matrix})

    return {"dimensions": result_dims, "gaps": all_gaps}


def save_all(analyses_dir: Path, registry_path: Path, landscape_path: Path) -> None:
    """Generate and save entities.json and coverage.json."""
    entities = build_entities(analyses_dir)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(entities, ensure_ascii=False, indent=2), encoding="utf-8")

    coverage = build_coverage(analyses_dir)
    landscape_path.parent.mkdir(parents=True, exist_ok=True)
    landscape_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd /d/量化研报分析 && python -m pytest tests/test_registry.py -v
```
期望：3 passed

- [ ] **Step 7: 运行全部测试确认无回归**

```bash
cd /d/量化研报分析 && python -m pytest tests/ -v
```
期望：29 passed (26 existing + 3 new)

- [ ] **Step 8: Commit**

```bash
git add pipeline/registry/ pipeline/io_paths.py tests/test_registry.py
git commit -m "feat: add registry aggregator — entities + coverage JSON generation

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: CLI registry 子命令 + build 更新

**Files:**
- Modify: `pipeline/cli.py`

**Interfaces:**
- Consumes: `io_paths.paths.analyses`, `io_paths.paths.registry`, `io_paths.paths.landscape` (from Task 1)
- Consumes: `pipeline.registry.aggregator.save_all` (from Task 1)
- Produces: `python -m pipeline registry` 命令，生成 entities.json 和 coverage.json；`python -m pipeline build` 包含 registry 步骤

- [ ] **Step 1: 修改 cli.py**

在 `pipeline/cli.py` 顶部新增 import：

```python
from .registry.aggregator import save_all
```

在 `main()` 函数中，`build` subparser 之后新增 `registry` subparser：

```python
# registry
reg = sub.add_parser("registry", help="Generate registry entities and landscape coverage JSON")
```

在 `if args.cmd == "build":` 之前新增：

```python
if args.cmd == "registry":
    save_all(io_paths.paths.analyses, io_paths.paths.registry, io_paths.paths.landscape)
    print(f"Registry saved → {io_paths.paths.registry}")
    print(f"Landscape saved → {io_paths.paths.landscape}")
    return 0
```

更新 `_build_site()` 函数，在复制 JSON 和 npm build 之间插入 registry 步骤：

```python
def _build_site() -> int:
    """Copy analysis JSONs into Astro content dir, generate registry, and run astro build."""
    site_root = io_paths.paths.root / "site"
    content_dir = site_root / "src" / "content" / "analyses"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Copy all JSONs from data/analyses to site content directory
    copied = 0
    for json_path in sorted(io_paths.paths.analyses.glob("*.json")):
        dst = content_dir / json_path.name
        shutil.copy2(json_path, dst)
        copied += 1
    print(f"Copied {copied} analysis JSON(s) to {content_dir}")

    # Step 2: Generate registry + landscape JSONs
    from .registry.aggregator import save_all
    save_all(io_paths.paths.analyses, io_paths.paths.registry, io_paths.paths.landscape)
    print(f"Registry saved → {io_paths.paths.registry}")
    print(f"Landscape saved → {io_paths.paths.landscape}")

    # Step 3: Copy registry/landscape JSONs into site src/data dir
    data_dir = site_root / "src" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(io_paths.paths.registry, data_dir / "entities.json")
    shutil.copy2(io_paths.paths.landscape, data_dir / "coverage.json")

    # Step 4: Run npm run build
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    result = subprocess.run([npm, "run", "build"], cwd=str(site_root))
    if result.returncode != 0:
        print(f"npm run build failed with exit code {result.returncode}")
        return result.returncode

    dist = site_root / "dist"
    print(f"Site built → {dist}")
    return 0
```

- [ ] **Step 2: 验证 registry 命令**

```bash
cd /d/量化研报分析 && python -m pipeline registry
```
期望：输出 "Registry saved → ..." 和 "Landscape saved → ..."，并检查生成的文件：
```bash
python -c "import json; d=json.load(open('data/registry/entities.json','r',encoding='utf-8')); print(f'factors: {len(d[\"factors\"])}, methods: {len(d[\"methods\"])}')"
python -c "import json; d=json.load(open('data/landscape/coverage.json','r',encoding='utf-8')); print(f'dimensions: {len(d[\"dimensions\"])}, gaps: {len(d[\"gaps\"])}')"
```

- [ ] **Step 3: 运行全部测试**

```bash
cd /d/量化研报分析 && python -m pytest tests/ -v
```
期望：29 passed

- [ ] **Step 4: Commit**

```bash
git add pipeline/cli.py
git commit -m "feat: add registry CLI subcommand + integrate into build

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: 安装 Chart.js 依赖

**Files:**
- Modify: `site/package.json`

- [ ] **Step 1: 安装 chart.js、react-chartjs-2 和 chartjs-chart-matrix**

```bash
cd /d/量化研报分析/site && npm install chart.js react-chartjs-2 chartjs-chart-matrix
```

- [ ] **Step 2: 验证安装**

```bash
cd /d/量化研报分析/site && node -e "require('chart.js'); require('react-chartjs-2'); require('chartjs-chart-matrix'); console.log('OK')"
```
期望：OK

- [ ] **Step 3: Commit**

```bash
cd /d/量化研报分析 && git add site/package.json site/package-lock.json
git commit -m "chore: add chart.js + react-chartjs-2 for heatmap

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: 因子·方法注册表页面

**Files:**
- Create: `site/src/pages/registry/index.astro`

**Interfaces:**
- Consumes: `src/data/entities.json` (由 build 命令复制到此处，通过 `fs.readFileSync` 读取)
- Produces: `/registry/` 页面

- [ ] **Step 1: 创建注册表页面**

创建 `site/src/pages/registry/index.astro`：

```astro
---
import BaseLayout from "../../layouts/BaseLayout.astro";
import fs from "node:fs";
import path from "node:path";

// Load entities from src/data/entities.json at build time
const dataDir = path.resolve("src/data");
let factors: any[] = [];
let methods: any[] = [];
try {
  const raw = fs.readFileSync(path.join(dataDir, "entities.json"), "utf-8");
  const data = JSON.parse(raw);
  factors = data.factors || [];
  methods = data.methods || [];
} catch {
  // entities.json not yet generated; show empty state
}
const allEntities = [...factors.map((f: any) => ({ ...f, entityType: "factor" })), ...methods.map((m: any) => ({ ...m, entityType: "method" }))];
---

<BaseLayout>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6 font-mono">
      <span class="text-accent-cyan">&gt;</span> 因子·方法注册表
      <span class="text-sm text-gray-500 ml-2">({allEntities.length} 个实体)</span>
    </h1>

    <div class="flex gap-6">
      <!-- Facets sidebar -->
      <aside class="w-56 shrink-0 space-y-5">
        <div class="panel p-3 text-sm">
          <div class="font-mono text-xs text-gray-400 uppercase tracking-wider mb-2">类型</div>
          <div class="space-y-1">
            <label class="flex items-center gap-2 text-xs cursor-pointer hover:text-white">
              <input type="radio" name="entity-type" class="facet-radio rounded border-border bg-bg text-accent-cyan" value="all" checked />
              全部
            </label>
            <label class="flex items-center gap-2 text-xs cursor-pointer hover:text-white">
              <input type="radio" name="entity-type" class="facet-radio rounded border-border bg-bg text-accent-cyan" value="factor" />
              因子 ({factors.length})
            </label>
            <label class="flex items-center gap-2 text-xs cursor-pointer hover:text-white">
              <input type="radio" name="entity-type" class="facet-radio rounded border-border bg-bg text-accent-cyan" value="method" />
              方法 ({methods.length})
            </label>
          </div>
        </div>
      </aside>

      <!-- Entity list -->
      <div class="flex-1">
        <input type="text" id="search-input" placeholder="搜索实体名称..." class="w-full panel text-xs px-3 py-1.5 rounded bg-bg border-border text-gray-300 placeholder-gray-600 mb-4" />

        <div id="entity-list" class="space-y-3">
          {allEntities.length === 0 && (
            <div class="panel p-8 text-center text-gray-500">
              <p class="text-lg mb-2">暂无实体数据</p>
              <p class="text-xs">运行 <code class="font-mono text-accent-cyan">python -m pipeline registry</code> 生成实体索引</p>
            </div>
          )}
          {allEntities.map((e: any) => (
            <details class="panel p-4 entity-card" data-type={e.entityType}>
              <summary class="cursor-pointer flex items-center justify-between">
                <span class="font-medium text-white">{e.name}</span>
                <div class="flex items-center gap-3 text-xs">
                  <span class="tag">{e.report_count} 篇报告</span>
                  <span class={`tag ${e.entityType === "factor" ? "bg-accent-amber/10 text-accent-amber border-accent-amber/30" : "bg-accent-indigo/10 text-accent-indigo border-accent-indigo/30"}`}>{e.entityType}</span>
                </div>
              </summary>
              <div class="mt-3 pt-3 border-t border-border space-y-2">
                <div class="flex flex-wrap gap-1">
                  {e.tags?.map((t: string) => <span class="tag text-xs">{t}</span>)}
                </div>
                <div class="text-xs text-gray-400 space-y-1">
                  <span class="text-gray-500">引用报告：</span>
                  {e.reports?.map((r: any) => (
                    <a href={`/reports/${r.slug}`} class="block text-accent-cyan hover:underline ml-2">
                      [{r.institution}] {r.title}
                    </a>
                  ))}
                </div>
              </div>
            </details>
          ))}
        </div>
      </div>
    </div>
  </div>
</BaseLayout>

<script>
  const searchInput = document.getElementById("search-input") as HTMLInputElement;
  const radios = document.querySelectorAll(".facet-radio") as NodeListOf<HTMLInputElement>;

  function filter() {
    const search = searchInput.value.toLowerCase();
    const activeType = Array.from(radios).find(r => r.checked)?.value || "all";
    const cards = document.querySelectorAll(".entity-card") as NodeListOf<HTMLElement>;
    cards.forEach(card => {
      const text = (card.textContent || "").toLowerCase();
      const type = card.dataset.type || "";
      const typeMatch = activeType === "all" || type === activeType;
      const searchMatch = text.includes(search);
      card.style.display = typeMatch && searchMatch ? "" : "none";
    });
  }

  searchInput.addEventListener("input", filter);
  radios.forEach(r => r.addEventListener("change", filter));
</script>
```

- [ ] **Step 2: 生成数据并验证构建**

```bash
cd /d/量化研报分析 && python -m pipeline registry && mkdir -p site/src/data && cp data/registry/entities.json site/src/data/ && cp data/landscape/coverage.json site/src/data/ && cd site && npm run build 2>&1 | tail -15
```
期望：构建成功，包含 `/registry/index.html`

- [ ] **Step 3: Commit**

```bash
git add site/src/pages/registry/
git commit -m "feat: add factor/method registry page

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: 全景图热力图 + 研究空白页面

**Files:**
- Create: `site/src/components/HeatmapChart.tsx`
- Create: `site/src/pages/landscape/index.astro`

**Interfaces:**
- Consumes: `src/data/coverage.json` (由 build 命令复制，通过 `fs.readFileSync` 读取)
- HeatmapChart props: `{dimension: {id, label, x_labels, y_labels, matrix}, gaps: array}`
- Produces: `/landscape/` 页面

- [ ] **Step 1: 创建 HeatmapChart React 组件**

创建 `site/src/components/HeatmapChart.tsx`：

```tsx
import { Chart as ChartJS, Tooltip, CategoryScale, LinearScale } from "chart.js";
import { MatrixController, MatrixElement } from "chartjs-chart-matrix";
import { Chart } from "react-chartjs-2";
import type { TooltipItem } from "chart.js";

ChartJS.register(Tooltip, CategoryScale, LinearScale, MatrixController, MatrixElement);

interface MatrixCell {
  x: string;
  y: string;
  count: number;
  slugs: string[];
}

interface Dimension {
  id: string;
  label: string;
  x_labels: string[];
  y_labels: string[];
  matrix: MatrixCell[];
}

interface HeatmapChartProps {
  dimension: Dimension;
}

export default function HeatmapChart({ dimension }: HeatmapChartProps) {
  const maxCount = Math.max(1, ...dimension.matrix.map((c) => c.count));

  const data = {
    datasets: [
      {
        label: "报告数",
        data: dimension.matrix.map((cell) => ({
          x: dimension.x_labels.indexOf(cell.x),
          y: dimension.y_labels.indexOf(cell.y),
          v: cell.count,
          slugs: cell.slugs,
        })),
        backgroundColor(ctx: any) {
          const v = (ctx.raw?.v || 0) as number;
          if (v === 0) return "rgba(30, 39, 51, 0.5)"; // 空白 = 灰色
          const alpha = 0.2 + (v / maxCount) * 0.8;
          return `rgba(34, 211, 238, ${alpha})`;
        },
        borderColor: "#1E2733",
        borderWidth: 1,
        width: ({ chart }: any) => {
          const area = chart.chartArea || { width: 600 };
          const xCount = dimension.x_labels.length || 1;
          return (area.width / xCount) * 0.9;
        },
        height: ({ chart }: any) => {
          const area = chart.chartArea || { height: 400 };
          const yCount = dimension.y_labels.length || 1;
          return (area.height / yCount) * 0.9;
        },
      },
    ],
  };

  const options: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        callbacks: {
          title: (items: TooltipItem<"matrix">[]) => {
            const item = items[0];
            const raw = item.raw as any;
            return `${dimension.y_labels[raw.y]} × ${dimension.x_labels[raw.x]}`;
          },
          label: (item: TooltipItem<"matrix">) => {
            const raw = item.raw as any;
            if (raw.v === 0) return "研究空白";
            return `${raw.v} 篇报告`;
          },
        },
      },
      legend: { display: false },
    },
    scales: {
      x: {
        type: "category" as const,
        labels: dimension.x_labels,
        offset: true,
        ticks: { color: "#6B7280", font: { size: 10 } },
        grid: { display: false },
      },
      y: {
        type: "category" as const,
        labels: dimension.y_labels,
        offset: true,
        ticks: { color: "#6B7280", font: { size: 10 } },
        grid: { display: false },
      },
    },
  };

  return (
    <div style={{ height: `${Math.max(200, dimension.y_labels.length * 50 + 40)}px` }}>
      <Chart type="matrix" data={data} options={options} />
    </div>
  );
}
```

- [ ] **Step 2: 创建全景图页面**

创建 `site/src/pages/landscape/index.astro`：

```astro
---
import BaseLayout from "../../layouts/BaseLayout.astro";
import HeatmapChart from "../../components/HeatmapChart.tsx";
import fs from "node:fs";
import path from "node:path";

const dataDir = path.resolve("src/data");
let dimensions: any[] = [];
let gaps: any[] = [];
let improvementIdeas: any[] = [];
try {
  const raw = fs.readFileSync(path.join(dataDir, "coverage.json"), "utf-8");
  const data = JSON.parse(raw);
  dimensions = data.dimensions || [];
  gaps = data.gaps || [];
} catch {
  // coverage.json not yet generated
}

// Collect improvement ideas from analyses
import { getCollection } from "astro:content";
const analyses = await getCollection("analyses");
const ok = analyses.filter((a: any) => a.data.status === "ok");
improvementIdeas = ok.flatMap((a: any) =>
  (a.data.critical?.improvement_ideas || []).map((idea: any) => ({
    ...idea,
    reportTitle: a.data.source.title,
    reportSlug: a.data.slug,
  }))
);
---

<BaseLayout>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6 font-mono">
      <span class="text-accent-cyan">&gt;</span> 全景图
      <span class="text-sm text-gray-500 ml-2">研究覆盖热力图</span>
    </h1>

    {dimensions.length === 0 && (
      <div class="panel p-8 text-center text-gray-500 mb-8">
        <p class="text-lg mb-2">暂无全景图数据</p>
        <p class="text-xs">运行 <code class="font-mono text-accent-cyan">python -m pipeline registry</code> 生成覆盖矩阵</p>
      </div>
    )}

    <!-- Dimension tabs -->
    <div id="dim-tabs" class="flex gap-2 mb-6">
      {dimensions.map((dim: any, i: number) => (
        <button class={`dim-tab text-xs px-3 py-1.5 rounded border ${i === 0 ? "border-accent-cyan text-accent-cyan bg-accent-cyan/10" : "border-border text-gray-400 hover:text-white"}`} data-dim={i}>
          {dim.label}
        </button>
      ))}
    </div>

    <!-- Heatmap panels -->
    {dimensions.map((dim: any, i: number) => (
      <div class={`dim-panel ${i === 0 ? "" : "hidden"}`} data-dim={i}>
        <div class="panel p-4 mb-6">
          <h3 class="text-xs font-mono text-gray-500 uppercase tracking-wider mb-3">{dim.label}</h3>
          <HeatmapChart dimension={dim} client:load />
        </div>
      </div>
    ))}

    <!-- Research gaps -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
      <div class="panel p-4">
        <h3 class="text-xs font-mono text-gray-500 uppercase tracking-wider mb-3">研究空白 ({gaps.length})</h3>
        {gaps.length === 0 ? (
          <p class="text-sm text-gray-500">暂无空白 — 所有维度组合均有覆盖</p>
        ) : (
          <div class="space-y-1 max-h-64 overflow-y-auto">
            {gaps.slice(0, 20).map((g: any) => (
              <div class="text-xs text-gray-400 flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-border inline-block shrink-0"></span>
                <span class="text-gray-500">{g.y}</span>
                <span>×</span>
                <span class="text-gray-500">{g.x}</span>
                <span class="text-gray-600 ml-auto">{g.dimension?.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <!-- Improvement ideas -->
      <div class="panel p-4">
        <h3 class="text-xs font-mono text-accent-amber uppercase tracking-wider mb-3">改进机会 ({improvementIdeas.length})</h3>
        {improvementIdeas.length === 0 ? (
          <p class="text-sm text-gray-500">暂无改进建议</p>
        ) : (
          <div class="space-y-3 max-h-64 overflow-y-auto">
            {improvementIdeas.map((im: any) => (
              <div class="text-sm">
                <p class="text-gray-300">{im.idea}</p>
                <div class="text-xs text-gray-500 mt-1 flex items-center gap-2">
                  <a href={`/reports/${im.reportSlug}`} class="text-accent-cyan hover:underline truncate">{im.reportTitle}</a>
                  {im.expected_gain && <span class="text-accent-green">预期: {im.expected_gain}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  </div>
</BaseLayout>

<script>
  // Dimension tab switching
  const tabs = document.querySelectorAll(".dim-tab") as NodeListOf<HTMLButtonElement>;
  const panels = document.querySelectorAll(".dim-panel") as NodeListOf<HTMLElement>;

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const dim = tab.dataset.dim!;
      tabs.forEach(t => {
        t.className = "dim-tab text-xs px-3 py-1.5 rounded border border-border text-gray-400 hover:text-white";
      });
      tab.className = "dim-tab text-xs px-3 py-1.5 rounded border border-accent-cyan text-accent-cyan bg-accent-cyan/10";
      panels.forEach(p => {
        p.classList.toggle("hidden", p.dataset.dim !== dim);
      });
    });
  });
</script>
```

- [ ] **Step 3: 验证构建**

```bash
cd /d/量化研报分析/site && npm run build 2>&1 | tail -15
```
期望：构建成功，包含 `/landscape/index.html`

- [ ] **Step 4: Commit**

```bash
git add site/src/components/HeatmapChart.tsx site/src/pages/landscape/
git commit -m "feat: add landscape heatmap page with Chart.js + research gaps

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: 同主题对比页

**Files:**
- Create: `site/src/pages/compare/[a]-[b].astro`

**Interfaces:**
- Consumes: Astro content collection `analyses`
- URL params: `a` 和 `b` 是两个报告 slug
- Produces: `/compare/[a]-[b]/` 页面，左右并排对比

- [ ] **Step 1: 创建对比页**

创建 `site/src/pages/compare/[a]-[b].astro`：

```astro
---
import BaseLayout from "../../layouts/BaseLayout.astro";
import { getCollection } from "astro:content";

export async function getStaticPaths() {
  const analyses = await getCollection("analyses");
  const ok = analyses.filter((a: any) => a.data.status === "ok");
  const paths: any[] = [];
  // Generate all pairs
  for (let i = 0; i < ok.length; i++) {
    for (let j = i + 1; j < ok.length; j++) {
      paths.push({
        params: { a: ok[i].data.slug, b: ok[j].data.slug },
      });
    }
  }
  return paths;
}

const { a: slugA, b: slugB } = Astro.params;
const analyses = await getCollection("analyses");
const reportA = analyses.find((x: any) => x.data.slug === slugA);
const reportB = analyses.find((x: any) => x.data.slug === slugB);
if (!reportA || !reportB) {
  return Astro.redirect("/reports");
}

const A = reportA.data;
const B = reportB.data;

// Jaccard similarity
function jaccard(a: any, b: any) {
  const tagsA = new Set([
    ...a.classification.research_type,
    ...a.classification.factor_family,
    ...a.classification.method,
    ...a.classification.asset_class,
    ...a.classification.data_frequency,
  ]);
  const tagsB = new Set([
    ...b.classification.research_type,
    ...b.classification.factor_family,
    ...b.classification.method,
    ...b.classification.asset_class,
    ...b.classification.data_frequency,
  ]);
  const intersection = new Set([...tagsA].filter((x) => tagsB.has(x)));
  const union = new Set([...tagsA, ...tagsB]);
  return union.size === 0 ? 0 : (intersection.size / union.size * 100).toFixed(0);
}

const sim = jaccard(A, B);

// Collect all classification keys for comparison
const clsKeys = ["research_type", "data_frequency", "factor_family", "asset_class", "method"] as const;
---

<BaseLayout>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <div class="mb-6">
      <a href="/reports" class="text-xs text-gray-500 hover:text-accent-cyan transition-colors">&larr; 返回列表</a>
      <h1 class="text-xl font-bold mt-2 text-white">报告对比</h1>
      <div class="text-xs text-gray-500 mt-1">
        相似度: <span class="font-mono text-accent-cyan">{sim}%</span>
        <span class="text-gray-600 ml-2">(Jaccard)</span>
      </div>
    </div>

    <!-- Side-by-side layout -->
    <div class="grid grid-cols-2 gap-6">
      <!-- Left: Report A -->
      <div class="space-y-4">
        <div class="panel p-4 border-t-2 border-t-accent-cyan">
          <h2 class="font-medium text-white text-sm mb-1">{A.source.title}</h2>
          <span class="tag">{A.source.institution}</span>
        </div>

        <CompareSection title="评分">
          <div class="flex gap-4 text-sm font-mono">
            <span class="text-accent-green">Q{A.ratings.quality}</span>
            <span class="text-accent-indigo">N{A.ratings.novelty}</span>
            <span class="text-accent-amber">R{A.ratings.reusability}</span>
          </div>
        </CompareSection>

        <CompareSection title="分类">
          {clsKeys.map((key) => {
            const vals = A.classification[key] as string[];
            return vals.length > 0 && (
              <div class="flex items-baseline gap-2 text-xs mb-1">
                <span class="text-gray-500 w-24 shrink-0">{key}:</span>
                <div class="flex flex-wrap gap-1">
                  {vals.map((v: string) => <span class="tag">{v}</span>)}
                </div>
              </div>
            );
          })}
        </CompareSection>

        <CompareSection title="实体">
          {A.entities?.length > 0 ? (
            <div class="flex flex-wrap gap-1">
              {A.entities.map((e: any) => (
                <span class="tag text-xs">{e.name} <span class="text-gray-500">[{e.type}]</span></span>
              ))}
            </div>
          ) : <span class="text-xs text-gray-500">无</span>}
        </CompareSection>

        <CompareSection title="构造类型">
          <span class="tag text-sm">{A.detailed.construction?.type || "未知"}</span>
        </CompareSection>

        <CompareSection title="关键结论">
          <p class="text-sm text-gray-300">{A.concise.key_result}</p>
        </CompareSection>
      </div>

      <!-- Right: Report B -->
      <div class="space-y-4">
        <div class="panel p-4 border-t-2 border-t-accent-indigo">
          <h2 class="font-medium text-white text-sm mb-1">{B.source.title}</h2>
          <span class="tag">{B.source.institution}</span>
        </div>

        <CompareSection title="评分">
          <div class="flex gap-4 text-sm font-mono">
            <span class="text-accent-green">Q{B.ratings.quality}</span>
            <span class="text-accent-indigo">N{B.ratings.novelty}</span>
            <span class="text-accent-amber">R{B.ratings.reusability}</span>
          </div>
        </CompareSection>

        <CompareSection title="分类">
          {clsKeys.map((key) => {
            const vals = B.classification[key] as string[];
            return vals.length > 0 && (
              <div class="flex items-baseline gap-2 text-xs mb-1">
                <span class="text-gray-500 w-24 shrink-0">{key}:</span>
                <div class="flex flex-wrap gap-1">
                  {vals.map((v: string) => <span class="tag">{v}</span>)}
                </div>
              </div>
            );
          })}
        </CompareSection>

        <CompareSection title="实体">
          {B.entities?.length > 0 ? (
            <div class="flex flex-wrap gap-1">
              {B.entities.map((e: any) => (
                <span class="tag text-xs">{e.name} <span class="text-gray-500">[{e.type}]</span></span>
              ))}
            </div>
          ) : <span class="text-xs text-gray-500">无</span>}
        </CompareSection>

        <CompareSection title="构造类型">
          <span class="tag text-sm">{B.detailed.construction?.type || "未知"}</span>
        </CompareSection>

        <CompareSection title="关键结论">
          <p class="text-sm text-gray-300">{B.concise.key_result}</p>
        </CompareSection>
      </div>
    </div>

    <!-- Critical comparison -->
    <div class="grid grid-cols-2 gap-6 mt-6">
      <CriticalColumn title="不足与缺陷" color="text-red" border="border-l-red" items={A.critical?.weaknesses || []} />
      <CriticalColumn title="不足与缺陷" color="text-red" border="border-l-red" items={B.critical?.weaknesses || []} />
      <CriticalColumn title="可复用元素" color="text-accent-green" border="border-l-accent-green" items={A.critical?.useful_elements || []} />
      <CriticalColumn title="可复用元素" color="text-accent-green" border="border-l-accent-green" items={B.critical?.useful_elements || []} />
      <CriticalColumn title="启发" color="text-accent-indigo" border="border-l-accent-indigo" items={A.critical?.inspirations || []} />
      <CriticalColumn title="启发" color="text-accent-indigo" border="border-l-accent-indigo" items={B.critical?.inspirations || []} />
    </div>
  </div>
</BaseLayout>

---
// Helper components
interface SectionProps {
  title: string;
}

const CompareSection = (props: SectionProps & { children: any }) => (
  <div class="panel p-3">
    <h4 class="text-xs font-mono text-gray-500 uppercase tracking-wider mb-2">{props.title}</h4>
    {props.children}
  </div>
);

interface CriticalProps {
  title: string;
  color: string;
  border: string;
  items: string[];
}

const CriticalColumn = (props: CriticalProps) => (
  <div class={`panel p-4 border-l-2 ${props.border}`}>
    <h3 class={`text-xs font-mono ${props.color} uppercase tracking-wider mb-2`}>{props.title}</h3>
    {props.items.length === 0 ? (
      <p class="text-xs text-gray-500">无</p>
    ) : (
      <ul class="list-disc list-inside space-y-1 text-sm text-gray-300">
        {props.items.map((item: string) => <li>{item}</li>)}
      </ul>
    )}
  </div>
);
```

- [ ] **Step 2: 验证构建**

```bash
cd /d/量化研报分析/site && npm run build 2>&1 | tail -20
```
期望：构建成功，包含 3 个对比页（3 篇报告 → C(3,2) = 3 对）

- [ ] **Step 3: Commit**

```bash
git add site/src/pages/compare/
git commit -m "feat: add side-by-side report comparison page

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: 导航栏更新 + 最终集成验证

**Files:**
- Modify: `site/src/layouts/BaseLayout.astro`

- [ ] **Step 1: 更新导航栏**

在 BaseLayout.astro 的导航栏中，在"关于"链接之前添加两个新链接：

```astro
<a href="/registry" class="hover:text-white transition-colors">注册表</a>
<a href="/landscape" class="hover:text-white transition-colors">全景图</a>
```

修改后的导航栏 `<nav>` 部分：

```astro
<nav class="border-b border-border bg-panel/80 backdrop-blur sticky top-0 z-50">
  <div class="max-w-7xl mx-auto px-4 h-12 flex items-center gap-6 text-sm font-medium">
    <a href="/" class="text-accent-cyan font-bold text-base tracking-tight">QuantReports</a>
    <a href="/" class="hover:text-white transition-colors">首页</a>
    <a href="/reports" class="hover:text-white transition-colors">报告</a>
    <a href="/registry" class="hover:text-white transition-colors">注册表</a>
    <a href="/landscape" class="hover:text-white transition-colors">全景图</a>
    <a href="/about" class="hover:text-white transition-colors">关于</a>
  </div>
</nav>
```

- [ ] **Step 2: 运行完整构建验证**

```bash
cd /d/量化研报分析 && python -m pipeline build 2>&1 | tail -20
```
期望：`pipeline build` 成功，dist 包含所有页面（about, index, reports/3篇, registry, landscape, compare/3对）

- [ ] **Step 3: 运行全部测试**

```bash
cd /d/量化研报分析 && python -m pytest tests/ -v
```
期望：29 passed

- [ ] **Step 4: 启动 dev server 验证**

```bash
cd /d/量化研报分析/site && npm run dev
```
访问验证：
- http://localhost:4321/registry — 注册表页面
- http://localhost:4321/landscape — 全景图热力图
- http://localhost:4321/compare/a834ae9c2e1e-b0af7c5f7305 — 对比页

- [ ] **Step 5: Commit**

```bash
git add site/src/layouts/BaseLayout.astro
git commit -m "feat: add registry and landscape links to navbar

Co-Authored-By: Claude <noreply@anthropic.com>"
```