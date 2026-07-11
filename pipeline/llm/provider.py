import os


class ArkProvider:
    def __init__(self, model: str, api_key=None, client=None):
        self.model = model
        if client is not None:
            self._client = client
        else:
            from volcenginesdkarkruntime import Ark  # lazy: real SDK only needed for live calls
            self._client = Ark(api_key=api_key or os.environ.get("ARK_API_KEY"))

    def chat(self, messages, **kw) -> str:
        resp = self._client.chat.completions.create(model=self.model, messages=messages, **kw)
        return resp.choices[0].message.content
