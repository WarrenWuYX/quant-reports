import os


class ArkProvider:
    def __init__(self, model: str, api_key=None, client=None):
        self.model = model
        self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        if client is not None:
            self._client = client
        else:
            key = api_key or os.environ.get("ARK_API_KEY")
            if not key:
                raise ValueError("ARK_API_KEY is required when Ark is the active LLM provider")
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
        usage = getattr(resp, "usage", None)
        self.last_usage = {
            "prompt_tokens": self._usage_value(usage, "prompt_tokens"),
            "completion_tokens": self._usage_value(usage, "completion_tokens"),
            "total_tokens": self._usage_value(usage, "total_tokens"),
        }
        for key, value in self.last_usage.items():
            self.usage_totals[key] += value
        return resp.choices[0].message.content

    @staticmethod
    def _usage_value(usage, key: str) -> int:
        if usage is None:
            return 0
        if isinstance(usage, dict):
            return int(usage.get(key, 0) or 0)
        return int(getattr(usage, key, 0) or 0)
