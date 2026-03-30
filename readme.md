# YouTube Summaries — Claude Code Plugin

Slash commands for Claude Code that fetch YouTube transcripts, generate summaries, and let you search for exact quotes with timestamp links.

## Commands

| Command | Description |
|---------|-------------|
| `/summarize [url\|id]` | Summarize a video. Omit arg to reuse last video. |
| `/transcript [url\|id]` | Full transcript with timestamps. |
| `/ask <question>` | Find where a topic was discussed + timestamp links. |

All commands accept:
- Full YouTube URL: `https://www.youtube.com/watch?v=VIDEO_ID`
- Short URL: `https://youtu.be/VIDEO_ID`
- Bare video ID: `VIDEO_ID` (11 characters)
- No argument: reuses the last video automatically

After fetching, each command asks whether you want output in the **CLI** or saved to a **file** in `output/`.

---

## Installation

### 1. Prerequisites

- Python 3.9+
- Node.js (for Claude Code CLI)
- Claude Code installed: `npm install -g @anthropic-ai/claude-code`

### 2. Clone this repo

```bash
git clone <repo-url>
cd yt_summaries
```

### 3. Install Python dependencies

```bash
pip install youtube-transcript-api
```

Or with a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
.venv\Scripts\activate          # Windows
pip install youtube-transcript-api
```

### 4. Open in Claude Code

```bash
claude .
```

The `.claude/commands/` directory is picked up automatically. The three slash commands are immediately available.

### 5. Verify

```
/summarize https://www.youtube.com/watch?v=Vitf8YaVXhc
```

---

## Output files

All saved output lands in `output/`:

| File | Created by |
|------|------------|
| `output/summary_<id>.md` | `/summarize` → file |
| `output/transcript_<id>.txt` | `/transcript` → file |
| `output/.last_video` | Updated after every command |

---

## Direct script usage

`yt_transcript.py` can be run directly:

```bash
# Plain transcript
python yt_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# With timestamps
python yt_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" --timestamps

# Bare video ID
python yt_transcript.py VIDEO_ID --timestamps

# Save to file
python yt_transcript.py VIDEO_ID --timestamps > output/transcript.txt
```
