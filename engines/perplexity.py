"""Adapter for the Perplexity chat completions API.

Fresh context: one user message per call, no earlier messages. The
declared location is passed through web_search_options.user_location when
location_method is 'setting'. Cited sources come from search_results, or
from citations when search_results is absent.
"""

from engines import Adapter, EngineResponse, finish, post_json

URL = "https://api.perplexity.ai/chat/completions"


class PerplexityAdapter(Adapter):
    supports_location_setting = True
    key_env_default = "PERPLEXITY_API_KEY"

    @classmethod
    def validate_engine(cls, engine_cfg):
        return [] if engine_cfg.get("model") else ["model is required"]

    def call(self, request):
        body = {"model": self.cfg["model"],
                "messages": [{"role": "user", "content": request.prompt_text}]}
        if request.location_method == "setting":
            loc = {}
            for key in ("country", "region", "city"):
                if request.location.get(key):
                    loc[key] = request.location[key]
            body["web_search_options"] = {"user_location": loc}
        summary = {k: v for k, v in body.items() if k != "messages"}
        status, data, err, limited = post_json(
            self.options.get("url", URL),
            {"Authorization": "Bearer " + self.api_key()}, body, request.timeout)
        if status != "ok":
            return EngineResponse(status, error=err, rate_limited=limited, request_summary=summary)
        choices = data.get("choices") or []
        text = ""
        if choices:
            text = ((choices[0].get("message") or {}).get("content")) or ""
        sources = [{"url": r["url"], "title": r.get("title")}
                   for r in data.get("search_results") or [] if r.get("url")]
        if not sources:
            sources = [{"url": u} for u in data.get("citations") or [] if isinstance(u, str)]
        return finish("ok", text, sources, search_indicated=bool(sources) or None,
                      served_model=data.get("model"), request_summary=summary)
