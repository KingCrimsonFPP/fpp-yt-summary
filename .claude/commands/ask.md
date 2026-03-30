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
