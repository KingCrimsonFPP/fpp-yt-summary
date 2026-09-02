import ingest_video
from ingest_video import (
    build_document,
    ingest,
    ingested_video_ids,
    resolve_target,
    transcript_video_id,
)

VID = "Vitf8YaVXhc"
OTHER = "dQw4w9WgXcQ"


def write_source_set(root, slug, video_id):
    folder = root / slug
    folder.mkdir(parents=True)
    (folder / f"transcript.{slug}.md").write_text(
        f"---\nvideo_id: {video_id}\n---\n# t\n", encoding="utf-8"
    )
    return folder


class TestTranscriptVideoId:
    def test_reads_the_id_from_frontmatter(self, tmp_path):
        folder = write_source_set(tmp_path, "chan-title", VID)
        assert transcript_video_id(folder / "transcript.chan-title.md") == VID

    def test_missing_file_is_none(self, tmp_path):
        assert transcript_video_id(tmp_path / "nope.md") is None


class TestIngestedVideoIds:
    def test_collects_across_folders(self, tmp_path):
        write_source_set(tmp_path, "a-one", VID)
        write_source_set(tmp_path, "b-two", OTHER)
        assert ingested_video_ids(tmp_path) == {VID, OTHER}

    def test_empty_directory(self, tmp_path):
        assert ingested_video_ids(tmp_path) == set()


class TestResolveTarget:
    def test_fresh_video_is_not_already_ingested(self, tmp_path):
        target, already = resolve_target(tmp_path, "chan-title", VID)
        assert target == tmp_path / "chan-title"
        assert already is False

    def test_same_video_again_is_recognised(self, tmp_path):
        write_source_set(tmp_path, "chan-title", VID)
        target, already = resolve_target(tmp_path, "chan-title", VID)
        assert target == tmp_path / "chan-title"
        assert already is True

    def test_colliding_slug_gets_its_own_folder(self, tmp_path):
        """A re-upload slugs identically to the original. It must not overwrite
        the existing transcript."""
        write_source_set(tmp_path, "chan-title", VID)
        target, already = resolve_target(tmp_path, "chan-title", OTHER)
        assert target == tmp_path / f"chan-title-{OTHER}"
        assert already is False

    def test_already_disambiguated_collision_is_recognised(self, tmp_path):
        write_source_set(tmp_path, "chan-title", VID)
        write_source_set(tmp_path, f"chan-title-{OTHER}", OTHER)
        _, already = resolve_target(tmp_path, "chan-title", OTHER)
        assert already is True


class TestBuildDocument:
    def test_quotes_titles_containing_yaml_metacharacters(self):
        doc = build_document(
            VID, 'Rust: the "why" # explained', "Some Channel",
            "2026-01-02", "2026-09-01", "api", [(0.0, "hi")],
        )
        assert 'title: "Rust: the \\"why\\" # explained"' in doc

    def test_includes_metadata_and_timestamped_body(self):
        doc = build_document(
            VID, "Title", "Chan", "2026-01-02", "2026-09-01", "api",
            [(0.0, "first"), (65.0, "second")],
        )
        assert f"video_id: {VID}" in doc
        assert "fetched_via: api" in doc
        assert "published: 2026-01-02" in doc
        assert "[00:00] first" in doc
        assert "[01:05] second" in doc

    def test_falls_back_to_the_id_as_heading(self):
        doc = build_document(VID, "", "", "", "2026-09-01", "api", [(0.0, "x")])
        assert f"# {VID}" in doc

    def test_contains_no_cortex_paths(self):
        doc = build_document(VID, "T", "C", "", "2026-09-01", "api", [(0.0, "x")])
        assert ".cortex" not in doc
        assert "inquiry/sources" not in doc


class TestIngest:
    def _stub(self, monkeypatch, segments=None):
        monkeypatch.setattr(ingest_video, "fetch_metadata",
                            lambda vid: ("A Talk", "Some Channel", "20260102"))
        monkeypatch.setattr(ingest_video.yt, "fetch_segments",
                            lambda vid: (segments or [(0.0, "hello")], "api"))

    def test_writes_a_source_set(self, tmp_path, monkeypatch):
        self._stub(monkeypatch)
        result = ingest(f"https://www.youtube.com/watch?v={VID}", tmp_path)

        assert result["slug"] == "some-channel-a-talk"
        assert result["skipped"] is False
        written = tmp_path / "some-channel-a-talk" / "transcript.some-channel-a-talk.md"
        assert written.exists()
        assert "[00:00] hello" in written.read_text(encoding="utf-8")

    def test_second_run_skips_without_refetching(self, tmp_path, monkeypatch):
        self._stub(monkeypatch)
        ingest(VID, tmp_path)

        def must_not_run(vid):
            raise AssertionError("an already-ingested video must not be refetched")

        monkeypatch.setattr(ingest_video.yt, "fetch_segments", must_not_run)
        assert ingest(VID, tmp_path)["skipped"] is True

    def test_force_refetches(self, tmp_path, monkeypatch):
        self._stub(monkeypatch)
        ingest(VID, tmp_path)
        self._stub(monkeypatch, segments=[(1.0, "refetched")])
        result = ingest(VID, tmp_path, force=True)

        assert result["skipped"] is False
        written = tmp_path / result["slug"] / f"transcript.{result['slug']}.md"
        assert "refetched" in written.read_text(encoding="utf-8")

    def test_missing_metadata_still_yields_a_unique_slug(self, tmp_path, monkeypatch):
        def no_metadata(vid):
            raise RuntimeError("yt-dlp unavailable")

        monkeypatch.setattr(ingest_video, "fetch_metadata", no_metadata)
        monkeypatch.setattr(ingest_video.yt, "fetch_segments", lambda vid: ([(0.0, "x")], "api"))

        first = ingest(VID, tmp_path)
        second = ingest(OTHER, tmp_path)
        assert first["slug"] != second["slug"]
