"""Fuel type normalization mapping for all sources."""

FUEL_TYPE_MAP: dict[str, str] = {
    # Polish labels (OTOMOTO)
    "benzyna": "petrol",
    "diesel": "diesel",
    "elektryczny": "electric",
    "hybryda": "hybrid",
    "hybryda plug-in": "hybrid_plugin",
    "lpg": "lpg",
    "cng": "cng",
    "wodór": "hydrogen",
    # English labels
    "petrol": "petrol",
    "electric": "electric",
    "hybrid": "hybrid",
    "gasoline": "petrol",
}


def normalize_fuel_type(raw: str | None) -> str | None:
    if raw is None:
        return None
    return FUEL_TYPE_MAP.get(raw.strip().lower(), raw.strip().lower())
