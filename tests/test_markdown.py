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