import sweep as sweep_module
from sweep import read_manifest, sweep


class TestReadManifest:
    def test_reads_channels_ignoring_comments_and_blanks(self, tmp_path):
        manifest = tmp_path / "channels.txt"
        manifest.write_text(
            "# my channels\n"
            "@alpha\n"
            "\n"
            "https://www.youtube.com/@beta   # trailing note\n"
            "   \n",
            encoding="utf-8",
        )
        assert read_manifest(manifest) == [
            "https://www.youtube.com/@alpha",
            "https://www.youtube.com/@beta",
        ]

    def test_dedupes_equivalent_forms_of_one_channel(self, tmp_path):
        """The same channel written three ways should be polled once."""
        manifest = tmp_path / "channels.txt"
        manifest.write_text(
            "@alpha\n"
            "https://www.youtube.com/@alpha\n"
            "https://www.youtube.com/@alpha/videos\n",
            encoding="utf-8",
        )
        assert read_manifest(manifest) == ["https://www.youtube.com/@alpha"]

    def test_empty_manifest(self, tmp_path):
        manifest = tmp_path / "channels.txt"
        manifest.write_text("# nothing here\n", encoding="utf-8")
        assert read_manifest(manifest) == []


class TestSweep:
    def manifest(self, tmp_path):
        path = tmp_path / "channels.txt"
        path.write_text("@alpha\n", encoding="utf-8")
        return path

    def stub_channel(self, monkeypatch, videos):
        monkeypatch.setattr(sweep_module.cv, "list_channel", lambda url: videos)
        monkeypatch.setattr(sweep_module.cv, "channel_id", lambda url: "UC123")
        monkeypatch.setattr(sweep_module.cv, "rss_dates", lambda cid: {
            v["video_id"]: "2026-08-30" for v in videos
        })

    def test_dry_run_reports_without_ingesting(self, tmp_path, monkeypatch):
        self.stub_channel(monkeypatch, [{"video_id": "aaaaaaaaaaa", "title": "one", "tab": "videos"}])
        monkeypatch.setattr(sweep_module, "ingest",
                            lambda *a, **k: pytest_fail_ingest())

        result = sweep(self.manifest(tmp_path), tmp_path / "out", since_days=3650, dry_run=True)
        assert result["ingested"] == 0
        assert [c["video_id"] for c in result["candidates"]] == ["aaaaaaaaaaa"]

    def test_ingests_candidates(self, tmp_path, monkeypatch):
        self.stub_channel(monkeypatch, [
            {"video_id": "aaaaaaaaaaa", "title": "one", "tab": "videos"},
            {"video_id": "bbbbbbbbbbb", "title": "two", "tab": "videos"},
        ])
        seen = []

        def fake_ingest(video_id, output_dir):
            seen.append(video_id)
            return {"slug": f"s-{video_id}", "skipped": False, "path": "p"}

        monkeypatch.setattr(sweep_module, "ingest", fake_ingest)
        result = sweep(self.manifest(tmp_path), tmp_path / "out", since_days=3650, pace=0)

        assert result["ingested"] == 2
        assert seen == ["aaaaaaaaaaa", "bbbbbbbbbbb"]

    def test_already_ingested_videos_are_never_fetched(self, tmp_path, monkeypatch):
        """Idempotency: a second sweep over unchanged channels does no work."""
        self.stub_channel(monkeypatch, [{"video_id": "aaaaaaaaaaa", "title": "one", "tab": "videos"}])
        monkeypatch.setattr(sweep_module, "ingested_video_ids", lambda d: {"aaaaaaaaaaa"})
        monkeypatch.setattr(sweep_module, "ingest",
                            lambda *a, **k: pytest_fail_ingest())

        result = sweep(self.manifest(tmp_path), tmp_path / "out", since_days=3650, pace=0)
        assert result == {"ingested": 0, "skipped": 0, "failed": 0, "candidates": []}

    def test_unaired_premiere_is_skipped_not_failed(self, tmp_path, monkeypatch):
        self.stub_channel(monkeypatch, [{"video_id": "aaaaaaaaaaa", "title": "soon", "tab": "videos"}])

        def premiere(video_id, output_dir):
            raise RuntimeError("ERROR: This live event will begin in 2 hours")

        monkeypatch.setattr(sweep_module, "ingest", premiere)
        result = sweep(self.manifest(tmp_path), tmp_path / "out", since_days=3650, pace=0)

        assert result["skipped"] == 1
        assert result["failed"] == 0

    def test_rate_limit_retries_the_same_video_then_gives_up(self, tmp_path, monkeypatch):
        self.stub_channel(monkeypatch, [{"video_id": "aaaaaaaaaaa", "title": "one", "tab": "videos"}])
        attempts = []

        def blocked(video_id, output_dir):
            attempts.append(video_id)
            raise RuntimeError("HTTP Error 429: Too Many Requests")

        monkeypatch.setattr(sweep_module, "ingest", blocked)
        monkeypatch.setattr(sweep_module.time, "sleep", lambda s: None)

        result = sweep(self.manifest(tmp_path), tmp_path / "out",
                       since_days=3650, pace=0, max_block=3)

        assert attempts == ["aaaaaaaaaaa"] * 3  # retried the same id, never advanced past it
        assert result["ingested"] == 0

    def test_ordinary_failure_advances_to_the_next_video(self, tmp_path, monkeypatch):
        self.stub_channel(monkeypatch, [
            {"video_id": "aaaaaaaaaaa", "title": "one", "tab": "videos"},
            {"video_id": "bbbbbbbbbbb", "title": "two", "tab": "videos"},
        ])

        def fail_first(video_id, output_dir):
            if video_id == "aaaaaaaaaaa":
                raise RuntimeError("transcripts are disabled")
            return {"slug": "s", "skipped": False, "path": "p"}

        monkeypatch.setattr(sweep_module, "ingest", fail_first)
        result = sweep(self.manifest(tmp_path), tmp_path / "out", since_days=3650, pace=0)

        assert result["failed"] == 1
        assert result["ingested"] == 1


def pytest_fail_ingest():
    raise AssertionError("ingest must not be called")
