# 量化研报分析 Agent · M1 实现计划(解析 + 单篇分析骨架)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 Python 流水线骨架,读取 `Clippings/*.md` 研报,经火山引擎 Ark(GLM-5.2)两段式分析,产出符合 schema 的单篇分析 JSON + manifest,并在真实样本上跑通端到端。

**Architecture:** 四层流水线的第①②层(Ingest + Analyze)。Ingest 把 MD 归一化为 `NormalizedDoc`;Analyze 用 `ArkProvider` 两段式调用 LLM(先结构化抽取,再深度生成),pydantic 校验后写入 `data/analyses/{slug}.json`。manifest(content-hash + schema_version)驱动增量,未变动报告跳过。

**Tech Stack:** Python ≥3.11 · pydantic v2 · PyYAML · python-frontmatter · volcenginesdkarkruntime · pytest

## Global Constraints

- Python ≥3.11;依赖装在项目 venv。
- LLM 走火山引擎 Ark(`volcenginesdkarkruntime.Ark`),模型默认 `GLM-5.2`,API key 走环境变量 `ARK_API_KEY`;换模型只改 `config.yaml` 的 `model`。
- 项目根 `D:\量化研报分析\`;只读 vault `D:\知识库\obsidian`(`config.yaml` 的 `vault_path`),**绝不写 vault**。
- 单元测试中 **不调用真实 LLM**;`ArkProvider` 通过注入假 client 测试。
- 机构名直接用 `Clippings/` 目录名,不做映射。
- schema_version 固定 `"1.0"`。
- 每个任务的 commit message 结尾加一行:`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

---

## File Structure(M1 涉及文件)

```
D:\量化研报分析\
├── pyproject.toml                 # 依赖与 pytest 配置
├── config.yaml                    # vault 路径、模型、分类体系
├── .env.example                   # ARK_API_KEY=...
├── pipeline/
│   ├── __init__.py                # 空
│   ├── __main__.py                # python -m pipeline 入口
│   ├── cli.py                     # run [--file|--slug] 命令编排
│   ├── config.py                  # load_config()
│   ├── io_paths.py                # 路径常量 paths
│   ├── ingest/
│   │   ├── __init__.py            # 空
│   │   ├── normalize.py           # NormalizedDoc/Section/DocMetadata/make_slug
│   │   ├── markdown.py            # parse_markdown_file()
│   │   └── manifest.py            # Manifest(hash/needs_analysis/update/save)
│   ├── llm/
│   │   ├── __init__.py            # 空
│   │   └── provider.py            # ArkProvider.chat()
│   └── analyze/
│       ├── __init__.py            # 空
│       ├── schema.py              # pydantic 模型(Analysis 及子模型)
│       ├── prompts.py             # extract/analyze prompt 模板
│       └── analyzer.py            # Analyzer.analyze()(两段式 + 校验 + 组装)
└── tests/
    ├── conftest.py                # (按需)
    ├── test_config.py
    ├── test_normalize.py
    ├── test_markdown.py
    ├── test_manifest.py
    ├── test_provider.py
    ├── test_schema.py
    ├── test_prompts.py
    ├── test_analyzer.py
    └── test_cli.py
```

**关键接口(跨任务契约):**
- `NormalizedDoc(slug, source_path, source_type, metadata: DocMetadata, clean_text, tables, sections)` — `ingest/normalize.py`
- `DocMetadata(institution, title, authors, published, original_url)` — `ingest/normalize.py`
- `make_slug(relative_path: str) -> str` — `ingest/normalize.py`(sha1[:12])
- `parse_markdown_file(path: Path, cfg: dict) -> NormalizedDoc` — `ingest/markdown.py`
- `Manifest.load(path) / .needs_analysis(rel, hash, schema_ver) / .update(...) / .save(path) / .hash_file(path)` — `ingest/manifest.py`
- `ArkProvider(model, api_key=None, client=None).chat(messages, **kw) -> str` — `llm/provider.py`
- `Analysis` 及子模型 — `analyze/schema.py`;`Analysis(**payload)` 构造,`.model_dump_json(indent=2)` 序列化
- `Analyzer(provider, taxonomy: dict, model: str).analyze(doc: NormalizedDoc) -> Analysis` — `analyze/analyzer.py`
- `load_config() -> dict`;`io_paths.paths.{root,data,analyses,manifest,config,clippings(cfg),pdfs(cfg)}`

---

### Task 1: 项目骨架 + 配置 + 路径

**Files:**
- Create: `pyproject.toml`, `config.yaml`, `.env.example`, `pipeline/__init__.py`, `pipeline/config.py`, `pipeline/io_paths.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `load_config() -> dict`;`io_paths.paths`(单例,含 `.root/.data/.analyses/.manifest/.config` 与方法 `.clippings(cfg)/.pdfs(cfg)`)

- [ ] **Step 1: 写失败测试 `tests/test_config.py`**

```python
from pipeline.config import load_config
from pipeline import io_paths

def test_load_config_defaults():
    cfg = load_config()
    assert cfg["model"] == "GLM-5.2"
    assert cfg["vault_path"].endswith("obsidian")
    assert "research_type" in cfg["classification"]
    assert io_paths.paths.root.exists()
    assert io_paths.paths.analyses.name == "analyses"
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: 写 `pyproject.toml`**

```toml
[project]
name = "quant-report-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "volcenginesdkarkruntime>=0.1.0",
  "pydantic>=2.0",
  "pyyaml>=6.0",
  "python-frontmatter>=1.0",
]
[project.optional-dependencies]
dev = ["pytest>=7.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 4: 写 `config.yaml`**

```yaml
vault_path: "D:/知识库/obsidian"
clippings_dir: "Clippings"
pdfs_dir: "raw/pdfs"
data_dir: "data"
model: "GLM-5.2"
classification:
  research_type: ["基本面", "技术面(量价)", "高频·微观结构", "资产配置·风格轮动", "行业轮动", "AI·机器学习", "另类数据"]
  data_frequency: ["财务(低频)", "日频", "分钟", "盘口", "逐笔(Level-2)", "集合竞价", "隔夜"]
  factor_family: ["动量", "反转", "波动率", "资金流", "流动性", "价值", "质量", "分析师", "情绪", "红利"]
  asset_class: ["A股", "港股", "指数增强", "行业轮动", "多资产", "基金"]
  method: ["统计线性", "树模型", "深度学习", "强化学习", "遗传规划·符号回归", "知识图谱·RAG", "组合优化"]
