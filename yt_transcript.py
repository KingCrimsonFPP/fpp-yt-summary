#!/usr/bin/env python3
import re
import sys
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)


_VIDEO_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')

def extract_video_id(url: str) -> str:
    """
    Handles:
    - Bare 11-char video IDs: Vitf8YaVXhc
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    """
    url = url.strip()

    if _VIDEO_ID_RE.match(url):
        return url

    parsed = urlparse(url)

    if parsed.netloc in ("youtu.be", "www.youtu.be"):
        return parsed.path.lstrip("/")

    qs = parse_qs(parsed.query)
    if "v" in qs:
        return qs["v"][0]

    return parsed.path.split("/")[-1]


def get_transcript(video_id: str, lang_priority=None) -> str:
    """
    Use the new instance API in youtube-transcript-api 1.2.3:
      ytt_api = YouTubeTranscriptApi()
      ytt_api.fetch(video_id, languages=[...])
    Fallback: if preferred languages fail, pick the first available transcript.
    """
    if lang_priority is None:
        lang_priority = ["en", "en-US", "en-GB"]

    api = YouTubeTranscriptApi()

    # 1) Try preferred languages
    try:
        fetched = api.fetch(video_id, languages=lang_priority)
    except NoTranscriptFound as last_exc:
        # 2) Fallback: list all available transcripts and pick the first one
        transcript_list = api.list(video_id)
        transcripts = list(transcript_list)

        if not transcripts:
            # no tracks at all
            raise last_exc

        fetched = transcripts[0].fetch()

    # fetched is a FetchedTranscript (iterable of snippets)
    snippets = [s for s in fetched]
    full_text = " ".join(
        getattr(s, "text", "").strip()
        for s in snippets
        if getattr(s, "text", "").strip()
    )

    return full_text


def main():
    if len(sys.argv) < 2:
        print("Usage: yt_transcript.py <youtube_url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    video_id = extract_video_id(url)

    try:
        transcript_text = get_transcript(video_id)
        print(transcript_text)
    except TranscriptsDisabled:
        print("Transcripts are disabled for this video.", file=sys.stderr)
        sys.exit(2)
    except NoTranscriptFound as e:
        print(f"No transcript found: {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
