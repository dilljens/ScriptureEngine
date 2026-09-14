"""Shared fakes for the chat endpoint tests.

FakeResp / _FakeStreamCtx / FakeHttpClient were copy-pasted across
chat_reliability_test.py, chat_speedup_test.py, and
chat_background_jobs_test.py. One implementation lives here now.

FakeHttpClient records every streamed payload (reliability tests assert on
max_tokens bumps) and raises RuntimeError when responses run dry instead of
an opaque IndexError.
"""


class FakeResp:
    """Minimal stand-in for the httpx stream response."""

    def __init__(self, lines, status_code=200):
        self.status_code = status_code
        self._lines = lines

    async def aread(self):
        return b""

    def aiter_lines(self):
        async def gen():
            for line in self._lines:
                yield line
        return gen()


class _FakeStreamCtx:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *exc):
        return False


class FakeHttpClient:
    """Replaces chat_routes._http_client for the final stream call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.streamed_payloads = []

    def stream(self, *args, **kwargs):
        if not self._responses:
            raise RuntimeError("No fake stream responses left")
        self.streamed_payloads.append(kwargs.get("json"))
        return _FakeStreamCtx(self._responses.pop(0))
