from app.engine.profile import clean_tags


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
