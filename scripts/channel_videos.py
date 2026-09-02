#!/usr/bin/env python3
"""List a YouTube channel's videos as JSON candidates for ingest.

Usage:
    python channel_videos.py "<channel URL or @handle>" [--since-days N] [--limit N]

Output (stdout): a JSON array of ``{video_id, title, url, tab, published?}``.

Two details worth knowing before changing this:

* **The RSS feed only carries ~15 entries.** It is the cheap way to get upload
  dates, but on a channel that posted more than that inside the window it silently
  drops the rest. So the listing comes from ``yt-dlp --flat-playlist`` over the
  ``/videos`` *and* ``/shorts`` tabs (shorts do not appear under /videos), and RSS
  is used only to date what it happens to cover.
* **Anything RSS missed gets dated individually.** That probe costs one request
  per video, so it walks newest-first and stops once it has seen a run of
  out-of-window videos — channel tabs are roughly reverse-chronological.

Topic filtering ("videos about X") is deliberately not done here: the caller
filters the returned titles semantically. This script stays deterministic.
"""
import argparse
import datetime
import json
import re
import ssl
import subprocess
import sys
import urllib.request

try:
    from defusedxml.ElementTree import fromstring as xml_fromstring
except Exception:
    from xml.etree.ElementTree import fromstring as xml_fromstring

TABS = ("videos", "shorts")
RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
ATOM_NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def normalize_channel_url(value: str) -> str:
    """Accept '@handle', 'youtube.com/@handle', a /channel/ or /c/ URL, or a URL
    already pointing at a tab. Returns the channel base URL, tab stripped."""
    value = (value or "").strip().rstrip("/")
    if not value:
        raise ValueError("empty channel reference")

    if value.startswith("@"):
        return f"https://www.youtube.com/{value}"

    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    for tab in TABS + ("streams", "featured"):
        if value.endswith("/" + tab):
            value = value[: -(len(tab) + 1)]
            break
    return value


def flat_list(url: str) -> tuple[list[dict], str | None]:
    """(videos, error). A failing tab is not on its own a problem — a channel
    with no shorts has no /shorts page — so the caller decides what it means."""
    cmd = ["yt-dlp", "--flat-playlist", "--no-warnings",
           "--print", "%(id)s\t%(title)s", url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return [], stderr.splitlines()[-1] if stderr else f"yt-dlp exited {result.returncode}"

    videos = []
    for line in result.stdout.strip().splitlines():
        if "\t" not in line:
            continue
        video_id, title = line.split("\t", 1)
        video_id, title = video_id.strip(), title.strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            videos.append({"video_id": video_id, "title": title})
    return videos, None


def list_channel(base_url: str, tabs=TABS) -> list[dict]:
    """Videos across the channel's tabs, deduped by id, listing order preserved.

    Raises if *every* tab failed — that means the channel reference is wrong (a
    common one: using the channel's display name where its @handle is required),
    and reporting yt-dlp's own message beats an empty list.
    """
    seen, out, errors = set(), [], []
    for tab in tabs:
        videos, error = flat_list(f"{base_url}/{tab}")
        if error:
            errors.append(f"{tab}: {error}")
        for video in videos:
            if video["video_id"] in seen:
                continue
            seen.add(video["video_id"])
            out.append({**video, "tab": tab})

    if not out and errors:
        raise RuntimeError("; ".join(errors))
    return out


def channel_id(url: str) -> str:
    """The UC… id, needed to build the RSS URL. Read from a one-item flat dump —
    in flat mode the per-entry channel_id is NA, but the top-level one is set."""
    cmd = ["yt-dlp", "--flat-playlist", "--playlist-items", "1", "-J",
           "--no-warnings", url]
    data = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    cid = data.get("channel_id")
    if not cid:
        raise RuntimeError("could not resolve channel_id")
    return cid


def rss_dates(cid: str) -> dict[str, str]:
    """{video_id: 'YYYY-MM-DD'} for the ~15 most recent uploads."""
    data = urllib.request.urlopen(
        RSS_URL.format(cid), context=ssl.create_default_context(), timeout=20
    ).read()
    dates = {}
    for entry in xml_fromstring(data).findall("a:entry", ATOM_NS):
        vid = entry.find("yt:videoId", ATOM_NS)
        published = entry.find("a:published", ATOM_NS)
        if vid is not None and published is not None and published.text:
            dates[vid.text] = published.text[:10]
    return dates


def probe_upload_date(video_id: str) -> str:
    """'YYYY-MM-DD' for one video, or '' if it cannot be resolved (an unaired
    premiere, a members-only video, a deleted id)."""
    cmd = ["yt-dlp", "--skip-download", "--no-warnings",
           "--print", "%(upload_date)s",
           f"https://www.youtube.com/watch?v={video_id}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    raw = result.stdout.strip()
    if result.returncode != 0 or len(raw) != 8 or not raw.isdigit():
        return ""
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def apply_date_window(videos, cutoff, known_dates, stop_after_old=5):
    """Keep videos published on/after ``cutoff``, dating the ones RSS missed.

    Stops probing after ``stop_after_old`` consecutive out-of-window videos, so a
    channel with a decade of uploads costs a handful of requests rather than one
    per video. Undatable videos (unaired premieres) are dropped from a windowed
    listing but do not count toward the stop, since they carry no date signal.
    """
    kept, consecutive_old = [], 0

    for video in videos:
        published = known_dates.get(video["video_id"])
        if published is None:
            published = probe_upload_date(video["video_id"])

        if not published:
            continue

        if published >= cutoff:
            kept.append({**video, "published": published})
            consecutive_old = 0
        else:
            consecutive_old += 1
            if consecutive_old >= stop_after_old:
                break

    kept.sort(key=lambda v: v["published"], reverse=True)
    return kept


def main():
    parser = argparse.ArgumentParser(description="List a channel's videos as JSON")
    parser.add_argument("channel", help="Channel URL or @handle")
    parser.add_argument("--since-days", type=int, default=None,
                        help="Keep only videos published within the last N days")
    parser.add_argument("--limit", type=int, default=None, help="Cap the result count")
    parser.add_argument("--stop-after-old", type=int, default=5,
                        help="Stop date-probing after this many consecutive out-of-window videos")
    args = parser.parse_args()

    try:
        base = normalize_channel_url(args.channel)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)

    try:
        videos = list_channel(base)
    except RuntimeError as exc:
        print(json.dumps({"error": f"could not list {base}", "detail": str(exc)}), file=sys.stderr)
        sys.exit(1)

    if not videos:
        print(json.dumps({"error": f"no videos listed for {base}"}), file=sys.stderr)
        sys.exit(1)

    if args.since_days is not None:
        cutoff = (datetime.date.today() - datetime.timedelta(days=args.since_days)).isoformat()
        try:
            known = rss_dates(channel_id(base))
        except Exception:
            known = {}  # every video gets probed individually instead
        videos = apply_date_window(videos, cutoff, known, args.stop_after_old)

    if args.limit:
        videos = videos[: args.limit]

    for video in videos:
        video["url"] = f"https://www.youtube.com/watch?v={video['video_id']}"

    print(json.dumps(videos, indent=2))


if __name__ == "__main__":
    main()
