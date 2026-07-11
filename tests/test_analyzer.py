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