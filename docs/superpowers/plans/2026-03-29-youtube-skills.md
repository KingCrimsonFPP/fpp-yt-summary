# YouTube Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing `yt_transcript.py` script into a set of Claude Code slash commands (`/summarize`, `/transcript`, `/ask`) with timestamp support, bare ID input, last-video memory, and CLI-or-file output choice.

**Architecture:** The Python script is the data layer — it fetches transcripts from YouTube and persists state. Claude Code commands are thin instruction files that tell Claude how to invoke the script, process the output, and ask the user where to send results. No MCP server, no external services, no new dependencies.

**Tech Stack:** Python 3.9+, `youtube-transcript-api`, Claude Code commands (`.claude/commands/*.md`)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `yt_transcript.py` | Add bare-ID support, `--timestamps` flag, state file save/load |
| Create | `tests/test_yt_transcript.py` | Unit tests for all script changes |
| Create | `.claude/commands/summarize.md` | `/summarize` slash command |
| Create | `.claude/commands/transcript.md` | `/transcript` slash command |
| Create | `.claude/commands/ask.md` | `/ask` slash command |
| Modify | `readme.md` | Installation + usage docs |

---

## Task 1: Add bare video ID support to `extract_video_id`

**Files:**
- Modify: `yt_transcript.py` (function `extract_video_id`)
- Create: `tests/test_yt_transcript.py`

- [ ] **Step 1: Create test file with failing test**

```python
# tests/test_yt_transcript.py
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yt_transcript import extract_video_id

def test_bare_id_returned_as_is():
    assert extract_video_id("Vitf8YaVXhc") == "Vitf8YaVXhc"

def test_watch_url():
    assert extract_video_id("https://www.youtube.com/watch?v=Vitf8YaVXhc") == "Vitf8YaVXhc"

def test_short_url():
    assert extract_video_id("https://youtu.be/Vitf8YaVXhc") == "Vitf8YaVXhc"

def test_short_url_with_params():
    assert extract_video_id("https://youtu.be/Vitf8YaVXhc?si=abc123") == "Vitf8YaVXhc"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_yt_transcript.py::test_bare_id_returned_as_is -v
```
Expected: FAIL — the bare ID path doesn't exist yet, `extract_video_id` returns the last path segment which may be empty.

- [ ] **Step 3: Update `extract_video_id` in `yt_transcript.py`**

Replace the existing `extract_video_id` function with:

```python
import re

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
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest tests/test_yt_transcript.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add yt_transcript.py tests/test_yt_transcript.py
git commit -m "feat: support bare video IDs in extract_video_id"
```

---

## Task 2: Add timestamp formatting and `--timestamps` flag

**Files:**
- Modify: `yt_transcript.py` (add `format_timestamp`, update `get_transcript` and `main`)
- Modify: `tests/test_yt_transcript.py`

- [ ] **Step 1: Add failing tests for timestamp formatter**

Append to `tests/test_yt_transcript.py`:

```python
from yt_transcript import format_timestamp

def test_format_timestamp_seconds_only():
    assert format_timestamp(45.0) == "[00:45]"

def test_format_timestamp_minutes():
    assert format_timestamp(125.0) == "[02:05]"

def test_format_timestamp_hours():
    assert format_timestamp(3725.0) == "[01:02:05]"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_yt_transcript.py::test_format_timestamp_seconds_only -v
```
Expected: FAIL — `format_timestamp` not defined

- [ ] **Step 3: Add `format_timestamp` and update `get_transcript` in `yt_transcript.py`**

Add after the imports:

```python
def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"[{h:02d}:{m:02d}:{s:02d}]"
    return f"[{m:02d}:{s:02d}]"
```

Update `get_transcript` signature and return logic:

```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_yt_transcript.py -v
```
Expected: 7 PASSED

- [ ] **Step 5: Add `--timestamps` flag to `main`**

Replace the `main` function:

```python
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch YouTube transcript")
    parser.add_argument("url", help="YouTube URL or video ID")
    parser.add_argument("--timestamps", action="store_true", help="Include timestamps in output")
    args = parser.parse_args()

    video_id = extract_video_id(args.url)

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
```

