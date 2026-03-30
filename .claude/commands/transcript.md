Fetch and display the full transcript of a YouTube video with timestamps.

## Input

`$ARGUMENTS` may be:
- A YouTube URL (any format)
- A bare 11-character video ID
- Empty — ask the user for a URL or ID before doing anything else

## Steps

1. Resolve the video ID:
   - If `$ARGUMENTS` is non-empty, use it directly as the script argument
   - If empty, ask the user: "Please provide a YouTube URL or video ID." — stop until they reply

2. Run the transcript script with timestamps:
   ```
   python yt_transcript.py <url_or_id> --timestamps
   ```

3. Save to `output/transcript_<video_id>.txt` using the Write tool.
