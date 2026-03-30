#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)


STATE_FILE = Path(__file__).parent / "output" / ".last_video"

def save_last_video(video_id: str) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(video_id)

def load_last_video() -> str | None:
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip() or None
    return None


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"[{h:02d}:{m:02d}:{s:02d}]"
    return f"[{m:02d}:{s:02d}]"


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


def get_transcript(video_id: str, with_timestamps: bool = False, lang_priority=None) -> str:
    if lang_priority is None:
        lang_priority = ["en", "en-US", "en-GB"]

    api = YouTubeTranscriptApi()

    try:
        fetched = api.fetch(video_id, languages=lang_priority)
    except NoTranscriptFound as last_exc:
        transcript_list = api.list(video_id)
        transcripts = list(transcript_list)
        if not transcripts:
            raise last_exc
        fetched = transcripts[0].fetch()

    snippets = [s for s in fetched]

    if with_timestamps:
        lines = []
        for s in snippets:
            text = getattr(s, "text", "").strip()
            if text:
                ts = format_timestamp(getattr(s, "start", 0.0))
                lines.append(f"{ts} {text}")
        return "\n".join(lines)

    return " ".join(
        getattr(s, "text", "").strip()
        for s in snippets
        if getattr(s, "text", "").strip()
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch YouTube transcript")
    parser.add_argument("url", help="YouTube URL or video ID")
    parser.add_argument("--timestamps", action="store_true", help="Include timestamps in output")
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    save_last_video(video_id)

    try:
        transcript_text = get_transcript(video_id, with_timestamps=args.timestamps)
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
