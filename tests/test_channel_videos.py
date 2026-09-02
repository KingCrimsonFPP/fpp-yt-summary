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

    def test_a_handle_named_after_a_tab_is_not_eaten(self):
        """Stripping trailing tabs unconditionally would turn the handle
        '@videos' into the bare youtube.com root."""
        assert normalize_channel_url("@videos") == "https://www.youtube.com/@videos"
        assert normalize_channel_url("@shorts") == "https://www.youtube.com/@shorts"

    def test_bare_handle_with_a_tab_suffix_is_stripped(self):
        assert normalize_channel_url("@somechannel/videos") == "https://www.youtube.com/@somechannel"


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

    def test_early_stop_is_per_tab_so_shorts_survive(self, monkeypatch):
        """Regression: with one counter shared across the merged tab list, the
        walk breaks inside /videos — every channel has more than stop_after_old
        old uploads — and no short is ever examined."""
        monkeypatch.setattr(cv, "probe_upload_date", lambda vid: "")
        videos = [
            {"video_id": f"v{i:010d}", "title": f"v{i}", "tab": "videos"} for i in range(8)
        ] + [
            {"video_id": f"s{i:010d}", "title": f"s{i}", "tab": "shorts"} for i in range(3)
        ]
        known = {"v0000000000": "2026-08-30"}
        known.update({f"v{i:010d}": "2020-01-01" for i in range(1, 8)})
        known.update({f"s{i:010d}": "2026-08-29" for i in range(3)})

        kept = apply_date_window(videos, "2026-08-25", known, stop_after_old=5)
        assert [v["video_id"] for v in kept if v["tab"] == "shorts"] == [
            "s0000000000", "s0000000001", "s0000000002",
        ]
        assert "v0000000000" in [v["video_id"] for v in kept]

    def test_probes_are_paced(self, monkeypatch):
        """Probing is one request per video; unpaced it can trip the very rate
        limit the ingest phase is built to survive."""
        slept = []
        monkeypatch.setattr(cv, "probe_upload_date", lambda vid: "2026-08-30")
        monkeypatch.setattr(cv.time, "sleep", lambda s: slept.append(s))
        videos = [self.video(f"{c}" * 11) for c in "abc"]

        apply_date_window(videos, "2026-08-01", {}, pace=2.0)
        assert slept == [2.0, 2.0]  # between probes, not before the first

    def test_no_sleeping_when_rss_covered_everything(self, monkeypatch):
        monkeypatch.setattr(cv, "probe_upload_date", lambda vid: pytest.fail("should not probe"))
        monkeypatch.setattr(cv.time, "sleep", lambda s: pytest.fail("should not sleep"))
        videos = [self.video("aaaaaaaaaaa")]
        apply_date_window(videos, "2026-08-01", {"aaaaaaaaaaa": "2026-08-30"}, pace=5.0)

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
