from app.engine.candidates import clean_title, gather_candidates
from app.engine.profile import build_profile
from app.engine.resolve import ResolvedAlbum


def test_clean_title():
    assert clean_title("Souvlaki (Deluxe Edition)") == "Souvlaki"
    assert clean_title("Loveless [2021 Remaster]") == "Loveless"
    assert clean_title("( )") == "( )"  # real title, not an edition suffix


class FakeLastFm:
    def similar_artists(self, artist, limit):
        return {"Slowdive": [("Ride", 1.0), ("my bloody valentine", 0.9)],
                "my bloody valentine": [("Ride", 1.0)]}.get(artist, [])

    def artist_top_albums(self, artist, limit):
        return {"Ride": ["Nowhere", "Nowhere (Deluxe Edition)"]}.get(artist, [])

    def tag_top_albums(self, tag, limit):
        if tag != "shoegaze":
            return []
        return [("Slowdive", "Pygmalion"), ("Lush", "Spooky"), ("Ride", "Going Blank Again")]


def _album(artist):
    return ResolvedAlbum(mbid=artist, title="t", artist=artist, year=None, primary_type="Album", secondary_types=[])


def test_gather_candidates():
    inputs = [_album("Slowdive"), _album("my bloody valentine")]
    profile = build_profile([[("shoegaze", 100)], [("shoegaze", 100)]])
    found = {(c.artist, c.title): c for c in gather_candidates(FakeLastFm(), inputs, profile)}

    # input artists' own albums are excluded, whichever source suggested them
    assert set(found) == {("Ride", "Nowhere"), ("Ride", "Going Blank Again"), ("Lush", "Spooky")}
    # the deluxe edition merged into the original, and both inputs pointed to Ride
    assert found[("Ride", "Nowhere")].pointed_by == {"Slowdive", "my bloody valentine"}
    assert found[("Lush", "Spooky")].from_tags == {"shoegaze"}
    assert found[("Lush", "Spooky")].pointed_by == set()  # Lush isn't on any similar list
    # came in via the tag search, but Ride is a similar artist, so it still gets the credit
    assert found[("Ride", "Going Blank Again")].pointed_by == {"Slowdive", "my bloody valentine"}
