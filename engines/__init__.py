"""Engine adapters. Each adapter is a small file with one class.

An adapter sends one prompt in a fresh context (a single turn, no earlier
messages) and returns an EngineResponse. It never retries and never edits
an answer: the runner owns retries and storage.
"""

import importlib
import json
import socket
import urllib.error
import urllib.request

ADAPTERS = {
    "fake": "engines.fake:FakeAdapter",
    "openai_responses": "engines.openai_responses:OpenAIResponsesAdapter",
    "perplexity": "engines.perplexity:PerplexityAdapter",
}


class LocationSettingUnavailable(RuntimeError):
    """Raised when an engine no longer accepts the location setting.

    The runner stops that engine and records a deviation. It never switches
    silently to stating the location in the prompt.
    """


class EngineResponse:
    def __init__(self, status, text="", sources=None, search_indicated=None,
                 served_model=None, error=None, rate_limited=False,
                 sponsored=None, request_summary=None):
        self.status = status            # ok, refused, empty, error or timeout
        self.text = text or ""
        self.sources = sources or []    # list of {"url": ..., "title": ...}
        self.search_indicated = search_indicated
        self.served_model = served_model
        self.error = error
        self.rate_limited = rate_limited
        self.sponsored = sponsored or []  # engine-marked sponsored blocks, kept out of the text
        self.request_summary = request_summary or {}


class EngineRequest:
    def __init__(self, prompt_id, prompt_text, location, location_method,
                 run_number, attempt, timeout):
        self.prompt_id = prompt_id
        self.prompt_text = prompt_text   # exact text to send, location sentence included if any
        self.location = location         # dict: label, country, region, city
        self.location_method = location_method
        self.run_number = run_number
        self.attempt = attempt
        self.timeout = timeout


class Adapter:
    supports_location_setting = False
    key_env_default = None

    def __init__(self, engine_cfg, keys, base_dir="."):
        self.cfg = engine_cfg
        self.options = engine_cfg.get("options") or {}
        self.keys = keys
        self.base_dir = base_dir

    @classmethod
    def validate_engine(cls, engine_cfg):
        return []

    def api_key(self):
        env = self.cfg.get("key_env") or self.key_env_default
        key = self.keys.get(env) if env else None
        if not key:
            raise RuntimeError("no API key: set %s in the keys file or the environment" % env)
        return key

    def call(self, request):
        raise NotImplementedError


def finish(status, text, sources, **kw):
    """Map a parsed answer to a status: an empty body is a technical failure."""
    if status == "ok" and not (text or "").strip():
        return EngineResponse("empty", text, sources, error="empty body", **kw)
    return EngineResponse(status, text, sources, **kw)


def post_json(url, headers, body, timeout):
    """POST a JSON body. Returns (status, parsed_json_or_None, error_text, rate_limited)."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:500].decode("utf-8", "replace") if exc.fp else ""
        return "error", None, "HTTP %d %s" % (exc.code, detail), exc.code == 429
    except (socket.timeout, TimeoutError):
        return "timeout", None, "no response within %s seconds" % timeout, False
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            return "timeout", None, "no response within %s seconds" % timeout, False
        return "error", None, "connection failed: %s" % exc.reason, False
    if not raw or not raw.strip():
        return "empty", None, "empty body", False
    try:
        return "ok", json.loads(raw.decode("utf-8")), None, False
    except ValueError:
        return "error", None, "response was not JSON", False


def get_adapter_class(name):
    if name not in ADAPTERS:
        raise KeyError("unknown adapter %r (known: %s)" % (name, ", ".join(sorted(ADAPTERS))))
    module_name, cls_name = ADAPTERS[name].split(":")
    return getattr(importlib.import_module(module_name), cls_name)


def make_adapter(engine_cfg, keys, base_dir="."):
    return get_adapter_class(engine_cfg["adapter"])(engine_cfg, keys, base_dir)
