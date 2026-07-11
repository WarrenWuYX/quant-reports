from pipeline.llm.provider import ArkProvider


class _FakeResp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


class _FakeCompletions:
    def __init__(self, content, calls):
        self._content = content
        self._calls = calls

    def create(self, **kw):
        self._calls.append(kw)
        return _FakeResp(self._content)


class _FakeChat:
    def __init__(self, content, calls):
        self.completions = _FakeCompletions(content, calls)


class _FakeClient:
    def __init__(self, content="ok"):
        self.calls = []
        self.chat = _FakeChat(content, self.calls)


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
