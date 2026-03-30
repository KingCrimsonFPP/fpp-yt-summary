Fetch and display the full transcript of a YouTube video with timestamps.

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

2. Run the transcript script with timestamps:
   ```
   python yt_transcript.py <url_or_id> --timestamps
   ```

3. Ask the user: "**CLI or file?**"

4. Deliver the output:
   - **CLI**: print the full transcript in the conversation
   - **File**: save to `output/transcript_<video_id>.txt` using the Write tool