- [ ] **Step 6: Commit**

```bash
git add yt_transcript.py tests/test_yt_transcript.py
git commit -m "feat: add --timestamps flag and format_timestamp to yt_transcript"
```

---

## Task 3: Add last-video state persistence

**Files:**
- Modify: `yt_transcript.py` (add `save_last_video`, `load_last_video`, call in `main`)
- Modify: `tests/test_yt_transcript.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_yt_transcript.py`:

```python
import tempfile
from pathlib import Path
from unittest.mock import patch
from yt_transcript import save_last_video, load_last_video

def test_save_and_load_last_video(tmp_path):
    state_file = tmp_path / ".last_video"
    with patch("yt_transcript.STATE_FILE", state_file):
        save_last_video("Vitf8YaVXhc")
        assert load_last_video() == "Vitf8YaVXhc"

def test_load_last_video_returns_none_when_missing(tmp_path):
    state_file = tmp_path / ".last_video"
    with patch("yt_transcript.STATE_FILE", state_file):
        assert load_last_video() is None
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_yt_transcript.py::test_save_and_load_last_video -v
```
Expected: FAIL — `save_last_video` not defined

- [ ] **Step 3: Add state functions to `yt_transcript.py`**

Add after imports (also add `from pathlib import Path` to imports):

```python
from pathlib import Path

STATE_FILE = Path(__file__).parent / "output" / ".last_video"

def save_last_video(video_id: str) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(video_id)

def load_last_video() -> str | None:
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip() or None
    return None
```

Update `main` to call `save_last_video` after extracting the ID:

```python
    video_id = extract_video_id(args.url)
    save_last_video(video_id)  # ← add this line
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_yt_transcript.py -v
```
Expected: 9 PASSED

- [ ] **Step 5: Commit**

```bash
git add yt_transcript.py tests/test_yt_transcript.py
git commit -m "feat: persist last video ID to output/.last_video"
```

---

## Task 4: Create `/summarize` command

**Files:**
- Create: `.claude/commands/summarize.md`

- [ ] **Step 1: Create the command file**

```markdown
<!-- .claude/commands/summarize.md -->
Summarize a YouTube video.

## Input

`$ARGUMENTS` may be:
- A YouTube URL (any format)
- A bare 11-character video ID
- Empty — use the last video by reading `output/.last_video`

If empty and `output/.last_video` does not exist, ask the user for a URL or ID.

## Steps

1. Resolve the video ID:
   - If `$ARGUMENTS` is non-empty, use it directly as the script argument
   - If empty, read `output/.last_video` with the Read tool; use that value

2. Run the transcript script (no timestamps needed for summary):
   ```
   python yt_transcript.py <url_or_id>
   ```

3. Ask the user: "**CLI or file?**"

4. Generate a summary from the transcript:
   - 5–10 bullet point overview
   - Key ideas / main arguments
   - Actionable takeaways (if any)
   - Note if transcript appears truncated or incomplete

5. Deliver the output:
   - **CLI**: print the summary in the conversation
   - **File**: save to `output/summary_<video_id>.md` using the Write tool
```

- [ ] **Step 2: Test manually**

In Claude Code, type:
```
/summarize https://www.youtube.com/watch?v=Vitf8YaVXhc
```
Verify: transcript is fetched, summary is generated, CLI/file question appears.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/summarize.md
git commit -m "feat: add /summarize Claude Code command"
```

---

## Task 5: Create `/transcript` command

**Files:**
- Create: `.claude/commands/transcript.md`

- [ ] **Step 1: Create the command file**

```markdown
<!-- .claude/commands/transcript.md -->
Fetch and display the full transcript of a YouTube video with timestamps.

## Input

`$ARGUMENTS` may be:
- A YouTube URL (any format)
- A bare 11-character video ID
- Empty — use the last video by reading `output/.last_video`

If empty and `output/.last_video` does not exist, ask the user for a URL or ID.

## Steps

1. Resolve the video ID (same as /summarize).

2. Run the transcript script with timestamps:
   ```
   python yt_transcript.py <url_or_id> --timestamps
   ```

