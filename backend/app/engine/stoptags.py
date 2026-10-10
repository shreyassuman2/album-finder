"""Last.fm tags that say something about the listener, not the music.

Compared after lowercasing and collapsing whitespace. Add to this as you spot
junk in real output.
"""

STOP_TAGS = frozenset({
    # ownership / listening habits
    "seen live", "albums i own", "albums i have", "owned", "vinyl", "cd",
    "my albums", "my collection", "in my collection", "spotify", "to listen",
    "want to listen", "check out", "listened", "heard",
    # favorites and ratings
    "favorite", "favourite", "favorites", "favourites", "favorite albums",
    "favourite albums", "my favorite", "my favourite", "best albums ever",
    "albums of the year", "love", "loved", "love it", "awesome", "amazing",
    "cool", "good", "great", "best", "masterpiece", "classic albums",
    "5 stars", "10/10", "10 of 10", "perfect",
    "classic", "essential", "albums i love",
    # meta / too vague to say anything
    "album", "albums", "music", "under 2000 listeners", "all", "vocals",
})
