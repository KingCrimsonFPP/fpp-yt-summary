import os
import sys
from openai import OpenAI
from yt_transcript import extract_video_id, get_transcript

def summarize_transcript(transcript: str, url: str) -> str:
    """
    Sends the transcript to OpenAI and returns a summary.
    You can adjust the prompt to your liking.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    client = OpenAI(api_key=api_key)

    # If transcripts are very long, you might want to truncate or chunk them.
    # Here we just naively clip to avoid huge payloads:
    max_chars = 12000  # tune this depending on the model/context size
    transcript_snippet = transcript[:max_chars]

    prompt = f"""
You are an expert note-taker.

Video URL: {url}

Here is the transcript (or part of it):

\"\"\"{transcript_snippet}\"\"\"

Tasks:
1. Provide a concise summary (5–10 bullet points).
2. Highlight the main arguments or key ideas.
3. List any actionable recommendations or steps mentioned (if any).
4. If the transcript seems incomplete/truncated, mention that explicitly.

Return your answer in Markdown.
"""

    # Using the Chat Completions style for newer models
    response = client.chat.completions.create(
        model="gpt-4.1-mini",   # or another model you prefer
        messages=[
            {"role": "system", "content": "You summarize transcripts clearly and concisely."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content


def main():
    if len(sys.argv) < 2:
        print("Usage: python summarize_youtube.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]

    print(f"[*] Extracting transcript for: {url}")
    video_id = extract_video_id(url)
    transcript = get_transcript(video_id)

    print("[*] Transcript fetched. Sending to OpenAI for summarization...")
    summary = summarize_transcript(transcript, url)

    print("\n==== SUMMARY ====\n")
    print(summary)


if __name__ == "__main__":
    main()
