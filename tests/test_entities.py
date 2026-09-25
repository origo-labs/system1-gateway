from system1_gateway.gateway import extract_entities


def test_extracts_common_operational_entities() -> None:
    entities = extract_entities("INC-42 for alice@example.com: freezer is 9 C and charge is €49.00")
    assert entities == {
        "email": "alice@example.com",
        "ticket_id": "INC-42",
        "amount": "€49.00",
        "temperature": "9 C",
    }
