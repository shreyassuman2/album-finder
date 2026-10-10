from app.engine.profile import build_profile, clean_tags


def test_clean_tags():
    raw = [
        ("Shoegaze", 100),
        ("Dream Pop", 80),
        ("dream  pop", 90),  # duplicate after normalizing; keep the higher count
        ("seen live", 70),  # stop tag
        ("Slowdive", 60),  # the artist's own name
        ("ambient", 2),  # too weak
    ]
    assert clean_tags(raw, artist_name="Slowdive") == [("shoegaze", 100), ("dream pop", 90)]


def test_exact_years_dropped_but_decades_kept():
    raw = [("1993", 90), ("best of 2010", 50), ("90s", 40), ("1990s", 30), ("2010s", 20)]
    assert clean_tags(raw) == [("90s", 40), ("1990s", 30), ("2010s", 20)]


def test_build_profile_weights_and_core():
    profile = build_profile([
        [("shoegaze", 100), ("dream pop", 50)],
        [("shoegaze", 100), ("noise pop", 30)],
        [("dream pop", 100), ("shoegaze", 10)],
        [("post-rock", 100)],
    ])
    assert profile.weights == {"shoegaze": 3, "dream pop": 2, "noise pop": 1, "post-rock": 1}
    assert profile.core == ["shoegaze", "dream pop"]
    # post-rock beats noise pop on strength (1.0 vs 0.3) as a tie-breaker
    assert profile.strongest(3) == ["shoegaze", "dream pop", "post-rock"]


def test_hyphen_variants_merge_and_bare_numbers_dropped():
    raw = [("hip-hop", 80), ("Hip Hop", 100), ("9", 60), ("post-rock", 50)]
    assert clean_tags(raw) == [("hip hop", 100), ("post rock", 50)]
