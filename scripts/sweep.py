#!/usr/bin/env python3
"""Sweep a manifest of channels and ingest whatever is missing.

Usage:
    python sweep.py <manifest> [--output-dir DIR] [--since-days N] [--dry-run]

The manifest is a plain text file you point at — one channel per line, ``#`` for
comments. It is an argument rather than a file in this repo because a real
subscription list is personal data; see ``examples/channels.example.txt`` for the
format.

The sweep is idempotent. Videos already ingested under the output directory are
filtered out by video id before anything is fetched, so re-running after an
interruption picks up exactly what is left.

Rate limiting is the main hazard on a large sweep: YouTube throttles the caption
endpoints per IP (``HTTP 429`` / ``IpBlocked``). Requests are paced, a throttled
video is retried after an exponential backoff, and the run gives up only after a
long run of consecutive blocks — so it can be left to grind rather than babysat.
"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import channel_videos as cv  # noqa: E402
from ingest_video import DEFAULT_OUTPUT_DIR, ingest, ingested_video_ids  # noqa: E402

BACKOFF = [60, 180, 420, 900, 1800, 3600]  # seconds; the last value repeats
RATE_LIMITED = re.compile(r"429|IpBlocked|Too Many Requests|RequestBlocked", re.I)
PREMIERE = re.compile(r"premiere|live event will begin|not yet available|hasn't started", re.I)


def read_manifest(path) -> list[str]:
    """Channel references from the manifest, deduped by normalized URL.

    Dedupe is on the normalized form so ``@chan``, ``youtube.com/@chan`` and
    ``youtube.com/@chan/videos`` in the same file poll the channel once.
    """
    seen, channels = set(), []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            try:
                normalized = cv.normalize_channel_url(line)
            except ValueError:
                continue
            key = normalized.lower()
            if key not in seen:
                seen.add(key)
                channels.append(normalized)
    return channels


def log(message, logpath=None):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    if logpath:
        try:
            with open(logpath, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


def collect_candidates(channels, since_days, limit_per_channel=None, stop_after_old=5, logpath=None):
    """Poll each channel and return the deduped candidate list, newest tab order."""
    import datetime

    cutoff = (datetime.date.today() - datetime.timedelta(days=since_days)).isoformat()
    seen, candidates = set(), []

    for channel in channels:
        try:
            videos = cv.list_channel(channel)
            try:
                known = cv.rss_dates(cv.channel_id(channel))
            except Exception:
                known = {}
            videos = cv.apply_date_window(videos, cutoff, known, stop_after_old)
        except Exception as exc:
            log(f"CHANNEL-FAIL {channel}: {exc}", logpath)
            continue

        if limit_per_channel:
            videos = videos[:limit_per_channel]

        fresh = 0
        for video in videos:
            if video["video_id"] in seen:
                continue
            seen.add(video["video_id"])
            candidates.append({**video, "channel_url": channel})
            fresh += 1
        log(f"CHANNEL {channel}: {fresh} in window", logpath)

    return candidates


def sweep(manifest, output_dir=DEFAULT_OUTPUT_DIR, since_days=7, limit_per_channel=None,
          pace=8.0, max_block=30, dry_run=False, logpath=None, stop_after_old=5):
    channels = read_manifest(manifest)
    if not channels:
        log(f"no channels found in {manifest}", logpath)
        return {"ingested": 0, "skipped": 0, "failed": 0, "candidates": []}

    log(f"sweeping {len(channels)} channel(s), last {since_days} day(s)", logpath)
    candidates = collect_candidates(channels, since_days, limit_per_channel, stop_after_old, logpath)

    already = ingested_video_ids(output_dir)
    todo = [c for c in candidates if c["video_id"] not in already]
    log(f"{len(candidates)} candidate(s), {len(candidates) - len(todo)} already ingested, "
        f"{len(todo)} to fetch", logpath)

    if dry_run:
        for candidate in todo:
            log(f"WOULD INGEST {candidate['video_id']} :: {candidate['title']}", logpath)
        return {"ingested": 0, "skipped": 0, "failed": 0, "candidates": todo}

    ingested = skipped = failed = 0
    consecutive_blocks = 0
    index = 0

    while index < len(todo):
        candidate = todo[index]
        video_id = candidate["video_id"]
        try:
            result = ingest(video_id, output_dir)
        except Exception as exc:
            message = str(exc)

            if RATE_LIMITED.search(message):
                consecutive_blocks += 1
                if consecutive_blocks >= max_block:
                    log(f"BLOCKED {consecutive_blocks}x consecutively — stopping. "
                        f"{len(todo) - index} left; rerun to resume.", logpath)
                    break
                wait = BACKOFF[min(consecutive_blocks - 1, len(BACKOFF) - 1)]
                log(f"429 on {video_id} (block #{consecutive_blocks}) — waiting {wait}s, "
                    f"then retrying the same video", logpath)
                time.sleep(wait)
                continue

            consecutive_blocks = 0
            index += 1
            if PREMIERE.search(message):
                skipped += 1
                log(f"PREMIERE {video_id} — not aired yet, will be picked up next sweep", logpath)
            else:
                failed += 1
                log(f"FAIL {video_id}: {message[:200]}", logpath)
            time.sleep(pace)
            continue

        consecutive_blocks = 0
        index += 1
        if result["skipped"]:
            skipped += 1
            log(f"SKIP {video_id} :: already at {result['path']}", logpath)
        else:
            ingested += 1
            log(f"OK [{ingested}] {video_id} -> {result['slug']}", logpath)
            time.sleep(pace)

    log(f"sweep end: ingested={ingested} skipped={skipped} failed={failed}", logpath)
    return {"ingested": ingested, "skipped": skipped, "failed": failed, "candidates": todo}


def main():
    parser = argparse.ArgumentParser(description="Sweep a channel manifest and ingest new videos")
    parser.add_argument("manifest", help="Path to the channel manifest file")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help=f"Where source sets are written (default: {DEFAULT_OUTPUT_DIR}/)")
    parser.add_argument("--since-days", type=int, default=7,
                        help="Only consider uploads from the last N days (default: 7)")
    parser.add_argument("--limit-per-channel", type=int, default=None,
                        help="Cap candidates taken from each channel")
    parser.add_argument("--pace", type=float, default=8.0,
                        help="Seconds between fetches (default: 8)")
    parser.add_argument("--max-block", type=int, default=30,
                        help="Give up after this many consecutive rate-limit blocks")
    parser.add_argument("--stop-after-old", type=int, default=5,
                        help="Stop date-probing a channel after this many consecutive old videos")
    parser.add_argument("--dry-run", action="store_true",
                        help="List what would be ingested and exit")
    parser.add_argument("--no-api", action="store_true",
                        help="Skip youtube_transcript_api; go straight to yt-dlp")
    parser.add_argument("--log", default=None, help="Also append run output to this file")
    args = parser.parse_args()

    if args.no_api:
        os.environ["YT_NO_API"] = "1"

    result = sweep(
        args.manifest, args.output_dir, args.since_days, args.limit_per_channel,
        args.pace, args.max_block, args.dry_run, args.log, args.stop_after_old,
    )
    sys.exit(1 if result["failed"] and not result["ingested"] else 0)


if __name__ == "__main__":
    main()
