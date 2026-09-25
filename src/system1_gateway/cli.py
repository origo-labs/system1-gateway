import argparse
from pathlib import Path

from .models import GatewayRequest
from .gateway import LocalGateway
from .config import GatewayConfig
from .stream import baseline_envelope


def main() -> None:
    parser = argparse.ArgumentParser(description="Local System-1 gateway")
    parser.add_argument("--text", required=True)
    parser.add_argument("--model", nargs="?", const="fastino/gliner2.5-small-v1", help="use local GLiNER2.5, optionally naming a checkpoint")
    parser.add_argument("--config", type=Path, help="path to a domain configuration JSON")
    args = parser.parse_args()
    request = GatewayRequest(text=args.text)
    if args.model:
        config = GatewayConfig.load(args.config) if args.config else None
        envelope = LocalGateway(model_name=args.model, config=config).decide_request(request)
    else:
        envelope = baseline_envelope(request)
    print(envelope.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
