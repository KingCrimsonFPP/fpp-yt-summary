import pytest

import channel_videos as cv
from channel_videos import apply_date_window, list_channel, normalize_channel_url


class TestNormalizeChannelUrl:
    @pytest.mark.parametrize("source", [
        "@somechannel",
        "https://www.youtube.com/@somechannel",
        "www.youtube.com/@somechannel",
        "https://www.youtube.com/@somechannel/",
        "https://www.youtube.com/@somechannel/videos",
        "https://www.youtube.com/@somechannel/shorts",
    ])
    def test_all_forms_collapse_to_one_base(self, source):
        assert normalize_channel_url(source) == "https://www.youtube.com/@somechannel"

    def test_keeps_channel_id_urls(self):
        url = "https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv"
        assert normalize_channel_url(url) == url

    def test_empty_is_rejected(self):
        with pytest.raises(ValueError):
            normalize_channel_url("   ")


class TestListChannel:
    def test_merges_tabs_and_dedupes(self, monkeypatch):
        """A video listed under both /videos and /shorts must appear once."""
        pages = {
            "https://www.youtube.com/@c/videos": [
                {"video_id": "aaaaaaaaaaa", "title": "long one"},
                {"video_id": "bbbbbbbbbbb", "title": "both tabs"},
            ],
            "https://www.youtube.com/@c/shorts": [
                {"video_id": "bbbbbbbbbbb", "title": "both tabs"},
                {"video_id": "ccccccccccc", "title": "a short"},
            ],
        }
        monkeypatch.setattr(cv, "flat_list", lambda url: (pages.get(url, []), None))

        result = list_channel("https://www.youtube.com/@c")
        assert [v["video_id"] for v in result] == ["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"]
        assert result[2]["tab"] == "shorts"

    def test_shorts_are_included(self, monkeypatch):
        """Shorts never appear under /videos, so a videos-only walk misses them."""
        monkeypatch.setattr(cv, "flat_list", lambda url: (
            ([{"video_id": "ccccccccccc", "title": "a short"}], None)
            if url.endswith("/shorts") else ([], None)
        ))
        assert [v["video_id"] for v in list_channel("https://www.youtube.com/@c")] == ["ccccccccccc"]

    def test_a_channel_without_shorts_still_lists(self, monkeypatch):
        """The /shorts tab 404s for channels that have none. That is normal and
        must not fail the listing."""
        monkeypatch.setattr(cv, "flat_list", lambda url: (
            ([{"video_id": "aaaaaaaaaaa", "title": "one"}], None)
            if url.endswith("/videos") else ([], "HTTP Error 404: Not Found")
        ))
        assert [v["video_id"] for v in list_channel("https://www.youtube.com/@c")] == ["aaaaaaaaaaa"]

    def test_reports_the_underlying_error_when_every_tab_fails(self, monkeypatch):
        """A wrong channel reference (display name instead of @handle) should say
        what yt-dlp said, not return an empty list."""
        monkeypatch.setattr(cv, "flat_list", lambda url: ([], "HTTP Error 404: Not Found"))
        with pytest.raises(RuntimeError, match="404"):
            list_channel("https://www.youtube.com/@wrong")


class TestApplyDateWindow:
    def video(self, vid, title="t"):
        return {"video_id": vid, "title": title, "tab": "videos"}

    def test_keeps_only_videos_inside_the_window(self, monkeypatch):
        monkeypatch.setattr(cv, "probe_upload_date", lambda vid: pytest.fail("should not probe"))
        videos = [self.video("aaaaaaaaaaa"), self.video("bbbbbbbbbbb")]
        known = {"aaaaaaaaaaa": "2026-08-30", "bbbbbbbbbbb": "2026-01-01"}

        kept = apply_date_window(videos, "2026-08-01", known)
        assert [v["video_id"] for v in kept] == ["aaaaaaaaaaa"]
        assert kept[0]["published"] == "2026-08-30"

    def test_probes_videos_the_rss_feed_missed(self, monkeypatch):
        """RSS carries ~15 entries; a burst channel pushes recent uploads past it."""
        monkeypatch.setattr(cv, "probe_upload_date", lambda vid: "2026-08-20")
        videos = [self.video("aaaaaaaaaaa"), self.video("bbbbbbbbbbb")]
        known = {"aaaaaaaaaaa": "2026-08-30"}

        kept = apply_date_window(videos, "2026-08-01", known)
        assert {v["video_id"] for v in kept} == {"aaaaaaaaaaa", "bbbbbbbbbbb"}

    def test_stops_probing_after_a_run_of_old_videos(self, monkeypatch):
        probed = []

        def probe(vid):
            probed.append(vid)
            return "2020-01-01"

        monkeypatch.setattr(cv, "probe_upload_date", probe)
        videos = [self.video(f"{c}" * 11) for c in "abcdefghij"]

        apply_date_window(videos, "2026-08-01", {}, stop_after_old=3)
        assert len(probed) == 3

    def test_undated_videos_are_dropped_without_ending_the_walk(self, monkeypatch):
        """An unaired premiere has no upload_date. It should not be ingested, and it
        should not be read as 'we have reached the old videos' either."""
        dates = {"bbbbbbbbbbb": "2026-08-30"}
        monkeypatch.setattr(cv, "probe_upload_date", lambda vid: dates.get(vid, ""))
        videos = [self.video("aaaaaaaaaaa"), self.video("bbbbbbbbbbb")]

        kept = apply_date_window(videos, "2026-08-01", {}, stop_after_old=1)
        assert [v["video_id"] for v in kept] == ["bbbbbbbbbbb"]

    def test_result_is_newest_first(self, monkeypatch):
        monkeypatch.setattr(cv, "probe_upload_date", lambda vid: "")
        videos = [self.video("aaaaaaaaaaa"), self.video("bbbbbbbbbbb"), self.video("ccccccccccc")]
        known = {
            "aaaaaaaaaaa": "2026-08-10",
            "bbbbbbbbbbb": "2026-08-30",
            "ccccccccccc": "2026-08-20",
        }
        kept = apply_date_window(videos, "2026-08-01", known)
        assert [v["published"] for v in kept] == ["2026-08-30", "2026-08-20", "2026-08-10"]
