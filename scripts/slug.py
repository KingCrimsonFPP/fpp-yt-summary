#!/usr/bin/env python3
"""Build the ``<author>-<title>`` kebab-case folder name used for a source set."""
import re


def _clean(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_]+", "-", value.strip())
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def slugify(author: str, title: str, fallback: str = "", maxlen: int = 72) -> str:
    """``slugify("Some Channel", "A Talk") -> "some-channel-a-talk"``.

    ``fallback`` (normally the video id) stands in for whichever half is missing.
    Without it two videos whose metadata failed to resolve would both slug to
    ``unknown-untitled`` and the second would land on top of the first.
    """
    fallback = _clean(fallback)
    author = _clean(author) or fallback or "unknown"
    title = _clean(title) or fallback or "untitled"

    slug = f"{author}-{title}"
    if len(slug) > maxlen:
        slug = slug[:maxlen].rstrip("-")
    return slug
