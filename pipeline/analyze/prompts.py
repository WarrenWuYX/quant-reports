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