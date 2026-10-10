import pytest

from app.engine.resolve import parse_input, pick_best


def rg(id, score, primary="Album", secondary=(), title="OK Computer", date="1997-05-21"):
    return {
        "id": id,
        "score": score,
        "title": title,
        "primary-type": primary,
        "secondary-types": list(secondary),
        "first-release-date": date,
        "artist-credit": [{"name": "Radiohead"}],
    }


def test_parse_input():
    assert parse_input("  Radiohead  -  OK Computer ") == ("Radiohead", "OK Computer")
    assert parse_input("Sigur Rós - ( )") == ("Sigur Rós", "( )")
    assert parse_input("A - B - C") == ("A", "B - C")


@pytest.mark.parametrize("bad", ["Radiohead OK Computer", " - OK Computer", "Radiohead - "])
def test_parse_input_rejects_bad_format(bad):
    with pytest.raises(ValueError):
        parse_input(bad)


def test_prefers_studio_album_over_live_with_similar_score():
    results = [rg("live", 100, secondary=["Live"]), rg("studio", 95)]
    assert pick_best(results).mbid == "studio"


def test_does_not_prefer_a_much_worse_studio_match():
    results = [rg("ep", 100, primary="EP"), rg("unrelated", 82)]
    assert pick_best(results).mbid == "ep"


def test_low_scores_are_rejected():
    assert pick_best([rg("x", 60)]) is None
    assert pick_best([]) is None


def test_fields_and_joined_artist_credit():
    r = rg("sg", 100, title="Bridge over Troubled Water", date="1970")
    r["artist-credit"] = [{"name": "Simon", "joinphrase": " & "}, {"name": "Garfunkel"}]
    album = pick_best([r])
    assert (album.artist, album.title, album.year) == ("Simon & Garfunkel", "Bridge over Troubled Water", "1970")
