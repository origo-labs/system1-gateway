def test_public_api_exports_core_types() -> None:
    from system1_gateway import GatewayConfig, GatewayRequest, LocalGateway

    assert GatewayConfig.default().schema_version == "system1.v1"
    assert GatewayRequest(text="hello").text == "hello"
    assert LocalGateway is not None
