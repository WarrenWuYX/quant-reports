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