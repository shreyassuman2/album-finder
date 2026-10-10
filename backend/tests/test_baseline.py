import eval.baseline as baseline
from app.engine.resolve import ResolvedAlbum


def album(artist, title):
    # Titles containing "Live" resolve as live albums, which aren't studio albums.
    secondary = ["Live"] if "Live" in title else []
    return ResolvedAlbum(f"id-{artist}-{title}", title, artist, "2020", "Album", secondary)


class FakeLastFm:
    SIMILAR = {"A": ["X", "Y"], "B": ["A", "Z"]}  # B lists input artist A, which must be skipped
    TOP = {"X": ["X Live", "X Studio"], "Y": ["Y1"], "Z": ["Z1"]}

    def similar_artists(self, artist, limit):
        return [(name, 1.0) for name in self.SIMILAR[artist]]

    def artist_top_albums(self, artist, limit):
        return self.TOP[artist]


def test_baseline_round_robin_skips_inputs_and_non_studio(monkeypatch):
    monkeypatch.setattr(baseline, "resolve_album", lambda mb, artist, title: album(artist, title))
    inputs = [album("A", "a"), album("B", "b")]
    picks = baseline.similar_artists_baseline(FakeLastFm(), None, inputs, n=20)
    # Rank 1 of each input (X; A is skipped), then rank 2 (Y, Z). X's live album is skipped.
    assert [p.title for p in picks] == ["X Studio", "Y1", "Z1"]
    assert [p.title for p in baseline.similar_artists_baseline(FakeLastFm(), None, inputs, n=2)] == ["X Studio", "Y1"]