3. Ask the user: "**CLI or file?**"

4. Deliver the output:
   - **CLI**: print the full transcript in the conversation
   - **File**: save to `output/transcript_<video_id>.txt` using the Write tool
```

- [ ] **Step 2: Test manually**

```
/transcript https://www.youtube.com/watch?v=Vitf8YaVXhc
```
Verify: transcript appears with `[MM:SS]` timestamps, CLI/file question appears.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/transcript.md
git commit -m "feat: add /transcript Claude Code command"
```

---

## Task 6: Create `/ask` command

**Files:**
- Create: `.claude/commands/ask.md`

- [ ] **Step 1: Create the command file**

```markdown
<!-- .claude/commands/ask.md -->
Search a YouTube video transcript for where a topic was discussed, and return verbatim quotes with timestamp links.

## Input

`$ARGUMENTS` is the question or topic to search for.

The video is always the last one worked on — read `output/.last_video`.
If `output/.last_video` does not exist, ask the user for a URL or ID first.

## Steps

1. Read `output/.last_video` to get the video ID.

2. Run the transcript script with timestamps:
   ```
   python yt_transcript.py <video_id> --timestamps
   ```

3. Search the transcript for segments relevant to `$ARGUMENTS`.

4. Return the top 3–5 matching segments as:
   - Verbatim quote from the transcript
   - Timestamp in `[MM:SS]` or `[HH:MM:SS]` format
   - Clickable link: `https://www.youtube.com/watch?v=<video_id>&t=<seconds>`

   Convert the timestamp to seconds for the URL parameter:
   - `[01:23]` → `t=83`
   - `[01:02:05]` → `t=3725`

5. If no relevant segments are found, say so clearly.
```

- [ ] **Step 2: Test manually**

First run `/summarize` on a video, then:
```
/ask what did they say about pricing?
```
Verify: 3-5 quotes appear with timestamp links.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/ask.md
git commit -m "feat: add /ask Claude Code command"
```

---

## Task 7: Update readme.md

**Files:**
- Modify: `readme.md`

- [ ] **Step 1: Replace readme content**

Rewrite `readme.md` to include:

```markdown
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

### 4. Register as a Claude Code project

Open this folder in Claude Code:

```bash
claude .
```

The `.claude/commands/` directory is automatically picked up. The three slash commands will be available immediately.

### 5. Verify

```
/summarize https://www.youtube.com/watch?v=Vitf8YaVXhc
```

---

## Using with Claude Desktop (MCP — optional)

If you want these commands available outside Claude Code (e.g. in Claude Desktop), you can expose the transcript script as a local MCP server. See `docs/mcp-setup.md` *(coming soon)*.

---

## Output files

All saved output lands in `output/`:

| File | Created by |
|------|------------|
| `output/summary_<id>.md` | `/summarize` → file |
| `output/transcript_<id>.txt` | `/transcript` → file |
| `output/.last_video` | Updated after every command |

---

## Scripts (advanced / direct use)

`yt_transcript.py` can also be run directly:

```bash
# Plain transcript
python yt_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# With timestamps
python yt_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" --timestamps

# Bare ID
python yt_transcript.py VIDEO_ID --timestamps

# Save to file
python yt_transcript.py VIDEO_ID --timestamps > output/transcript.txt
```
```

- [ ] **Step 2: Commit**

```bash
git add readme.md
git commit -m "docs: rewrite readme with installation and command reference"
```

---

## Self-Review

**Spec coverage:**
- ✅ URL or bare ID input
- ✅ "Last video" memory via state file
- ✅ CLI or file output choice on every command
- ✅ `/summarize`
- ✅ `/transcript` with timestamps
- ✅ `/ask` with verbatim quotes + timestamp links
- ✅ Readme with installation instructions

**Placeholder scan:** None found — all steps contain actual code or file content.

**Type consistency:** `get_transcript(video_id, with_timestamps)` used consistently across Tasks 2 and 3. `STATE_FILE`, `save_last_video`, `load_last_video` defined in Task 3 and referenced in the same task only (commands call the CLI, not the Python API directly).
