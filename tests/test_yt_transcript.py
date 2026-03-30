# tests/test_yt_transcript.py
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yt_transcript import extract_video_id

def test_bare_id_returned_as_is():
    assert extract_video_id("Vitf8YaVXhc") == "Vitf8YaVXhc"

def test_watch_url():
    assert extract_video_id("https://www.youtube.com/watch?v=Vitf8YaVXhc") == "Vitf8YaVXhc"

def test_short_url():
    assert extract_video_id("https://youtu.be/Vitf8YaVXhc") == "Vitf8YaVXhc"

def test_short_url_with_params():
    assert extract_video_id("https://youtu.be/Vitf8YaVXhc?si=abc123") == "Vitf8YaVXhc"

def test_www_short_url():
    assert extract_video_id("https://www.youtu.be/Vitf8YaVXhc") == "Vitf8YaVXhc"

from yt_transcript import format_timestamp

def test_format_timestamp_seconds_only():
    assert format_timestamp(45.0) == "[00:45]"

def test_format_timestamp_minutes():
    assert format_timestamp(125.0) == "[02:05]"

def test_format_timestamp_hours():
    assert format_timestamp(3725.0) == "[01:02:05]"

import tempfile
from pathlib import Path
from unittest.mock import patch
from yt_transcript import save_last_video, load_last_video

def test_save_and_load_last_video(tmp_path):
    state_file = tmp_path / ".last_video"
    with patch("yt_transcript.STATE_FILE", state_file):
        save_last_video("Vitf8YaVXhc")
        assert load_last_video() == "Vitf8YaVXhc"

def test_load_last_video_returns_none_when_missing(tmp_path):
    state_file = tmp_path / ".last_video"
    with patch("yt_transcript.STATE_FILE", state_file):
        assert load_last_video() is None
