from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class IntentConfig(BaseModel):
    name: str
    description: str = Field(min_length=1)
    route: str = Field(min_length=1)
    requires_approval: bool = False


class EntityConfig(BaseModel):
    name: str
    description: str = Field(min_length=1)
    pattern: str = Field(min_length=1)
    required_for: list[str] = Field(default_factory=list)


class GatewayConfig(BaseModel):
    schema_version: str = "system1.v1"
    confidence_threshold: float = Field(default=0.75, ge=0, le=1)
    intent_thresholds: dict[str, float] = Field(default_factory=dict)
    intents: list[IntentConfig] = Field(min_length=1)
    entities: list[EntityConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_intents(self) -> "GatewayConfig":
        names = [item.name for item in self.intents]
        if len(names) != len(set(names)):
            raise ValueError("intent names must be unique")
        if "unknown" not in names:
            raise ValueError("domain config must define an unknown intent")
        if any(not 0 <= value <= 1 for value in self.intent_thresholds.values()):
            raise ValueError("intent thresholds must be between 0 and 1")
        return self

    def threshold_for(self, intent: str) -> float:
        return self.intent_thresholds.get(intent, self.confidence_threshold)

    @classmethod
    def load(cls, path: Path) -> "GatewayConfig":
        return cls.model_validate_json(path.read_text())

    @classmethod
    def default(cls) -> "GatewayConfig":
        return cls.load(Path(__file__).with_name("default_config.json"))
