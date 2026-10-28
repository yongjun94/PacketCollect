import base64
from datetime import datetime, timezone
import os
import time
import uuid
from mitmproxy import http


def stamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if value is not None else None


class CaptureAddon:
    def __init__(self, writer):
        self.writer = writer
        self.run_id = str(uuid.uuid4())
        self.paused = False
        self.active = {}

    def requestheaders(self, flow: http.HTTPFlow):
        if self.paused:
            # Paused traffic is forwarded but not buffered in RAM by the addon.
            flow.request.stream = True
            return
        self.active[flow.id] = {"flow": flow, "files": {}, "refs": {}, "error": None}
        self._stream(flow, flow.request, "request")
        self._emit(flow, "receiving")

    def responseheaders(self, flow):
        if flow.id in self.active:
            self._stream(flow, flow.response, "response")
        else:
            flow.response.stream = True

    def _stream(self, flow, message, side):
        state = self.active[flow.id]
        rel = f"bodies/{flow.id}.{side}.bin"
        f = open(self.writer.root / rel, "xb", buffering=0)
        state["files"][side] = f
        state["refs"][side] = {"path": rel, "size": 0, "complete": False}

        def stream(chunk):
            if chunk:
                try:
                    n = f.write(chunk)
                    if n != len(chunk):
                        raise OSError("Short body write")
                    state["refs"][side]["size"] += n
                except OSError as exc:
                    state["error"] = f"Body storage failed: {exc}"
                    # Fail closed on storage loss, never silently claim completeness.
                    raise
            return chunk
        message.stream = stream

    def request(self, flow):
        if flow.id in self.active:
            self._finish(flow, "request", True)
            self._emit(flow, "receiving")

    def response(self, flow):
        if flow.id in self.active:
            self._finish(flow, "response", True)
            self._emit(flow, "complete" if not self.active[flow.id]["error"] else "partial")
            self.active.pop(flow.id)

    def error(self, flow):
        if flow.id in self.active:
            self.active[flow.id]["error"] = str(flow.error)
            self._close(flow)
            self._emit(flow, "error")
            self.active.pop(flow.id)

    def _finish(self, flow, side, complete):
        state = self.active[flow.id]
        f = state["files"].pop(side, None)
        if f is not None:
            os.fsync(f.fileno())
            f.close()
            state["refs"][side]["complete"] = complete

    def _close(self, flow):
        for side in list(self.active[flow.id]["files"]):
            self._finish(flow, side, False)

    def done(self):
        for state in list(self.active.values()):
            flow = state["flow"]
            self._close(flow)
            self._emit(flow, "interrupted")
        self.active.clear()

    def _emit(self, flow, status):
        state = self.active[flow.id]

        def message(m, side):
            if m is None:
                return None
            result = {"version": m.http_version, "headers": [
                {"name": base64.b64encode(n).decode(), "value": base64.b64encode(v).decode()}
                for n, v in m.headers.fields], "body": dict(state["refs"].get(side, {})) or None}
            if side == "request":
                result.update(method=m.method, url=m.url)
            else:
                result.update(status=m.status_code, reason=m.reason)
            return result

        req, res = flow.request, flow.response
        end = (res.timestamp_end if res else None)
        timing = {}
        if req.timestamp_end is not None:
            timing['send'] = max(0, (req.timestamp_end-req.timestamp_start)*1000)
        if res and req.timestamp_end is not None:
            timing['wait'] = max(0, (res.timestamp_start-req.timestamp_end)*1000)
        if res and res.timestamp_end is not None:
            timing['receive'] = max(0, (res.timestamp_end-res.timestamp_start)*1000)
        self.writer.emit("session", session={
            "id": flow.id, "runId": self.run_id,
            "sourceDevice": str(flow.client_conn.peername[0]) if flow.client_conn.peername else "unknown",
            "startTime": stamp(req.timestamp_start), "endTime": stamp(end),
            "request": message(req, "request"), "response": message(res, "response"),
            "captureStatus": status, "error": state["error"], "timing": timing,
            "connection": {"peer": flow.client_conn.peername, "server": flow.server_conn.address},
            "tls": {"version": flow.client_conn.tls_version, "cipher": flow.client_conn.cipher,
                    "sni": flow.client_conn.sni}})
