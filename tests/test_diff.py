from watchx.diff import diff_lines, intraline_spans


def test_first_frame_has_no_changes() -> None:
    result = diff_lines(None, ("a", "b"))
    assert result.changed_count == 0
    assert [item.kind for item in result.lines] == ["same", "same"]


def test_replace_highlights_new_content() -> None:
    result = diff_lines(("a", "b"), ("a", "c"))
    assert result.changed_count >= 1
    assert any(item.kind == "changed" for item in result.lines)


def test_intraline_spans_mark_only_changed_text() -> None:
    assert intraline_spans("cpu: 10%", "cpu: 20%") == (
        ("cpu: ", False),
        ("2", True),
        ("0%", False),
    )
