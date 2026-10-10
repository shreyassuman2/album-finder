"""Clusters: what to do when the 5 inputs don't agree.

Two inputs are linked if:
  - their tags share a word ("west coast hip hop" and "hip hop" share "hip"
    and "hop"), or
  - one input's artist is on the other's similar-artists list.
Linked inputs form a group (if A links to B and B to C, all three are one
group), and we recommend for the biggest group.
"""

import re

from app.engine.profile import Tags
from app.engine.resolve import ResolvedAlbum

# Words that appear in tags of unrelated genres and would link everything:
# "dream pop" and "pop rap" share "pop" but sound nothing alike.
GENERIC_WORDS = {"music", "and", "of", "the", "s", "new", "alternative", "indie", "pop", "rock"}
DECADE = re.compile(r"^(19|20)?\d0s$")  # "90s", "1990s": an era, not a sound


def _tag_words(tags: Tags) -> set[str]:
    words = {word for tag, _ in tags for word in tag.split()}
    return {w for w in words if w not in GENERIC_WORDS and not DECADE.match(w)}


def linked(a: int, b: int, inputs: list[ResolvedAlbum], input_tags: list[Tags], similar: list[set[str]]) -> bool:
    if _tag_words(input_tags[a]) & _tag_words(input_tags[b]):
        return True
    return inputs[b].artist.lower() in similar[a] or inputs[a].artist.lower() in similar[b]


def cluster_inputs(inputs: list[ResolvedAlbum], input_tags: list[Tags], similar: list[set[str]]) -> list[list[int]]:
    """Group input positions into connected groups, biggest first (ties keep
    the order the user entered them).

    `similar[i]` is the set of lowercased similar-artist names for input i.
    """
    unvisited = list(range(len(inputs)))
    groups = []
    while unvisited:
        # Flood fill: start from one input and keep pulling in anything
        # linked to an input already in the group.
        group = [unvisited.pop(0)]
        for member in group:  # `group` grows while we loop over it
            for other in list(unvisited):
                if linked(member, other, inputs, input_tags, similar):
                    group.append(other)
                    unvisited.remove(other)
        groups.append(sorted(group))
    return sorted(groups, key=len, reverse=True)  # sorted() is stable, so ties keep input order


def cluster_note(chosen: list[ResolvedAlbum]) -> str:
    titles = [a.title for a in chosen]
    joined = titles[0] if len(titles) == 1 else ", ".join(titles[:-1]) + " and " + titles[-1]
    return f"Your picks didn't share one sound, so these focus on {joined}."
