from pipeline.llm.provider import ArkProvider


class _FakeResp:
    def __init__(self, content, usage=None):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]
        self.usage = usage


class _FakeCompletions:
    def __init__(self, content, calls, usage=None):
        self._content = content
        self._calls = calls
        self._usage = usage

    def create(self, **kw):
        self._calls.append(kw)
        return _FakeResp(self._content, self._usage)


class _FakeChat:
    def __init__(self, content, calls, usage=None):
        self.completions = _FakeCompletions(content, calls, usage)


class _FakeClient:
    def __init__(self, content="ok", usage=None):
        self.calls = []
        self.chat = _FakeChat(content, self.calls, usage)


def test_chat_returns_content():
    p = ArkProvider(model="GLM-5.2", client=_FakeClient("hello"))
    assert p.chat([{"role": "user", "content": "hi"}]) == "hello"


def test_chat_passes_model_messages_and_kwargs():
    fake = _FakeClient("x")
    p = ArkProvider(model="GLM-5.2", client=fake)
    p.chat([{"role": "user", "content": "hi"}], response_format={"type": "json_object"})
    kw = fake.calls[0]
    assert kw["model"] == "GLM-5.2"
    assert kw["messages"] == [{"role": "user", "content": "hi"}]
    assert kw["response_format"] == {"type": "json_object"}


def test_chat_accumulates_usage():
    usage = type("Usage", (), {
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "total_tokens": 150,
    })()
    p = ArkProvider(model="GLM-5.2", client=_FakeClient("ok", usage=usage))
    p.chat([{"role": "user", "content": "hi"}])
    p.chat([{"role": "user", "content": "again"}])
    assert p.last_usage == {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
    assert p.usage_totals == {"prompt_tokens": 240, "completion_tokens": 60, "total_tokens": 300}
