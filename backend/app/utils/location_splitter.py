"""Location splitter — bypass LinkedIn's 1000-result cap per search.

LinkedIn caps a single search at 1000 hits. One "USA Remote" search hits
that ceiling fast; instead we fan out into several per-metro searches.
Each search produces its own 1000-cap slice, so 5 splits ≈ 5000 jobs
achievable for the same keywords.
"""
from dataclasses import dataclass

REGION_SPLITS: dict[str, list[str]] = {
    "usa": ["San Francisco", "New York", "Austin", "Seattle", "Remote (USA)"],
    "us": ["San Francisco", "New York", "Austin", "Seattle", "Remote (USA)"],
    "united states": ["San Francisco", "New York", "Austin", "Seattle", "Remote (USA)"],
    "europe": ["London", "Berlin", "Amsterdam", "Dublin", "Remote (Europe)"],
    "eu": ["London", "Berlin", "Amsterdam", "Dublin", "Remote (Europe)"],
    "uk": ["London", "Manchester", "Edinburgh", "Remote (UK)"],
    "australia": ["Sydney", "Melbourne", "Brisbane", "Remote (Australia)"],
    "au": ["Sydney", "Melbourne", "Brisbane", "Remote (Australia)"],
}


@dataclass(frozen=True)
class LocationVariant:
    location: str
    is_remote_variant: bool


def generate_location_variants(target_regions: list[str] | None) -> list[LocationVariant]:
    """Expand high-level regions into per-city variants.

    Unknown/specific locations (e.g. "Jakarta") pass through unchanged as
    a single variant. Empty input yields a single Remote-anywhere variant.
    """
    if not target_regions:
        return [LocationVariant(location="Remote", is_remote_variant=True)]

    seen: set[str] = set()
    out: list[LocationVariant] = []
    for raw in target_regions:
        key = raw.strip().lower()
        splits = REGION_SPLITS.get(key)
        if splits:
            for city in splits:
                if city not in seen:
                    seen.add(city)
                    out.append(
                        LocationVariant(
                            location=city,
                            is_remote_variant="remote" in city.lower(),
                        )
                    )
        else:
            # Pass through literal location (e.g. "Jakarta", "Singapore")
            if raw not in seen:
                seen.add(raw)
                out.append(
                    LocationVariant(
                        location=raw,
                        is_remote_variant="remote" in raw.lower(),
                    )
                )
    return out
