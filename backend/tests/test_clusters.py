from app.engine.clusters import cluster_inputs, cluster_note
from app.engine.resolve import ResolvedAlbum


def album(artist, title="t"):
    return ResolvedAlbum(mbid=artist, title=title, artist=artist, year=None, primary_type="Album", secondary_types=[])


INPUTS = [album("Kendrick Lamar"), album("Miles Davis"), album("Vince Staples"), album("John Coltrane"), album("Slowdive")]


def test_groups_by_shared_tag_words_and_similar_artists():
    tags = [
        [("conscious hip hop", 100)],
        [("cool jazz", 100)],
        [("west coast hip hop", 100)],  # shares "hip"/"hop" with Kendrick
        [("free improvisation", 100)],  # no shared words...
        [("shoegaze", 100)],
    ]
    similar = [set(), set(), set(), {"miles davis"}, set()]  # ...but Coltrane lists Miles Davis
    assert cluster_inputs(INPUTS, tags, similar) == [[0, 2], [1, 3], [4]]  # tie: Kendrick's group came first


def test_all_unrelated_gives_singletons():
    tags = [[("a", 1)], [("b", 1)], [("c", 1)], [("d", 1)], [("e", 1)]]
    assert cluster_inputs(INPUTS, tags, [set()] * 5) == [[0], [1], [2], [3], [4]]


def test_cluster_note():
    assert cluster_note([album("A", "DAMN."), album("B", "Big Fish Theory")]) == \
        "Your picks didn't share one sound, so these focus on DAMN. and Big Fish Theory."


def test_generic_words_and_decades_dont_link():
    tags = [[("pop rap", 100), ("90s", 50)], [("dream pop", 100), ("90s", 50)], [("x", 1)], [("y", 1)], [("z", 1)]]
    assert cluster_inputs(INPUTS, tags, [set()] * 5) == [[0], [1], [2], [3], [4]]
