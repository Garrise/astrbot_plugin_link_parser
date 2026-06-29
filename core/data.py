from dataclasses import dataclass, field

@dataclass(repr=False, slots=True)
class ParseResult:
    image_url: str
    description: str
    resource_id: str | None = None