```

- [ ] **Step 5: 写 `.env.example`**

```
ARK_API_KEY=your_volcengine_ark_key_here
```

- [ ] **Step 6: 写 `pipeline/__init__.py`(空)、`pipeline/io_paths.py`、`pipeline/config.py`**

`pipeline/io_paths.py`:
```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ANALYSES = DATA / "analyses"
REGISTRY = DATA / "registry"
LANDSCAPE = DATA / "landscape"
MANIFEST = DATA / "manifest.json"
CONFIG = ROOT / "config.yaml"


class _Paths:
    def __init__(self):
        self.root = ROOT
        self.data = DATA
        self.analyses = ANALYSES
        self.registry = REGISTRY
        self.landscape = LANDSCAPE
        self.manifest = MANIFEST
        self.config = CONFIG

    def vault(self, cfg):
        return Path(cfg["vault_path"])

    def clippings(self, cfg):
        return self.vault(cfg) / cfg["clippings_dir"]

    def pdfs(self, cfg):
        return self.vault(cfg) / cfg["pdfs_dir"]


paths = _Paths()
```

`pipeline/config.py`:
```python
import yaml
from . import io_paths


def load_config(path=None):
    path = path or io_paths.paths.config
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
```

- [ ] **Step 7: 安装依赖并运行测试**

Run: `pip install -e ".[dev]" && pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add pyproject.toml config.yaml .env.example pipeline/ tests/test_config.py
git commit -m "feat: project scaffold, config, io paths

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: 归一化文档模型 `NormalizedDoc`

**Files:**
- Create: `pipeline/ingest/__init__.py`, `pipeline/ingest/normalize.py`, `tests/test_normalize.py`

**Interfaces:**
- Produces: `Section`, `DocMetadata`, `NormalizedDoc`, `make_slug(relative_path) -> str`

- [ ] **Step 1: 写失败测试 `tests/test_normalize.py`**

```python
from pipeline.ingest.normalize import NormalizedDoc, DocMetadata, Section, make_slug

def test_make_slug_stable_and_unique():
    a = make_slug("广发/x.md")
    assert a == make_slug("广发/x.md")
    assert a != make_slug("国信/x.md")
    assert len(a) == 12

def test_docmetadata_defaults():
    m = DocMetadata(institution="广发", title="T")
    assert m.authors == []
    assert m.published is None
    assert m.original_url is None
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `pytest tests/test_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.ingest.normalize`

- [ ] **Step 3: 写 `pipeline/ingest/__init__.py`(空)与 `pipeline/ingest/normalize.py`**

```python
from dataclasses import dataclass, field
import hashlib


@dataclass
class Section:
    heading: str
    body: str


@dataclass
class DocMetadata:
    institution: str
    title: str
    authors: list[str] = field(default_factory=list)
    published: str | None = None
    original_url: str | None = None


@dataclass
class NormalizedDoc:
    slug: str
    source_path: str
    source_type: str  # wechat | pdf | official | article
    metadata: DocMetadata
    clean_text: str
    tables: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)


def make_slug(relative_path: str) -> str:
    return hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:12]
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `pytest tests/test_normalize.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add pipeline/ingest/__init__.py pipeline/ingest/normalize.py tests/test_normalize.py
git commit -m "feat: NormalizedDoc data model and slug

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Markdown 解析器

**Files:**
- Create: `pipeline/ingest/markdown.py`, `tests/test_markdown.py`

**Interfaces:**
- Consumes: `NormalizedDoc`, `DocMetadata`, `Section`, `make_slug`(Task 2);`io_paths.paths.clippings(cfg)`
- Produces: `parse_markdown_file(path: Path, cfg: dict) -> NormalizedDoc`;`_split_sections(text) -> list[Section]`

- [ ] **Step 1: 写失败测试 `tests/test_markdown.py`**

```python
from pipeline.ingest.markdown import parse_markdown_file, _split_sections

SAMPLE = """---
title: "测试报告"
source: "https://example.com/x"
author:
  - "[[张三]]"
created: 2026-01-01
---

# 第一节
内容 A

## 子节
内容 B
"""

def test_split_sections():
    secs = _split_sections("# T1\nbody1\n## T2\nbody2")
    assert len(secs) == 2
    assert secs[0].heading == "T1"
    assert secs[0].body == "body1"
    assert secs[1].heading == "T2"

def test_parse_markdown(tmp_path):
    cfg = {"vault_path": str(tmp_path), "clippings_dir": "Clippings", "pdfs_dir": "raw/pdfs"}
    clip = tmp_path / "Clippings" / "广发"
    clip.mkdir(parents=True)
    f = clip / "x.md"
    f.write_text(SAMPLE, encoding="utf-8")
    doc = parse_markdown_file(f, cfg)
    assert doc.metadata.institution == "广发"
    assert doc.metadata.title == "测试报告"
    assert doc.metadata.authors == ["张三"]
    assert doc.metadata.original_url == "https://example.com/x"
    assert doc.metadata.published == "2026-01-01"
    assert doc.source_type == "wechat"
    assert len(doc.slug) == 12
    assert any(s.heading == "第一节" for s in doc.sections)
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `pytest tests/test_markdown.py -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.ingest.markdown`

- [ ] **Step 3: 写 `pipeline/ingest/markdown.py`**

