#!/usr/bin/env python3
"""Route model calls across free engines, falling over as quotas run out.

An engine is one (provider, model) pair. Each role ("author", "solver") has an
ordered list of engines in tools/engines.json. A call goes to the first engine
in the role's list that is configured, not exhausted, and not excluded:

- daily quota reached (429 that says so)  -> engine marked exhausted for the
  rest of the run; the call moves to the next engine
- per-minute 429                          -> wait the server's stated delay
- 503 / timeout                           -> brief retries, then next engine
- model not found / other 4xx             -> engine disabled for the run

Limits are honored, never evaded: one key per provider, no key rotation.
Keys are sent only in headers, never in URLs.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

CALL_TIMEOUT = 240
MAX_RETRIES = 3
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines.json")


class QuotaExhausted(Exception):
    """The engine's quota for today is used up."""


class Unavailable(Exception):
    """503 / timeout: the engine was busy. Not a judgment on content."""


class Disabled(Exception):
    """The engine cannot serve this run (model missing, bad request...)."""


def _post(url, payload, headers, timeout=CALL_TIMEOUT):
    """POST JSON; returns (status, body_text, response_headers)."""
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), resp.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), e.headers
    except (TimeoutError, urllib.error.URLError) as e:
        return None, str(e), {}


def _get(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _parse_json_text(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return json.loads(text)


class Engine:
    def __init__(self, provider, model, spec, key):
        self.provider, self.model, self.spec, self.key = provider, model, spec, key
        self.label = f"{provider}:{model}"
        self.state = "ready"          # ready | exhausted | disabled
        self.note = ""
        self.calls = self.tokens = 0

    # -- wire formats -------------------------------------------------------
    def _request(self, prompt):
        base = self.spec["base"]
        if self.spec["kind"] == "gemini":
            return (f"{base}/models/{self.model}:generateContent",
                    {"contents": [{"parts": [{"text": prompt}]}],
                     "generationConfig": {"temperature": 0.7,
                                          "responseMimeType": "application/json"}},
                    {"x-goog-api-key": self.key, "Content-Type": "application/json"})
        return (f"{base}/chat/completions",
                {"model": self.model, "temperature": 0.7,
                 "messages": [{"role": "user", "content": prompt}],
                 "response_format": {"type": "json_object"}},
                {"Authorization": f"Bearer {self.key}",
                 "Content-Type": "application/json"})

    def _extract(self, data):
        if self.spec["kind"] == "gemini":
            cands = data.get("candidates") or []
            parts = (cands[0].get("content", {}).get("parts") if cands else None) or []
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            if not text.strip():
                reason = cands[0].get("finishReason") if cands else "no candidates"
                raise RuntimeError(f"{self.label} returned no text ({reason})")
            return text, data.get("usageMetadata", {}).get("totalTokenCount", 0)
        choices = data.get("choices") or []
        text = (choices[0].get("message", {}).get("content") if choices else "") or ""
        if not text.strip():
            raise RuntimeError(f"{self.label} returned no text")
        return text, (data.get("usage") or {}).get("total_tokens", 0)

    @staticmethod
    def _is_daily(body, retry_after):
        b = body.lower()
        return ("perday" in b.replace(" ", "") or "per day" in b
                or "requests per day" in b or "(rpd)" in b or "daily" in b
                or (retry_after is not None and retry_after > 600))

    @staticmethod
    def _retry_after(body, headers):
        m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', body)
        if m:
            return float(m.group(1))
        h = (headers or {}).get("retry-after") if headers else None
        try:
            return float(h) if h is not None else None
        except ValueError:
            return None

    # -- one call -----------------------------------------------------------
    def call(self, prompt):
        url, payload, headers = self._request(prompt)
        for attempt in range(MAX_RETRIES + 1):
            status, body, rh = _post(url, payload, headers)
            if status == 200:
                break
            if status is None or status in (500, 502, 503, 504):
                if attempt == MAX_RETRIES:
                    raise Unavailable(f"{self.label}: {status or body[:120]}")
                wait = 20 * (attempt + 1)
                print(f"   {self.label} unavailable ({status or 'timeout'}); "
                      f"retrying in {wait}s")
                time.sleep(wait)
                continue
            if status == 429:
                ra = self._retry_after(body, rh)
                if self._is_daily(body, ra):
                    raise QuotaExhausted(f"{self.label}: daily quota reached")
                if attempt == MAX_RETRIES:
                    raise QuotaExhausted(f"{self.label}: still rate-limited "
                                         f"after {MAX_RETRIES} waits")
                wait = (ra or 30 * (attempt + 1)) + 1
                print(f"   429 from {self.label}; waiting {wait:.0f}s as instructed")
                time.sleep(wait)
                continue
            raise Disabled(f"{self.label}: HTTP {status}: {body[:200]}")
        text, tokens = self._extract(json.loads(body))
        self.calls += 1
        self.tokens += tokens or 0
        return _parse_json_text(text)


class Router:
    def __init__(self, config_path=CONFIG, overrides=None, env=os.environ,
                 check_models=True):
        with open(config_path) as f:
            cfg = json.load(f)
        self.providers = cfg["providers"]
        self.engines = {}
        self.chains = {}
        for role in ("author", "solver"):
            chain = list(cfg.get(role, []))
            o = (overrides or {}).get(role)
            if o:
                o = o if ":" in o.split("/")[0] else f"gemini:{o}"
                chain = [o] + [c for c in chain if c != o]
            self.chains[role] = chain
        listed = {}
        for role, chain in self.chains.items():
            kept = []
            for label in chain:
                provider, model = label.split(":", 1)
                spec = self.providers.get(provider)
                key = env.get(spec["key_env"]) if spec else None
                if not key:
                    continue
                if check_models and spec["kind"] == "openai":
                    if provider not in listed:
                        listed[provider] = self._list_models(provider, spec, key)
                    if listed[provider] is not None and model not in listed[provider]:
                        print(f"   skipping {label}: not in provider's model list")
                        continue
                if label not in self.engines:
                    self.engines[label] = Engine(provider, model, spec, key)
                kept.append(label)
            self.chains[role] = kept

    @staticmethod
    def _list_models(provider, spec, key):
        try:
            data = _get(f"{spec['base']}/models",
                        {"Authorization": f"Bearer {key}"})
            return {m.get("id") for m in data.get("data", [])}
        except Exception as e:
            print(f"   could not list {provider} models ({e}); trying configured ids")
            return None

    def describe(self):
        return {role: chain for role, chain in self.chains.items()}

    def call(self, role, prompt, avoid=()):
        """Returns (parsed_json, engine_label). Falls over down the chain."""
        tried_any = False
        for label in self.chains[role]:
            eng = self.engines[label]
            if eng.state != "ready" or label in avoid:
                continue
            tried_any = True
            try:
                return eng.call(prompt), label
            except QuotaExhausted as e:
                eng.state, eng.note = "exhausted", str(e)
                print(f"   {label} exhausted; falling over")
            except Disabled as e:
                eng.state, eng.note = "disabled", str(e)
                print(f"   {label} disabled for this run: {e}")
            except Unavailable as e:
                eng.note = str(e)
                print(f"   {label} unavailable; trying next engine")
        live = [l for l in self.chains[role]
                if self.engines[l].state == "ready" and l not in avoid]
        if not live:
            raise QuotaExhausted(f"no {role} engine left "
                                 f"({'all exhausted or disabled' if tried_any or self.chains[role] else 'none configured'})")
        raise Unavailable(f"every {role} engine was busy")

    def report_lines(self):
        lines = ["| engine | roles | calls | tokens | state |",
                 "|---|---|---|---|---|"]
        for label, e in self.engines.items():
            roles = ", ".join(r for r, c in self.chains.items() if label in c)
            state = e.state + (f" ({e.note[:80]})" if e.note and e.state != "ready" else "")
            lines.append(f"| `{label}` | {roles} | {e.calls} | {e.tokens} | {state} |")
        return lines
