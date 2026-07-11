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