```python
import re
from pathlib import Path

import frontmatter

from .. import io_paths
from .normalize import NormalizedDoc, DocMetadata, Section, make_slug

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_WIKILINK = re.compile(r"\[\[(.*?)\]\]")


def _strip_wikilink(s: str) -> str:
    m = _WIKILINK.fullmatch(s.strip())
    return m.group(1) if m else s.strip()


def _split_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    cur_h, cur_body = "", []
    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            if cur_h or cur_body:
                sections.append(Section(cur_h, "\n".join(cur_body).strip()))
            cur_h, cur_body = m.group(2).strip(), []
        else:
            cur_body.append(line)
    if cur_h or cur_body:
        sections.append(Section(cur_h, "\n".join(cur_body).strip()))
    return sections


def parse_markdown_file(path: Path, cfg: dict) -> NormalizedDoc:
    clip_root = io_paths.paths.clippings(cfg)
    rel = str(path.resolve().relative_to(clip_root.resolve())).replace("\\", "/")
    post = frontmatter.loads(path.read_text(encoding="utf-8"))
    fm, body = post.metadata, post.content
    institution = path.parent.name
    authors = [_strip_wikilink(a) for a in (fm.get("author") or [])]
    title = fm.get("title") or path.stem
    published = fm.get("published") or (str(fm.get("created")) if fm.get("created") else None)
    url = fm.get("source")
    return NormalizedDoc(
        slug=make_slug(rel),
        source_path=rel,
        source_type="wechat",
        metadata=DocMetadata(
            institution=institution, title=title, authors=authors,
            published=published, original_url=url,
        ),
        clean_text=body,
        tables=[],
        sections=_split_sections(body),
    )
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `pytest tests/test_markdown.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add pipeline/ingest/markdown.py tests/test_markdown.py
git commit -m "feat: markdown parser (frontmatter + sections)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: 增量 Manifest

**Files:**
- Create: `pipeline/ingest/manifest.py`, `tests/test_manifest.py`

**Interfaces:**
- Produces: `Manifest` 类(静态 `load/hash_file`,实例 `needs_analysis/update/save`);常量 `SCHEMA_VERSION = "1.0"`

- [ ] **Step 1: 写失败测试 `tests/test_manifest.py`**

```python
from pipeline.ingest.manifest import Manifest, SCHEMA_VERSION

def test_new_file_needs_analysis():
    assert Manifest().needs_analysis("a.md", "h1") is True

def test_unchanged_skipped():
    m = Manifest({"a.md": {"hash": "h1", "schema_version": "1.0", "analyzed_at": "x"}})
    assert m.needs_analysis("a.md", "h1") is False

def test_changed_hash_needs_analysis():
    m = Manifest({"a.md": {"hash": "h1", "schema_version": "1.0", "analyzed_at": "x"}})
    assert m.needs_analysis("a.md", "h2") is True

def test_schema_bump_needs_analysis():
    m = Manifest({"a.md": {"hash": "h1", "schema_version": "0.9", "analyzed_at": "x"}})
    assert m.needs_analysis("a.md", "h1") is True

def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "m.json"
    m = Manifest()
    m.update("a.md", "h1")
    m.save(p)
    m2 = Manifest.load(p)
    assert m2.needs_analysis("a.md", "h1") is False

def test_hash_file_stable(tmp_path):
    f = tmp_path / "x.md"
    f.write_text("hello", encoding="utf-8")
    assert Manifest.hash_file(f) == Manifest.hash_file(f)
    assert len(Manifest.hash_file(f)) == 64

def test_schema_version_constant():
    assert SCHEMA_VERSION == "1.0"
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `pytest tests/test_manifest.py -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.ingest.manifest`

- [ ] **Step 3: 写 `pipeline/ingest/manifest.py`**

```python
import hashlib
import json
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = "1.0"


