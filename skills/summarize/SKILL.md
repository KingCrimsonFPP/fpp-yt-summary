---
name: yt-summary:summarize
description: Summarize a YouTube video by extracting and condensing its transcript into key points and takeaways
---

# Summarize Skill

Generates a concise summary of a YouTube video by extracting the transcript and condensing it into key points, main arguments, and actionable takeaways.

## Behavior

1. **Get the video identifier**: If the user hasn't provided a YouTube URL or video ID, ask them for it.

2. **Run the transcript script**: Execute the transcript extraction script without timestamps:
   ```
   python {plugin_dir}/scripts/yt_transcript.py <url_or_id>
   ```

   Where `{plugin_dir}` is the plugin's installation directory (the directory containing `scripts/yt_transcript.py`). Find this directory by locating the `scripts/yt_transcript.py` file in the fpp-yt-summary plugin installation.

3. **Generate the summary**: Analyze the extracted transcript and create a structured summary with the following sections:
   - **Overview**: 5–10 bullet points covering the main content and key points of the video
   - **Key Ideas / Main Arguments**: The core concepts, themes, or arguments presented
   - **Actionable Takeaways**: Practical steps, recommendations, or conclusions the user can apply (if applicable)
   - **Notes**: Any observations about transcript completeness (e.g., if the transcript appears truncated, incomplete, or if there were extraction issues)

4. **Save the summary**: After generating the summary, save it to a file named `output/summary_<video_id>.md` in the user's working directory using the Write tool. Format the summary as a Markdown file with clear sections and formatting.

5. **Display the summary**: Show the complete summary to the user in the conversation.

## Notes

- The script automatically saves the video ID to `{plugin_dir}/scripts/output/.last_video` for reference.
- If the script fails or returns an error, report the error to the user and offer to help troubleshoot.
- Handle both full YouTube URLs (e.g., `https://www.youtube.com/watch?v=VIDEO_ID`) and bare video IDs.
- Ensure the summary file is well-formatted with proper Markdown heading levels and bullet points for readability.
