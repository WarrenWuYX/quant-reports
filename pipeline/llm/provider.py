import os


class ArkProvider:
    def __init__(self, model: str, api_key=None, client=None):
        self.model = model
        if client is not None:
            self._client = client
        else:
            key = api_key or os.environ.get("ARK_API_KEY")
            try:
                from volcenginesdkarkruntime import Ark
                self._client = Ark(api_key=key)
            except ImportError:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=key,
                    base_url="https://ark.cn-beijing.volces.com/api/v3",
                )

    def chat(self, messages, **kw) -> str:
        resp = self._client.chat.completions.create(model=self.model, messages=messages, **kw)
        return resp.choices[0].message.content
