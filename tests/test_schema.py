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
    assert a.detailed.attribution.done is False
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