"""A fake engine that returns canned answers from a JSON file. No network.

Used for the dry run and the tests. The canned file maps engine id, then
prompt id, to a list of answers; run number n uses entry (n - 1) modulo the
list length. An entry may carry fail_attempts and fail_status to make the
first attempts fail, which exercises the runner's retry rule.
"""

import json
import os

from engines import Adapter, EngineResponse, finish, LocationSettingUnavailable


class FakeAdapter(Adapter):
    supports_location_setting = True

    _cache = {}

    @classmethod
    def validate_engine(cls, engine_cfg):
        if not (engine_cfg.get("options") or {}).get("canned_file"):
            return ["the fake adapter needs options.canned_file"]
        return []

    def _canned(self):
        path = self.options["canned_file"]
        if not os.path.isabs(path):
            path = os.path.join(self.base_dir, path)
        if path not in self._cache:
            with open(path, "r", encoding="utf-8") as fh:
                FakeAdapter._cache[path] = json.load(fh)
        return self._cache[path]

    def call(self, request):
        if request.location_method == "setting" and self.options.get("drop_location_setting"):
            raise LocationSettingUnavailable("fake engine no longer accepts a location setting")
        answers = self._canned().get(self.cfg["id"], {}).get(request.prompt_id)
        if not answers:
            return EngineResponse("error", error="no canned answer for %s %s" % (self.cfg["id"], request.prompt_id))
        entry = answers[(request.run_number - 1) % len(answers)]
        summary = {"adapter": "fake", "model": self.cfg.get("model"),
                   "location_method": request.location_method}
        if request.attempt <= int(entry.get("fail_attempts", 0)):
            status = entry.get("fail_status", "error")
            return EngineResponse(status, error=entry.get("error", "canned %s" % status),
                                  rate_limited=bool(entry.get("rate_limited")),
                                  request_summary=summary)
        return finish(entry.get("status", "ok"), entry.get("text", ""),
                      [dict(s) for s in entry.get("sources", [])],
                      search_indicated=entry.get("search_indicated"),
                      served_model=entry.get("served_model", self.cfg.get("model")),
                      sponsored=entry.get("sponsored"),
                      request_summary=summary)
