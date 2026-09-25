import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from system1_gateway.http import Handler


def test_http_health_and_decide() -> None:
    Handler.gateway = None
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port)
    connection.request("GET", "/health")
    response = connection.getresponse()
    assert response.status == 200
    health = json.loads(response.read())
    assert health["ready"] is True
    connection.request("POST", "/decide", body=json.dumps({"text": "My card was charged twice"}),
                       headers={"Content-Type": "application/json"})
    response = connection.getresponse()
    payload = json.loads(response.read())
    assert response.status == 200
    assert payload["decision"]["intent"] == "billing_duplicate_charge"
    server.shutdown()
    server.server_close()
