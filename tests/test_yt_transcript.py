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
