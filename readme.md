# YouTube Transcript & Summary Tools

This repo contains two Python scripts:

1. `yt_transcript.py` – fetches the transcript of a YouTube video.
2. `summarize_youtube.py` – fetches the transcript and sends it to OpenAI to generate a summary.

---

## 1. Prerequisites

- Python 3.9+ (tested with 3.11)
- `pip` for installing dependencies
- An OpenAI API key (for `summarize_youtube.py` only)

---

## 2. Script: `yt_transcript.py` (Get Transcripts Only)

This script uses `youtube-transcript-api` to pull the transcript from a YouTube video and print it to stdout.

### 2.1. Install dependencies

```bash
pip install youtube-transcript-api
```

### 2.2. How to execute

From the project root (where `yt_transcript.py` lives):

```bash
python yt_transcript.py "<YOUTUBE_URL>"
```

Example:

```bash
python yt_transcript.py "https://www.youtube.com/watch?v=Vitf8YaVXhc"
```

### 2.3. Output

- By default, the script prints the full transcript as plain text to **stdout**.
- You can redirect it to a file:

```bash
python yt_transcript.py "https://www.youtube.com/watch?v=Vitf8YaVXhc" > ./output/transcript.txt
```

Result:

- `transcript.txt` will contain the merged transcript text (no timestamps) in the detected language.

---

## 3. Script: `summarize_youtube.py` (Get Transcript + Summary via OpenAI)

This script:

1. Extracts the video ID from a YouTube URL.
2. Uses `yt_transcript.py`’s functions to get the transcript.
3. Sends the transcript to the OpenAI API with a summarization prompt.
4. Prints a Markdown-formatted summary.

### 3.1. Install dependencies

```bash
pip install youtube-transcript-api openai
```

(Optional virtual environment):

```bash
python -m venv .venv
.\.venv\Scriptsctivate   # Windows
source .venv/bin/activate # macOS/Linux
pip install youtube-transcript-api openai
```

### 3.2. Set environment variables

#### Windows PowerShell

**Temporary:**

```powershell
$env:OPENAI_API_KEY="sk-xxx_your_key_here"
```

**Persistent:**

```powershell
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-xxx_your_key_here", "User")
```

#### macOS / Linux

```bash
export OPENAI_API_KEY="sk-xxx_your_key_here"
```

### 3.3. How to execute

```bash
python summarize_youtube.py "<YOUTUBE_URL>"
```

Example:

```bash
python summarize_youtube.py "https://www.youtube.com/watch?v=Vitf8YaVXhc"
```

Save output:

```bash
python summarize_youtube.py "https://www.youtube.com/watch?v=Vitf8YaVXhc" > ./output/summary.md
```

### 3.4. Output

Produces a Markdown summary containing:

- Bullet-point summary
- Key ideas
- Actionable insights
- Notes if transcript is truncated

---

## 4. Troubleshooting

### Missing modules

```bash
python -m pip install openai youtube-transcript-api
```

### Missing environment variable

Verify:

- PowerShell: `echo $env:OPENAI_API_KEY`
- Bash: `echo $OPENAI_API_KEY`

---

## 5. Suggested Project Structure

```
yt_summaries/
├─ yt_transcript.py
├─ summarize_youtube.py
├─ README.md
└─ requirements.txt
```

Example `requirements.txt`:

```
youtube-transcript-api
openai
```

Install:

```bash
pip install -r requirements.txt
```

---

Happy summarizing! 🎬📝
