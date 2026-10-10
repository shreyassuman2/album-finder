import pytest

from app.engine.resolve import parse_input, pick_best, similar


def rg(id, score, primary="Album", secondary=(), title="OK Computer", date="1997-05-21", artist="Radiohead"):
    return {
        "id": id,
        "score": score,
        "title": title,
        "primary-type": primary,
        "secondary-types": list(secondary),
        "first-release-date": date,
        "artist-credit": [{"name": artist}],
    }


def test_parse_input():
    assert parse_input("  Radiohead  -  OK Computer ") == ("Radiohead", "OK Computer")
    assert parse_input("Sigur Rós - ( )") == ("Sigur Rós", "( )")
    assert parse_input("A - B - C") == ("A", "B - C")


def test_self_titled_becomes_artist_name():
    assert parse_input("Playboi Carti - Self Titled") == ("Playboi Carti", "Playboi Carti")
    assert parse_input("Weezer - s/t") == ("Weezer", "Weezer")


@pytest.mark.parametrize("bad", ["Radiohead OK Computer", " - OK Computer", "Radiohead - "])
def test_parse_input_rejects_bad_format(bad):
    with pytest.raises(ValueError):
        parse_input(bad)


def test_similar_names():
    assert similar("Playboy Carti", "Playboi Carti")  # typo
    assert similar("Simon and Garfunkel", "Simon & Garfunkel")
    assert similar("( )", "( )")
    assert not similar("Playboy Carti", "Playboy the Beast")
    assert not similar("Self Titled", "Self Made Self Paid")


def test_prefers_studio_album_over_live_with_similar_score():
    results = [rg("live", 100, secondary=["Live"]), rg("studio", 95)]
    assert pick_best(results, "Radiohead", "OK Computer").mbid == "studio"


def test_does_not_prefer_a_much_worse_studio_match():
    results = [rg("ep", 100, primary="EP"), rg("other", 82)]
    assert pick_best(results, "Radiohead", "OK Computer").mbid == "ep"


def test_top_result_rejected_when_names_dont_match():
    # The real bug: a fuzzy search's top result scores 100 even when it's wrong.
    wrong = rg("x", 100, title="Self Made Self Paid", artist="Playboy the Beast")
    assert pick_best([wrong], "Playboy Carti", "Playboy Carti") is None


def test_typo_still_matches():
    right = rg("pc", 100, title="Playboi Carti", artist="Playboi Carti", secondary=["Mixtape/Street"])
    assert pick_best([right], "Playboy Carti", "Playboy Carti").mbid == "pc"


def test_empty_results():
    assert pick_best([], "Radiohead", "OK Computer") is None


def test_fields_and_joined_artist_credit():
    r = rg("sg", 100, title="Bridge over Troubled Water", date="1970")
    r["artist-credit"] = [{"name": "Simon", "joinphrase": " & "}, {"name": "Garfunkel"}]
    album = pick_best([r], "Simon & Garfunkel", "Bridge over Troubled Water")
    assert (album.artist, album.title, album.year) == ("Simon & Garfunkel", "Bridge over Troubled Water", "1970")
