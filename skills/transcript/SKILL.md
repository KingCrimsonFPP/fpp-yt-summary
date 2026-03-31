---
name: yt-summary:transcript
description: Fetch and display the full transcript or captions of a YouTube video with timestamps
---

# Transcript Skill

Fetches and displays the complete transcript of a YouTube video with timestamps.

## Behavior

1. **Get the video identifier**: If the user hasn't provided a YouTube URL or video ID, ask them for it.

2. **Run the transcript script**: Execute the transcript extraction script with timestamps:
   ```
   python {plugin_dir}/scripts/yt_transcript.py <url_or_id> --timestamps
   ```

   Where `{plugin_dir}` is the plugin's installation directory (the directory containing `scripts/yt_transcript.py`). Find this directory by locating the `scripts/yt_transcript.py` file in the fpp-yt-summary plugin installation.

3. **Save the transcript**: After the script completes successfully, save the output to a file named `output/transcript_<video_id>.txt` in the user's working directory. Use the Write tool to create this file.

4. **Display a preview**: Show the user the first few lines of the transcript to confirm it was extracted successfully.

## Notes

- The script automatically saves the video ID to `{plugin_dir}/scripts/output/.last_video` for reference.
- If the script fails or returns an error, report the error to the user and offer to help troubleshoot.
- Handle both full YouTube URLs (e.g., `https://www.youtube.com/watch?v=VIDEO_ID`) and bare video IDs.
