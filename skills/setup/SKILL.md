---
name: yt-summary:setup
description: Set up the yt-summary plugin by installing required dependencies, or install youtube-transcript-api if another yt-summary skill fails due to missing dependencies
---

# Setup yt-summary Plugin

The user is setting up the yt-summary plugin or one of its skills has failed due to missing the `youtube-transcript-api` dependency.

## Task

Install the required Python dependency for the yt-summary plugin:

1. Run `pip install youtube-transcript-api`
2. Wait for the installation to complete successfully
3. Confirm success with a message indicating the dependency is now installed
4. Inform the user that they can now use the summarize, transcript, and ask skills

## Notes

- The `youtube-transcript-api` package is required by the plugin's transcript fetching functionality
- This dependency is specified in the `requirements.txt` file at the plugin root
- The script that uses this dependency is `scripts/yt_transcript.py` within the plugin directory
