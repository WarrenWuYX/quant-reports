import json

from pipeline.publish import prepare_site_data


def test_prepare_site_data_syncs_and_removes_stale_files(tmp_path):
    analyses = tmp_path / "data" / "analyses"
    analyses.mkdir(parents=True)
    payload = {
        "slug": "report-a",
        "status": "ok",
        "source": {"title": "报告 A", "institution": "机构 A"},
        "classification": {
            "research_type": ["基本面"],
            "data_frequency": ["日频"],
            "factor_family": ["价值"],
            "asset_class": ["A股"],
            "method": ["统计线性"],
        },
        "entities": [{"name": "价值因子", "type": "factor"}],
    }
    (analyses / "report-a.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    content_dir = tmp_path / "site" / "src" / "content" / "analyses"
    content_dir.mkdir(parents=True)
    (content_dir / "stale.json").write_text("{}", encoding="utf-8")

    registry = tmp_path / "data" / "registry" / "entities.json"
    landscape = tmp_path / "data" / "landscape" / "coverage.json"
    stats = prepare_site_data(tmp_path, analyses, registry, landscape)

    assert stats == {"copied": 1, "removed": 1}
    assert (content_dir / "report-a.json").exists()
    assert not (content_dir / "stale.json").exists()
    assert (tmp_path / "site" / "src" / "data" / "entities.json").exists()
    assert (tmp_path / "site" / "src" / "data" / "coverage.json").exists()
