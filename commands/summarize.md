Summarize a YouTube video.

## Input

`$ARGUMENTS` may be:
- A YouTube URL (any format)
- A bare 11-character video ID
- Empty — ask the user for a URL or ID before doing anything else

## Steps

1. Resolve the video ID:
   - If `$ARGUMENTS` is non-empty, use it directly as the script argument
   - If empty, ask the user: "Please provide a YouTube URL or video ID." — stop until they reply

2. Run the transcript script (no timestamps needed for summary):
   ```
   python yt_transcript.py <url_or_id>
   ```

3. Generate a summary from the transcript:
   - 5–10 bullet point overview
   - Key ideas / main arguments
   - Actionable takeaways (if any)
   - Note if transcript appears truncated or incomplete

4. Save to `output/summary_<video_id>.md` using the Write tool.
