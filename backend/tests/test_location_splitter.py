from app.utils.location_splitter import generate_location_variants


def test_usa_expands_to_five_metros():
    variants = generate_location_variants(["USA"])
    locs = [v.location for v in variants]
    assert "San Francisco" in locs
    assert "New York" in locs
    assert "Remote (USA)" in locs
    assert len(variants) == 5


def test_europe_expands_to_multiple_metros():
    variants = generate_location_variants(["Europe"])
    locs = [v.location for v in variants]
    assert "London" in locs
    assert "Berlin" in locs
    assert any(v.is_remote_variant for v in variants)


def test_case_insensitive_region_keys():
    upper = generate_location_variants(["USA"])
    lower = generate_location_variants(["usa"])
    mixed = generate_location_variants(["United States"])
    assert [v.location for v in upper] == [v.location for v in lower] == [v.location for v in mixed]


def test_unknown_location_passes_through():
    variants = generate_location_variants(["Jakarta"])
    assert len(variants) == 1
    assert variants[0].location == "Jakarta"


def test_empty_defaults_to_remote():
    assert generate_location_variants(None) == generate_location_variants([])
    out = generate_location_variants(None)
    assert out[0].location == "Remote"
    assert out[0].is_remote_variant is True


def test_dedupes_overlapping_regions():
    # USA + US produce the same splits — dedup.
    variants = generate_location_variants(["USA", "US"])
    assert len({v.location for v in variants}) == len(variants)


def test_remote_variant_flag_detection():
    variants = generate_location_variants(["USA"])
    remote = [v for v in variants if v.is_remote_variant]
    assert len(remote) == 1
    assert "remote" in remote[0].location.lower()
