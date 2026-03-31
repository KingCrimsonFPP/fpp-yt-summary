# Plugin Structure Design — fpp-yt-summary

**Date:** 2026-03-31
**Status:** Approved

## Goal

Restructure the `fpp-yt-summary` repo into the standard Claude Code plugin format so it can be distributed via `/plugin marketplace add KingCrimsonFPP/fpp-yt-summary`.

## Final Structure

```
fpp-yt-summary/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Marketplace registry
├── skills/
│   ├── setup/
│   │   └── SKILL.md         # Install dependencies
│   ├── summarize/
│   │   └── SKILL.md         # Summarize a YouTube video
│   ├── transcript/
│   │   └── SKILL.md         # Fetch full transcript with timestamps
│   └── ask/
│       └── SKILL.md         # Search transcript for a topic
├── scripts/
│   └── yt_transcript.py     # Python backend (moved from root)
├── requirements.txt
└── README.md
```

## What Changes

- `commands/` and `.claude/commands/` removed — replaced by skills
- `yt_transcript.py` moved to `scripts/`
- Skills use natural language triggers (Option A)

## Skills Specification

### setup
- **Trigger:** User mentions setup, install, dependencies, or first use of any other skill fails
- **Behavior:** Runs `pip install youtube-transcript-api`, confirms success
- **Output:** Confirmation message

### summarize
- **Trigger:** User asks to summarize a YouTube video/URL
- **Input:** YouTube URL or video ID (ask if not provided)
- **Behavior:** Calls `scripts/yt_transcript.py <id>`, generates 5-10 bullet summary
- **Output:** Summary saved to `output/summary_<id>.md`

### transcript
- **Trigger:** User asks for transcript, captions, or full text of a YouTube video
- **Input:** YouTube URL or video ID (ask if not provided)
- **Behavior:** Calls `scripts/yt_transcript.py <id> --timestamps`
- **Output:** Saved to `output/transcript_<id>.txt`

### ask
- **Trigger:** User asks what a video said about a topic, or wants to find a moment in a video
- **Input:** Topic/question; video from `output/.last_video` (ask if not found)
- **Behavior:** Fetches transcript, finds top 3-5 relevant segments
- **Output:** Verbatim quotes with `[MM:SS]` timestamps and clickable YouTube links

## Execution Plan (Fan-out / Fan-in)

- **Fan-out:** 4 parallel Haiku agents each write one `SKILL.md`
- **Fan-in:** 1 Opus agent verifies consistency across all 4 skills (paths, triggers, output conventions)
