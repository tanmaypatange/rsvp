"""Adapter for an OpenAI Responses API model with the web search tool.

Fresh context: every call is a new response with no previous_response_id
and store set to false. The declared location is passed through the web
search tool's user_location setting when location_method is 'setting'.
Cited sources are the url_citation annotations shown with the answer.
"""

from engines import Adapter, EngineResponse, finish, post_json, LocationSettingUnavailable

URL = "https://api.openai.com/v1/responses"


class OpenAIResponsesAdapter(Adapter):
    supports_location_setting = True
    key_env_default = "OPENAI_API_KEY"

    @classmethod
    def validate_engine(cls, engine_cfg):
        return [] if engine_cfg.get("model") else ["model is required"]

    def call(self, request):
        tool = {"type": self.options.get("tool_type", "web_search")}
        if request.location_method == "setting":
            loc = {"type": "approximate"}
            for key in ("country", "region", "city", "timezone"):
                if request.location.get(key):
                    loc[key] = request.location[key]
            tool["user_location"] = loc
        body = {"model": self.cfg["model"], "input": request.prompt_text, "store": False}
        if self.cfg.get("mode", "").startswith("search-on"):
            body["tools"] = [tool]
        summary = {k: v for k, v in body.items() if k != "input"}
        status, data, err, limited = post_json(
            self.options.get("url", URL),
            {"Authorization": "Bearer " + self.api_key()}, body, request.timeout)
        if status != "ok":
            if status == "error" and err and "user_location" in err:
                raise LocationSettingUnavailable(err)
            return EngineResponse(status, error=err, rate_limited=limited, request_summary=summary)
        text_parts, sources, refused, searched = [], [], False, False
        for item in data.get("output") or []:
            if item.get("type") == "web_search_call":
                searched = True
            if item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if part.get("type") == "refusal":
                    refused = True
                    text_parts.append(part.get("refusal") or "")
                if part.get("type") == "output_text":
                    text_parts.append(part.get("text") or "")
                    for ann in part.get("annotations") or []:
                        if ann.get("type") == "url_citation" and ann.get("url"):
                            sources.append({"url": ann["url"], "title": ann.get("title")})
        return finish("refused" if refused else "ok", "\n".join(text_parts), sources,
                      search_indicated=searched, served_model=data.get("model"),
                      request_summary=summary)
