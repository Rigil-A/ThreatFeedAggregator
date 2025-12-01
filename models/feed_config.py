from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class FeedSettings:
    csv_indexes: List[int] = field(default_factory=list)
    csv_delimiter: str = ","
    exclude_regex: Optional[str] = None

@dataclass
class FeedConfigModel:
    name: str
    provider: Optional[str]
    url: str
    enabled: bool
    source_format: str  # "csv" | "freetext" | "misp"
    input_source: str = "network"
    settings: FeedSettings = field(default_factory=FeedSettings)
    tag_name: Optional[str] = None
