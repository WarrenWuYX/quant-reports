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

    class _FakeProvider:
        def __init__(self, model, api_key=None, client=None):
            self.model = model

        def chat(self, messages, **kw):
            return "{}"

    monkeypatch.setattr("pipeline.cli.ArkProvider", _FakeProvider)

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

    code = main(["run", "--no-build"])
    assert code == 0
    outs = list((tmp_path / "data" / "analyses").glob("*.json"))
    assert len(outs) == 1
    assert (tmp_path / "data" / "manifest.json").exists()
