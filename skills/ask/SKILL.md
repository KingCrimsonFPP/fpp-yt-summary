---
name: yt-summary:ask
description: Search a YouTube video transcript for where a specific topic was discussed. Trigger when the user wants to find where in a video something was mentioned, asks what a video said about a topic, or wants to locate a specific moment in the video.
---

# Ask Skill

Search YouTube video transcripts to find where specific topics or moments are discussed.

## Workflow

1. **Load the current video**
   - Read `{plugin_dir}/scripts/output/.last_video` to get the stored video ID (where `{plugin_dir}` is the plugin's installation directory)
   - If the file doesn't exist, ask the user for a YouTube URL or video ID
   - Store the video ID for the search operation

2. **Confirm the search with the user**
   - Display: "About to search **<topic>** in: https://www.youtube.com/watch?v=<video_id> — continue?"
   - Stop and wait for the user's response
   - If they say no or want a different video, ask for a new YouTube URL or video ID
   - If they confirm, proceed to the next step

3. **Fetch the transcript with timestamps**
   - Run: `python {plugin_dir}/scripts/yt_transcript.py <video_id> --timestamps`
   - Replace `{plugin_dir}` with the directory containing the `scripts/yt_transcript.py` file
   - This retrieves the full transcript with timestamp markers

4. **Search the transcript**
   - Search through the transcript for segments relevant to the user's topic
   - Identify the most relevant segments that mention or discuss the topic
   - Keep track of the timestamps for each segment

5. **Format and return results**
   - Return the top 3–5 most relevant matching segments
   - For each segment, provide:
     - The verbatim quote from the transcript
     - The timestamp in `[MM:SS]` or `[HH:MM:SS]` format
     - A clickable YouTube link: `https://www.youtube.com/watch?v=<video_id>&t=<seconds>`
   - Convert timestamps to seconds:
     - `[01:23]` → `t=83` (1×60 + 23 = 83 seconds)
     - `[01:02:05]` → `t=3725` (1×3600 + 2×60 + 5 = 3725 seconds)

6. **Handle no results**
   - If no relevant segments are found in the transcript, clearly state that nothing matching the topic was found
   - Offer to search for a different topic in the same video

## Example Output

> **Segment 1 [04:32]**
> "This is where the speaker talks about the topic in detail..."
> https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=272

> **Segment 2 [12:15]**
> "Another relevant quote about the same topic..."
> https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=735
