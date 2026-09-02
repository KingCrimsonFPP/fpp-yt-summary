from slug import slugify


def test_basic_author_title():
    assert slugify("Some Channel", "A Great Talk") == "some-channel-a-great-talk"


def test_punctuation_is_dropped():
    assert slugify("Dr. Who?!", "Time & Space") == "dr-who-time-space"


def test_collapses_runs_of_separators():
    assert slugify("a   b", "c___d") == "a-b-c-d"


def test_truncates_to_maxlen_without_trailing_dash():
    slug = slugify("channel", "x" * 200, maxlen=20)
    assert len(slug) <= 20
    assert not slug.endswith("-")


def test_fallback_fills_missing_author_and_title():
    assert slugify("", "", fallback="dQw4w9WgXcQ") == "dqw4w9wgxcq-dqw4w9wgxcq"


def test_two_videos_without_metadata_do_not_collide():
    """Without the id fallback both would slug to 'unknown-untitled' and the
    second ingest would land on top of the first."""
    assert slugify("", "", fallback="aaaaaaaaaaa") != slugify("", "", fallback="bbbbbbbbbbb")


def test_defaults_when_nothing_is_known():
    assert slugify("", "") == "unknown-untitled"
