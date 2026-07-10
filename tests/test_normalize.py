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