class Manifest:
    def __init__(self, files=None):
        self.files: dict = files or {}

    @staticmethod
    def load(path) -> "Manifest":
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return Manifest(data.get("files", {}))
        return Manifest()

    @staticmethod
    def hash_file(path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def needs_analysis(self, source_path, content_hash, schema_version=SCHEMA_VERSION) -> bool:
        entry = self.files.get(source_path)
        if not entry:
            return True
        return entry.get("hash") != content_hash or entry.get("schema_version") != schema_version

    def update(self, source_path, content_hash, schema_version=SCHEMA_VERSION, analyzed_at=None):
        self.files[source_path] = {
            "hash": content_hash,
            "schema_version": schema_version,
            "analyzed_at": analyzed_at or datetime.utcnow().isoformat(),
        }

    def save(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"files": self.files}, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `pytest tests/test_manifest.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add pipeline/ingest/manifest.py tests/test_manifest.py
git commit -m "feat: incremental manifest (hash + schema_version)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: ArkProvider(火山引擎 LLM 封装)

**Files:**
- Create: `pipeline/llm/__init__.py`, `pipeline/llm/provider.py`, `tests/test_provider.py`

**Interfaces:**
- Produces: `ArkProvider(model, api_key=None, client=None).chat(messages: list[dict], **kw) -> str`

- [ ] **Step 1: 写失败测试 `tests/test_provider.py`**

```python
from pipeline.llm.provider import ArkProvider


class _FakeResp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


class _FakeClient:
    def __init__(self, content="ok"):
        self.chat = type("Chat", (), {
            "completions": type("Comp", (), {
                "create": lambda self, **kw: _FakeResp(self._content),
            })(),
        })()
        self.chat.completions._content = content
        self.calls = []

        def _create(**kw):
            self.calls.append(kw)
            return _FakeResp(content)
        self.chat.completions.create = _create


def test_chat_returns_content():
    p = ArkProvider(model="GLM-5.2", client=_FakeClient("hello"))
    assert p.chat([{"role": "user", "content": "hi"}]) == "hello"

def test_chat_passes_model_messages_and_kwargs():
    fake = _FakeClient("x")
    p = ArkProvider(model="GLM-5.2", client=fake)
    p.chat([{"role": "user", "content": "hi"}], response_format={"type": "json_object"})
    kw = fake.calls[0]
    assert kw["model"] == "GLM-5.2"
    assert kw["messages"] == [{"role": "user", "content": "hi"}]
    assert kw["response_format"] == {"type": "json_object"}
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `pytest tests/test_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.llm.provider`

- [ ] **Step 3: 写 `pipeline/llm/__init__.py`(空)与 `pipeline/llm/provider.py`**

```python
import os

from volcenginesdkarkruntime import Ark


class ArkProvider:
    def __init__(self, model: str, api_key=None, client=None):
        self.model = model
        self._client = client or Ark(api_key=api_key or os.environ.get("ARK_API_KEY"))

    def chat(self, messages, **kw) -> str:
        resp = self._client.chat.completions.create(model=self.model, messages=messages, **kw)
        return resp.choices[0].message.content
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `pytest tests/test_provider.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add pipeline/llm/__init__.py pipeline/llm/provider.py tests/test_provider.py
git commit -m "feat: ArkProvider wrapping volcenginesdkarkruntime

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: 分析 schema(pydantic 模型)

**Files:**
- Create: `pipeline/analyze/__init__.py`, `pipeline/analyze/schema.py`, `tests/test_schema.py`

**Interfaces:**
- Produces: `Analysis` 及全部子模型;`Analysis(**dict).model_dump_json(indent=2)`

- [ ] **Step 1: 写失败测试 `tests/test_schema.py`**

```python
import pytest
from pipeline.analyze.schema import Analysis


def _minimal():
    return {
        "slug": "abc123",
        "source": {"title": "T", "institution": "广发", "source_type": "wechat",
                   "local_path": "广发/x.md", "ingested_at": "2026-07-09"},
        "classification": {},
        "ratings": {"quality": 4, "novelty": 4, "reusability": 3},
        "concise": {"one_liner": "x", "key_result": "y"},
        "detailed": {
            "core_content": "c", "economic_logic": "e",
            "construction": {"type": "model", "model_architecture": "a", "outputs": "o", "training": "t"},
            "excess_return_logic": "ex",
            "performance": {"metrics": []},
            "attribution": {"done": False, "summary": "未做"},
            "novelty_assessment": {"type": "新方法", "summary": "s"},
        },
        "model_used": "GLM-5.2",
    }

def test_valid_analysis():
    a = Analysis(**_minimal())
    assert a.detailed.construction.type == "model"
    assert a.attribution.done is False
    assert a.schema_version == "1.0"

def test_invalid_rating_rejected():
    d = _minimal()
    d["ratings"]["quality"] = 9
    with pytest.raises(Exception):
        Analysis(**d)

def test_serialization_roundtrip():
    a = Analysis(**_minimal())
    js = a.model_dump_json(indent=2)
    a2 = Analysis.model_validate_json(js)
    assert a2.slug == a.slug
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.analyze.schema`

- [ ] **Step 3: 写 `pipeline/analyze/__init__.py`(空)与 `pipeline/analyze/schema.py`**

```python
from typing import Optional
from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    institution: str
    authors: list[str] = []
    published: Optional[str] = None
    source_type: str
    original_url: Optional[str] = None
    local_path: str
    ingested_at: str


class Classification(BaseModel):
    research_type: list[str] = []
    data_frequency: list[str] = []
    factor_family: list[str] = []
    asset_class: list[str] = []
    method: list[str] = []
    custom_tags: list[str] = []


class Ratings(BaseModel):
    quality: int = Field(ge=1, le=5)
    novelty: int = Field(ge=1, le=5)
    reusability: int = Field(ge=1, le=5)


class Concise(BaseModel):
    one_liner: str
    core_points: list[str] = []
    key_result: str


class Metric(BaseModel):
    name: str
    value: str


class Performance(BaseModel):
    metrics: list[Metric] = []
    benchmark: Optional[str] = None
    backtest_period: Optional[str] = None
    turnover: Optional[str] = None
    capacity: Optional[str] = None
    ic_decay: Optional[str] = None
    summary: str = ""


class Attribution(BaseModel):
    done: bool
    method: Optional[str] = None
    summary: str
    gap: Optional[str] = None


class Construction(BaseModel):
    type: str  # factor | model | strategy | config
    data_inputs: list[dict] = []
    backtest_setup: Optional[dict] = None
    combination: Optional[str] = None
    parameters: list[dict] = []
    factor_definition: Optional[str] = None
    processing_pipeline: list[str] = []
    model_architecture: Optional[str] = None
    inputs: list[str] = []
    outputs: Optional[str] = None
    training: Optional[str] = None
    strategy_logic: Optional[str] = None
    allocation: Optional[str] = None


class Robustness(BaseModel):
    subsample_stability: Optional[str] = None
    style_bias: Optional[str] = None
    turnover: Optional[str] = None
    capacity: Optional[str] = None
    summary: str = ""


class DataDependency(BaseModel):
    data_required: str = ""
    reproducibility: str = ""
    summary: str = ""


class PriorArt(BaseModel):
    method: str
    relation: str = ""


class NoveltyAssessment(BaseModel):
    type: str
    summary: str


class Detailed(BaseModel):
    core_content: str
    economic_logic: str
    construction: Construction
    excess_return_logic: str
    performance: Performance
    attribution: Attribution
    robustness: Robustness = Robustness()
    data_dependency: DataDependency = DataDependency()
    prior_art: list[PriorArt] = []
    novelty_assessment: NoveltyAssessment


class ImprovementIdea(BaseModel):
    idea: str
    based_on: str = ""
    expected_gain: str = ""


class Critical(BaseModel):
    weaknesses: list[str] = []
    useful_elements: list[str] = []
    inspirations: list[str] = []
    improvement_ideas: list[ImprovementIdea] = []
    replication_plan: str = ""


class Entity(BaseModel):
    name: str
    type: str


class RelatedReport(BaseModel):
    slug: str
    title: str
    relation: str = ""


class Analysis(BaseModel):
    schema_version: str = "1.0"
    slug: str
    source: Source
    classification: Classification = Classification()
    ratings: Ratings
    concise: Concise
    detailed: Detailed
    critical: Critical = Critical()
    entities: list[Entity] = []
    related_reports: list[RelatedReport] = []
    confidence: str = "high"
    model_used: str
    status: str = "ok"
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `pytest tests/test_schema.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add pipeline/analyze/__init__.py pipeline/analyze/schema.py tests/test_schema.py
git commit -m "feat: pydantic analysis schema

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Prompt 模板

**Files:**
- Create: `pipeline/analyze/prompts.py`, `tests/test_prompts.py`

**Interfaces:**
- Produces: `EXTRACT_SYSTEM`, `ANALYZE_SYSTEM` 常量;`extract_user(**kw) -> str`;`analyze_user(**kw) -> str`

- [ ] **Step 1: 写失败测试 `tests/test_prompts.py`**

```python
from pipeline.analyze.prompts import extract_user, analyze_user, EXTRACT_SYSTEM, ANALYZE_SYSTEM

def test_extract_user_renders_fields():
    s = extract_user(title="T", institution="广发", body="BODY",
                     research_type=["基本面"], data_frequency=["日频"],
                     factor_family=["动量"], asset_class=["A股"], method=["深度学习"])
    assert "T" in s and "广发" in s and "BODY" in s
    assert "基本面" in s and "深度学习" in s

def test_analyze_user_renders_and_requires_reproducible():
    s = analyze_user(title="T", institution="广发", body="BODY", extracted_json='{"x":1}')
    assert "T" in s and "可复现" in s

def test_system_prompts_exist():
    assert EXTRACT_SYSTEM and ANALYZE_SYSTEM
    assert "JSON" in EXTRACT_SYSTEM
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `pytest tests/test_prompts.py -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.analyze.prompts`

- [ ] **Step 3: 写 `pipeline/analyze/prompts.py`**

```python
EXTRACT_SYSTEM = "你是量化研报分析助手。只输出合法 JSON,不要任何解释或多余文本。"

EXTRACT_USER_TMPL = """研报标题:{title}
机构:{institution}

正文:
{body}

请抽取并只输出如下 JSON:
{{
  "classification": {{"research_type": [], "data_frequency": [], "factor_family": [], "asset_class": [], "method": [], "custom_tags": []}},
  "ratings": {{"quality": 1, "novelty": 1, "reusability": 1}},
  "performance": {{"metrics": [{{"name": "", "value": ""}}], "benchmark": "", "backtest_period": "", "summary": ""}},
  "attribution": {{"done": false, "method": null, "summary": "", "gap": ""}},
  "entities": [{{"name": "", "type": "method"}}]
}}
分类取值范围(多选):research_type={research_type}; data_frequency={data_frequency}; factor_family={factor_family}; asset_class={asset_class}; method={method}。ratings 为 1-5 整数。entities.type ∈ factor|method|dataset|model|person|concept。"""

ANALYZE_SYSTEM = "你是资深量化研究员。深度分析研报,构造细节必须达到可复现级别。只输出合法 JSON。"

ANALYZE_USER_TMPL = """研报标题:{title}
机构:{institution}

正文:
{body}

已抽取信息:{extracted_json}

请输出如下 JSON:
{{
  "concise": {{"one_liner": "", "core_points": [], "key_result": ""}},
  "detailed": {{
    "core_content": "", "economic_logic": "",
    "construction": {{
      "type": "factor|model|strategy|config",
      "data_inputs": [{{"field": "", "frequency": "", "source": "", "preprocessing": ""}}],
      "backtest_setup": {{"period": "", "benchmark": "", "rebalance_freq": "", "cost": "", "grouping": ""}},
      "combination": "", "parameters": [{{"name": "", "value": "", "meaning": ""}}],
      "factor_definition": "(因子类填:公式/算子/逐步构造逻辑,达到可复现)",
      "processing_pipeline": [],
      "model_architecture": "(模型类填:网络结构/关键模块)",
      "inputs": [], "outputs": "", "training": ""
    }},
    "excess_return_logic": "",
    "robustness": {{"subsample_stability": "", "style_bias": "", "summary": ""}},
    "data_dependency": {{"data_required": "", "reproducibility": "easy|medium|hard", "summary": ""}},
    "prior_art": [{{"method": "", "relation": ""}}],
    "novelty_assessment": {{"type": "新方法|新数据|新组合|综述", "summary": ""}}
  }},
  "critical": {{
    "weaknesses": [], "useful_elements": [], "inspirations": [],
    "improvement_ideas": [{{"idea": "", "based_on": "", "expected_gain": ""}}],
    "replication_plan": ""
  }}
}}
要求:construction.type 按报告性质选;因子类必填 factor_definition + processing_pipeline(可复现),模型类必填 model_architecture + inputs + outputs + training(可复现);critical 四段必填,improvement_ideas 至少给一条"相似逻辑 + 不同构造"的可行改进。"""


def extract_user(**kw) -> str:
    return EXTRACT_USER_TMPL.format(**kw)


def analyze_user(**kw) -> str:
    return ANALYZE_USER_TMPL.format(**kw)
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `pytest tests/test_prompts.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add pipeline/analyze/prompts.py tests/test_prompts.py
git commit -m "feat: two-stage extraction and analysis prompts

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Analyzer(两段式 + 校验 + 组装)

**Files:**
- Create: `pipeline/analyze/analyzer.py`, `tests/test_analyzer.py`

**Interfaces:**
- Consumes: `ArkProvider.chat`(Task 5)、`Analysis` schema(Task 6)、`prompts`(Task 7)、`NormalizedDoc`(Task 2)
- Produces: `Analyzer(provider, taxonomy, model).analyze(doc: NormalizedDoc) -> Analysis`;`AnalysisError`

- [ ] **Step 1: 写失败测试 `tests/test_analyzer.py`**

```python
import json
from pipeline.analyze.analyzer import Analyzer
from pipeline.ingest.normalize import NormalizedDoc, DocMetadata

EXTRACT_JSON = json.dumps({
    "classification": {"research_type": ["AI·机器学习"], "data_frequency": [], "factor_family": [],
                       "asset_class": [], "method": ["深度学习"], "custom_tags": []},
    "ratings": {"quality": 4, "novelty": 4, "reusability": 3},
    "performance": {"metrics": [{"name": "IC", "value": "13.85%"}]},
    "attribution": {"done": False, "summary": "未做", "gap": "缺归因"},
    "entities": [{"name": "AlphaForge", "type": "method"}],
}, ensure_ascii=False)

ANALYZE_JSON = json.dumps({
    "concise": {"one_liner": "可导因子挖掘", "core_points": ["a"], "key_result": "IC 13.85%"},
    "detailed": {
        "core_content": "c", "economic_logic": "e",
        "construction": {"type": "model", "model_architecture": "AE+DCGAN",
                         "inputs": ["特征"], "outputs": "IC", "training": "梯度下降"},
        "excess_return_logic": "低相关因子组合",
        "performance": {"metrics": []},
        "attribution": {"done": False, "summary": "未做"},
        "novelty_assessment": {"type": "新方法", "summary": "可导框架"},
    },
    "critical": {"weaknesses": ["未归因"], "useful_elements": ["掩码思路"],
                 "inspirations": ["用到附注因子"],
                 "improvement_ideas": [{"idea": "容量感知", "based_on": "加换手惩罚", "expected_gain": "可交易"}],
                 "replication_plan": "复现步骤"},
}, ensure_ascii=False)


class _ScriptedProvider:
    def __init__(self, replies):
        self.replies = list(replies)
        self.i = 0

    def chat(self, messages, **kw):
        r = self.replies[self.i]
        self.i += 1
        return r


def _doc():
    return NormalizedDoc(
        slug="abc123", source_path="广发/x.md", source_type="wechat",
        metadata=DocMetadata(institution="广发", title="T", authors=["张三"],
                             published="2026-01-01", original_url="https://x"),
        clean_text="正文", sections=[])


def test_analyzer_assembles_valid_analysis():
    prov = _ScriptedProvider([EXTRACT_JSON, ANALYZE_JSON])
    a = Analyzer(prov, {"research_type": ["AI·机器学习"], "method": ["深度学习"]}, model="GLM-5.2")
    out = a.analyze(_doc())
    assert out.slug == "abc123"
    assert out.source.institution == "广发"
    assert out.source.original_url == "https://x"
    assert out.ratings.quality == 4
    assert out.detailed.construction.type == "model"
    assert out.critical.weaknesses == ["未归因"]
    assert out.entities[0].name == "AlphaForge"
    assert out.model_used == "GLM-5.2"


def test_analyzer_retries_on_bad_json_then_succeeds():
    bad = "not json"
    prov = _ScriptedProvider([bad, EXTRACT_JSON, ANALYZE_JSON])
    a = Analyzer(prov, {"research_type": [], "method": []}, model="GLM-5.2")
    out = a.analyze(_doc())
    assert out.slug == "abc123"
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `pytest tests/test_analyzer.py -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.analyze.analyzer`

- [ ] **Step 3: 写 `pipeline/analyze/analyzer.py`**

```python
import json
from datetime import date

from . import prompts
from .schema import Analysis
from ..ingest.normalize import NormalizedDoc


class AnalysisError(Exception):
    pass


class Analyzer:
    MAX_RETRIES = 3
    BODY_TRUNC = 12000

    def __init__(self, provider, taxonomy: dict, model: str = "GLM-5.2"):
        self.provider = provider
        self.tax = taxonomy
        self.model = model

    def analyze(self, doc: NormalizedDoc) -> Analysis:
        extracted = self._call_json([
            {"role": "system", "content": prompts.EXTRACT_SYSTEM},
            {"role": "user", "content": self._extract_prompt(doc)},
        ])
        analyzed = self._call_json([
            {"role": "system", "content": prompts.ANALYZE_SYSTEM},
            {"role": "user", "content": self._analyze_prompt(doc, extracted)},
        ])
        return self._assemble(doc, extracted, analyzed)

    def _call_json(self, messages) -> dict:
        last = None
        for mode in ({"response_format": {"type": "json_object"}}, {}):
            for _ in range(self.MAX_RETRIES):
                content = self.provider.chat(messages, **mode)
                last = content
                try:
                    return json.loads(content)
                except Exception:
                    continue
        raise AnalysisError(f"JSON parse failed: {(last or '')[:200]}")

    def _extract_prompt(self, doc):
        return prompts.extract_user(
            title=doc.metadata.title, institution=doc.metadata.institution,
            body=doc.clean_text[:self.BODY_TRUNC],
            research_type=self.tax.get("research_type", []),
            data_frequency=self.tax.get("data_frequency", []),
            factor_family=self.tax.get("factor_family", []),
            asset_class=self.tax.get("asset_class", []),
            method=self.tax.get("method", []),
        )

    def _analyze_prompt(self, doc, extracted):
        return prompts.analyze_user(
            title=doc.metadata.title, institution=doc.metadata.institution,
            body=doc.clean_text[:self.BODY_TRUNC],
            extracted_json=json.dumps(extracted, ensure_ascii=False),
        )

    def _assemble(self, doc, extracted, analyzed) -> Analysis:
        payload = {
            "slug": doc.slug,
            "source": {
                "title": doc.metadata.title, "institution": doc.metadata.institution,
                "authors": doc.metadata.authors, "published": doc.metadata.published,
                "source_type": doc.source_type, "original_url": doc.metadata.original_url,
                "local_path": doc.source_path, "ingested_at": str(date.today()),
            },
            "classification": extracted.get("classification", {}),
            "ratings": extracted.get("ratings", {"quality": 3, "novelty": 3, "reusability": 3}),
            "concise": analyzed.get("concise", {}),
            "detailed": analyzed.get("detailed", {}),
            "critical": analyzed.get("critical", {}),
            "entities": extracted.get("entities", []),
            "model_used": self.model,
        }
        return Analysis(**payload)
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `pytest tests/test_analyzer.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add pipeline/analyze/analyzer.py tests/test_analyzer.py
git commit -m "feat: two-stage analyzer with JSON retry and assembly

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: CLI 入口(编排 + 单篇指定)

**Files:**
- Create: `pipeline/cli.py`, `pipeline/__main__.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_config`、`io_paths`、`parse_markdown_file`、`Manifest`、`ArkProvider`、`Analyzer`、`Analysis`
- Produces: `main(argv=None) -> int`;`python -m pipeline run [--file PATH|--slug SLUG]`

- [ ] **Step 1: 写失败测试 `tests/test_cli.py`**

```python
from pathlib import Path
from pipeline.cli import main, _resolve_targets


def test_resolve_file_relative(tmp_path):
    cfg = {"vault_path": str(tmp_path), "clippings_dir": "Clippings", "pdfs_dir": "raw/pdfs"}
    clip = tmp_path / "Clippings" / "广发"
    clip.mkdir(parents=True)
    f = clip / "a.md"
    f.write_text("---\ntitle: A\n---\nbody", encoding="utf-8")

    class Args:
        file = "广发/a.md"
        slug = None
    assert _resolve_targets(cfg, Args()) == [f]


def test_resolve_scan_all(tmp_path):
    cfg = {"vault_path": str(tmp_path), "clippings_dir": "Clippings", "pdfs_dir": "raw/pdfs"}
    clip = tmp_path / "Clippings" / "广发"
    clip.mkdir(parents=True)
    (clip / "a.md").write_text("---\ntitle: A\n---\nbody", encoding="utf-8")
    (clip / "b.md").write_text("---\ntitle: B\n---\nbody", encoding="utf-8")

    class Args:
        file = None
        slug = None
    assert len(_resolve_targets(cfg, Args())) == 2


def test_main_with_mocked_analyzer(tmp_path, monkeypatch):
    cfg = {
        "vault_path": str(tmp_path), "clippings_dir": "Clippings", "pdfs_dir": "raw/pdfs",
        "model": "GLM-5.2",
        "classification": {"research_type": ["AI·机器学习"], "method": ["深度学习"]},
    }
    clip = tmp_path / "Clippings" / "广发"
    clip.mkdir(parents=True)
    f = clip / "a.md"
    f.write_text("---\ntitle: T\nauthor:\n  - \"[[张三]]\"\nsource: \"https://x\"\ncreated: 2026-01-01\n---\nbody", encoding="utf-8")

    monkeypatch.setattr("pipeline.cli.load_config", lambda: cfg)
    from pipeline import io_paths
    monkeypatch.setattr(io_paths.paths, "analyses", tmp_path / "data" / "analyses")
    monkeypatch.setattr(io_paths.paths, "manifest", tmp_path / "data" / "manifest.json")

    from pipeline.analyze.schema import Analysis

    def fake_analyze(self, doc):
        return Analysis(
            slug=doc.slug,
            source={"title": doc.metadata.title, "institution": doc.metadata.institution,
                    "authors": doc.metadata.authors, "published": doc.metadata.published,
                    "source_type": "wechat", "original_url": doc.metadata.original_url,
                    "local_path": doc.source_path, "ingested_at": "2026-07-09"},
            classification={}, ratings={"quality": 3, "novelty": 3, "reusability": 3},
            concise={"one_liner": "x", "key_result": "y"},
            detailed={"core_content": "c", "economic_logic": "e", "construction": {"type": "model"},
                      "excess_return_logic": "ex", "performance": {"metrics": []},
                      "attribution": {"done": False, "summary": "未做"},
                      "novelty_assessment": {"type": "新方法", "summary": "s"}},
            model_used="GLM-5.2")

    monkeypatch.setattr("pipeline.analyze.analyzer.Analyzer.analyze", fake_analyze)

    code = main(["run"])
    assert code == 0
    outs = list((tmp_path / "data" / "analyses").glob("*.json"))
    assert len(outs) == 1
    assert (tmp_path / "data" / "manifest.json").exists()
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: pipeline.cli`

- [ ] **Step 3: 写 `pipeline/cli.py`**

```python
import argparse
from pathlib import Path

from . import io_paths
from .analyze.analyzer import Analyzer
from .analyze.schema import Analysis
from .config import load_config
from .ingest.manifest import Manifest, SCHEMA_VERSION
from .ingest.markdown import parse_markdown_file
from .llm.provider import ArkProvider


def _resolve_targets(cfg, args):
    clip = io_paths.paths.clippings(cfg)
    if args.file:
        p = Path(args.file)
        if not p.is_absolute():
            p = clip / args.file
        return [p]
    if args.slug:
        for md in sorted(clip.rglob("*.md")):
            if parse_markdown_file(md, cfg).slug == args.slug:
                return [md]
        raise SystemExit(f"slug not found: {args.slug}")
    return sorted(clip.rglob("*.md"))


def _save(analysis: Analysis):
    out = io_paths.paths.analyses / f"{analysis.slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--file")
    run.add_argument("--slug")
    args = parser.parse_args(argv)

    cfg = load_config()
    provider = ArkProvider(model=cfg["model"])
    manifest = Manifest.load(io_paths.paths.manifest)
    analyzer = Analyzer(provider, cfg["classification"], model=cfg["model"])

    clip = io_paths.paths.clippings(cfg)
    targets = _resolve_targets(cfg, args)
    changed = 0
    for path in targets:
        if not path.exists():
            continue
        rel = str(path.resolve().relative_to(clip.resolve())).replace("\\", "/")
        h = Manifest.hash_file(path)
        if not manifest.needs_analysis(rel, h, SCHEMA_VERSION):
            continue
        doc = parse_markdown_file(path, cfg)
        try:
            analysis = analyzer.analyze(doc)
        except Exception as e:
            print(f"[FAIL] {rel}: {e}")
            continue
        _save(analysis)
        manifest.update(rel, h, SCHEMA_VERSION)
        changed += 1
        print(f"[OK] {rel} -> {analysis.slug}.json")
    manifest.save(io_paths.paths.manifest)
    print(f"analyzed {changed} report(s); {len(targets)} scanned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`pipeline/__main__.py`:
```python
from .cli import main

raise SystemExit(main())
```

- [ ] **Step 4: 运行测试,确认通过**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: 全量测试**

Run: `pytest -v`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add pipeline/cli.py pipeline/__main__.py tests/test_cli.py
git commit -m "feat: CLI entrypoint with --file/--slug incremental run

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: 真实样本端到端冒烟测试

**Files:**
- Verify: `data/analyses/*.json`, `data/manifest.json`(产出物,提交作为冒烟证据)

**Interfaces:**
- Consumes: 全部前序任务;真实 `ARK_API_KEY` 与 vault `Clippings/`

> 本任务为集成验证(调用真实 LLM),非单元测试。目的是确认整条链路在真实数据上产出合法 Analysis。

- [ ] **Step 1: 配置环境变量**

在 shell 设置:`export ARK_API_KEY=<你的火山引擎 key>`(Windows PowerShell:`$env:ARK_API_KEY="<key>"`)。

- [ ] **Step 2: 挑 1 篇真实报告,单篇运行**

挑一篇较短的报告(如 `开源/APM因子模型的进阶版.md`)。运行:
```bash
python -m pipeline run --file "开源/APM因子模型的进阶版.md"
```
Expected: 输出 `[OK] 开源/APM因子模型的进阶版.md -> <slug>.json` 与 `analyzed 1 report(s)`;`data/analyses/<slug>.json` 生成。

- [ ] **Step 3: 校验产出 JSON 合法且字段齐全**

运行(Python 内联):
```bash
python -c "import json,glob; from pipeline.analyze.schema import Analysis; f=glob.glob('data/analyses/*.json')[0]; a=Analysis.model_validate_json(open(f,encoding='utf-8').read()); print('OK', a.slug, a.source.institution, a.detailed.construction.type, len(a.critical.weaknesses))"
```
Expected: 打印 `OK <slug> <机构> <construction.type> < weaknesses 数>` 且无异常。

- [ ] **Step 4: 人工抽检质量**

打开该 JSON,确认:`detailed.construction` 按 report 类型填了可复现细节(因子类有 `factor_definition`+`processing_pipeline`;模型类有 `model_architecture`+`inputs`+`outputs`+`training`);`critical` 四段非空;`source.original_url` 非空。若质量不达标,微调 `prompts.py`(Task 7)后重跑该篇。

- [ ] **Step 5: 再跑 2 篇不同类型(一篇因子类、一篇模型类)验证自适应**

```bash
python -m pipeline run --file "国信/【国信金工】动量类因子全解析.md"
python -m pipeline run --file "广发/【广发金工】AlphaForge：基于梯度下降的因子挖掘.md"
```
Expected: 两篇均 `[OK]`;`construction.type` 分别预期 `factor` 与 `model`(抽检确认)。

- [ ] **Step 6: 验证增量(重跑跳过未变动)**

```bash
python -m pipeline run --file "开源/APM因子模型的进阶版.md"
```
Expected: `analyzed 0 report(s)`(hash 未变,跳过)。

- [ ] **Step 7: 提交冒烟产出**

```bash
git add data/analyses/ data/manifest.json
git commit -m "test: M1 end-to-end smoke on real reports

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## M1 完成标准

- `pytest -v` 全绿(9 个测试文件)。
- `python -m pipeline run` 能扫描全量 `Clippings/*.md` 并增量分析;`--file`/`--slug` 能指定单篇。
- 至少 3 篇真实报告产出合法 Analysis JSON,`construction` 达到可复现级别,`critical` 四段非空。
- manifest 正确跳过未变动报告。

---

## 后续里程碑大纲(各自展开为独立计划)

> M1 完成并验收后,逐个里程碑写详细计划。下面是任务级大纲,非可执行步骤。

### M2 · 网站 MVP(可浏览的静态站)
- Task: Astro 项目脚手架(`site/`)+ Tailwind + 量化终端深色主题 + 字体(Plus Jakarta Sans / JetBrains Mono / Noto Sans SC,Google Fonts)。
- Task: content collection 读取 `data/analyses/*.json` -> 报告列表页(多维 facets 筛选 + 排序)。
- Task: 报告详情页(精简⇄详述切换、绩效指标卡、收益归因状态行、构造细节·可复现区块 + 流程图、批判性四卡、「查看原文」按钮、相关报告)。
- Task: Dashboard 首页(KPI、最新分析;M3 再接全景图)。
- Task: `pipeline build` 子命令调 `astro build` -> `dist/`。
- 验收:本地 `astro dev` 可浏览 M1 产出的报告,详情页可复现级构造 + 批判四卡正确渲染。

### M3 · 跨报告综合层
- Task: `pipeline/synthesize/registry.py` — 遍历单篇 `entities`+`construction` 聚类因子/方法(别名表 + LLM 辅助近义合并,人工确认)。
- Task: `landscape.py` — 拥挤度统计、`matrix_family_x_institution`、研究空白与差异化机会(带 score + 可借鉴报告)、同主题对比。
- Task: `synthesize.py` 编排 + `cli.py` 接 `synthesize` 子命令(单篇变动后全量重算本层)。
- Task: 网站新增「因子·方法注册表」「研究全景图(热力图 + 机会卡,可切换 方法×频率 / 家族×资产)」「同主题对比」页(React 岛屿 + ECharts)。
- 验收:全景图正确反映拥挤/空白,机会卡 ≥10 条。

### M4 · PDF 解析 + 全量增量
- Task: `pipeline/ingest/pdf.py` — PyMuPDF 抽文本 + pdfplumber 抽表格 + 启发式阅读顺序 + 图注提取 + PaddleOCR 兜底;`partial` 标记。
- Task: `cli.py` 扫描 `raw/pdfs/*.pdf` 并接入 manifest。
- Task: 全量跑 213 篇,产出 `data/analyses/` 全集 + manifest。
- 验收:PDF 报告解析入库,213 篇全量分析完成,增量重跑只处理新增/改动。

### M5 · 打磨
- Task: 全文搜索(客户端,如 Pagefind)。
- Task: 机构画像页、同主题对比页增强。
- Task: 可读性/性能/响应式优化;「关于」页(方法论、schema、如何编辑)。
- 验收:网站上乘,可读、美观、质量达标。

---

## 自检(Self-Review)

1. **Spec 覆盖**:M1 覆盖 spec §3(架构 ①② 层)、§4.1(单篇 schema)、§4.2(分类体系入 config)、§5.1/§5.3/§5.4/§5.5(MD 解析、归一化、manifest、一键运行 + 单篇指定)、§6(两段式 prompt、pydantic 校验、重试)、§9(ArkProvider)、§10(schema 校验/失败不阻塞/增量)。M2–M5 大纲覆盖 §7、§8、§5.2、§11 其余里程碑。✓
2. **Placeholder 扫描**:无 TBD/TODO;每步含完整代码或确切命令与预期输出。✓
3. **类型一致性**:`make_slug`、`NormalizedDoc`、`parse_markdown_file`、`Manifest.needs_analysis/update/hash_file`、`ArkProvider.chat`、`Analysis`、`Analyzer.analyze` 在各任务中签名一致;`SCHEMA_VERSION="1.0"` 在 manifest.py 与 cli.py 复用。✓
4. **一处注意**:`cli.py` 用 `from .ingest.manifest import Manifest, SCHEMA_VERSION` 复用常量,与 Task 4 定义一致;`Analyzer.__init__` 签名 `(provider, taxonomy, model="GLM-5.2")` 在 Task 8 定义、Task 9 调用一致。✓
