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
