import pytest

import yt_transcript
from yt_transcript import (
    extract_video_id,
    fetch_segments,
    format_timestamp,
    load_last_video,
    parse_vtt,
    render,
    save_last_video,
    vtt_time_to_seconds,
)

VID = "Vitf8YaVXhc"


class TestExtractVideoId:
    @pytest.mark.parametrize("source", [
        VID,
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtu.be/{VID}",
        f"https://youtu.be/{VID}?si=abc123",
        f"https://www.youtu.be/{VID}",
        f"https://www.youtube.com/shorts/{VID}",
        f"https://www.youtube.com/embed/{VID}",
        f"https://www.youtube.com/live/{VID}",
        f"https://m.youtube.com/watch?v={VID}&feature=share",
        f"https://www.youtube.com/watch?list=PLxxx&v={VID}",
    ])
    def test_resolves(self, source):
        assert extract_video_id(source) == VID

    def test_strips_surrounding_whitespace(self):
        assert extract_video_id(f"  {VID}  ") == VID


class TestFormatTimestamp:
    def test_seconds_only(self):
        assert format_timestamp(45.0) == "[00:45]"

    def test_minutes(self):
        assert format_timestamp(125.0) == "[02:05]"

    def test_hours(self):
        assert format_timestamp(3725.0) == "[01:02:05]"

    def test_zero_and_none_are_safe(self):
        assert format_timestamp(0) == "[00:00]"
        assert format_timestamp(None) == "[00:00]"


class TestVttParsing:
    def test_time_to_seconds(self):
        assert vtt_time_to_seconds("00:01:23.456") == pytest.approx(83.456)
        assert vtt_time_to_seconds("01:23.500") == pytest.approx(83.5)

    def test_parses_cues_to_seconds_and_text(self):
        vtt = (
            "WEBVTT\nKind: captions\nLanguage: en\n\n"
            "00:00:01.000 --> 00:00:03.000\nhello world\n\n"
            "00:01:23.000 --> 00:01:25.000\nsecond cue\n"
        )
        assert parse_vtt(vtt) == [(1.0, "hello world"), (83.0, "second cue")]

    def test_drops_rolling_caption_repeats(self):
        """Auto-generated captions repeat the previous line as they scroll; each
        distinct line should survive exactly once."""
        vtt = (
            "WEBVTT\n\n"
            "00:00:01.000 --> 00:00:03.000\nfirst line\n\n"
            "00:00:03.000 --> 00:00:05.000\nfirst line\nsecond line\n\n"
            "00:00:05.000 --> 00:00:07.000\nsecond line\nthird line\n"
        )
        assert [text for _, text in parse_vtt(vtt)] == ["first line", "second line", "third line"]

    def test_strips_karaoke_tags_and_unescapes_entities(self):
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n<c.colorE5E5E5>Tom &amp; Jerry</c>\n"
        assert parse_vtt(vtt) == [(1.0, "Tom & Jerry")]

    def test_empty_vtt_raises(self):
        with pytest.raises(RuntimeError):
            parse_vtt("WEBVTT\n\n")


class TestRender:
    segments = [(0.0, "alpha"), (65.0, "beta")]

    def test_with_timestamps(self):
        assert render(self.segments, True) == "[00:00] alpha\n[01:05] beta"

    def test_without_timestamps(self):
        assert render(self.segments, False) == "alpha beta"


class TestFetchSegments:
    def test_prefers_the_api(self, monkeypatch):
        monkeypatch.delenv("YT_NO_API", raising=False)
        monkeypatch.setattr(yt_transcript, "via_api", lambda v, l=None: [(0.0, "api")])
        monkeypatch.setattr(yt_transcript, "via_ytdlp", lambda v: [(0.0, "ytdlp")])
        assert fetch_segments(VID) == ([(0.0, "api")], "api")

    def test_falls_back_to_ytdlp_when_the_api_fails(self, monkeypatch):
        monkeypatch.delenv("YT_NO_API", raising=False)

        def boom(video_id, languages=None):
            raise RuntimeError("api blocked")

        monkeypatch.setattr(yt_transcript, "via_api", boom)
        monkeypatch.setattr(yt_transcript, "via_ytdlp", lambda v: [(0.0, "ytdlp")])
        assert fetch_segments(VID) == ([(0.0, "ytdlp")], "ytdlp")

    def test_yt_no_api_skips_the_api_entirely(self, monkeypatch):
        monkeypatch.setenv("YT_NO_API", "1")

        def must_not_run(video_id, languages=None):
            raise AssertionError("the API should not be called when YT_NO_API is set")

        monkeypatch.setattr(yt_transcript, "via_api", must_not_run)
        monkeypatch.setattr(yt_transcript, "via_ytdlp", lambda v: [(0.0, "ytdlp")])
        assert fetch_segments(VID) == ([(0.0, "ytdlp")], "ytdlp")

    def test_reports_both_failures_when_neither_source_works(self, monkeypatch):
        monkeypatch.delenv("YT_NO_API", raising=False)

        def api_boom(video_id, languages=None):
            raise RuntimeError("api blocked")

        def ytdlp_boom(video_id):
            raise RuntimeError("no vtt written")

        monkeypatch.setattr(yt_transcript, "via_api", api_boom)
        monkeypatch.setattr(yt_transcript, "via_ytdlp", ytdlp_boom)
        with pytest.raises(RuntimeError, match="api blocked.*no vtt written"):
            fetch_segments(VID)


class TestLastVideoState:
    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(yt_transcript, "STATE_FILE", tmp_path / ".last_video")
        save_last_video(VID)
        assert load_last_video() == VID

    def test_returns_none_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(yt_transcript, "STATE_FILE", tmp_path / ".last_video")
        assert load_last_video() is None
