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
    # Second analysis with different classifications to create coverage gaps
    b = {
        "schema_version": "1.0", "slug": "def", "status": "ok",
        "source": {"title": "基本面价值研究", "institution": "中信", "authors": [], "published": None, "source_type": "wechat", "original_url": None, "local_path": "", "ingested_at": "2026-01-02"},
        "classification": {"research_type": ["基本面"], "factor_family": ["动量"], "asset_class": ["A股"], "method": ["机器学习"], "data_frequency": ["月频"]},
        "ratings": {"quality": 3, "novelty": 3, "reusability": 3},
        "concise": {"one_liner": "x2", "key_result": "y2"},
        "detailed": {"core_content": "c2", "economic_logic": "e2", "construction": {"type": "factor"}, "excess_return_logic": "ex2", "performance": {"metrics": []}, "attribution": {"done": False, "summary": "未做"}, "novelty_assessment": {"type": "改进", "summary": "s2"}},
        "critical": {"weaknesses": ["w2"], "improvement_ideas": [{"idea": "改进2", "based_on": "x2", "expected_gain": "y2"}]},
        "entities": [],
        "model_used": "GLM-5.2", "confidence": "medium",
    }
    (d / "def.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
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