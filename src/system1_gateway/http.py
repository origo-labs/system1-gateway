from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import GatewayConfig
from .gateway import LocalGateway
from .models import GatewayRequest
from .stream import baseline_envelope


class Handler(BaseHTTPRequestHandler):
    gateway: LocalGateway | None = None
    history: list[dict] = []

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in {"/", "/ui"}:
            body = (Path(__file__).with_name("ui").joinpath("index.html").read_bytes())
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path == "/decisions":
            self._send(200, {"decisions": self.history[-100:]})
            return
        if self.path == "/health":
            ready = self.gateway is None or self.gateway.ready
            self._send(200 if ready else 503, {"status": "ok" if ready else "warming",
                             "model_loaded": self.gateway is not None, "ready": ready })
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/decide":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = GatewayRequest.model_validate(json.loads(self.rfile.read(length)))
            envelope = self.gateway.decide_request(request) if self.gateway else baseline_envelope(request)
            payload = envelope.model_dump(mode="json")
            self.history.append(payload)
            del self.history[:-100]
            self._send(200, payload)
        except Exception as exc:
            self._send(400, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Local System-1 HTTP gateway")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", nargs="?", const="fastino/gliner2.5-small-v1", help="use local GLiNER2.5, optionally naming a checkpoint")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--warmup", action="store_true", help="warm local model before serving")
    args = parser.parse_args()
    config = GatewayConfig.load(args.config) if args.config else None
    Handler.gateway = LocalGateway(model_name=args.model, config=config) if args.model else None
    if Handler.gateway and args.warmup:
        Handler.gateway.warmup()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"system1 gateway listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
