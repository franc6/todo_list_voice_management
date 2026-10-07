"""Tests for items.py."""

import datetime

import pytest
from homeassistant.components.todo import TodoItem, TodoItemStatus

from custom_components.todo_list_voice_management.items import (
    due_date_order,
    find_entry,
    normalize,
    parse_summary,
    sort_key,
    to_entries,
)

from .conftest import make_item


@pytest.mark.parametrize(
    ("summary", "expected"),
    [
        ("Milk", ("Milk", None)),
        ("Milk (2)", ("Milk", 2)),
        ("Milk(12)", ("Milk", 12)),
        ("  Paper towels (3)  ", ("Paper towels", 3)),
        ("Milk (0)", ("Milk", 0)),
        ("Milk (٣)", ("Milk", 3)),  # Arabic-Indic digit three
        ("Milk (2) extra", ("Milk (2) extra", None)),
        ("Milk (two)", ("Milk (two)", None)),
        ("Milk (-2)", ("Milk (-2)", None)),
        ("(2)", ("(2)", None)),
        ("Batteries (AA) (4)", ("Batteries (AA)", 4)),
    ],
)
def test_parse_summary(summary, expected):
    """Test splitting counts from summaries."""
    assert parse_summary(summary) == expected


def test_normalize():
    """Test normalizing text for comparison."""
    assert normalize("  Peanut   BUTTER! ") == "peanut butter"
    assert normalize("Ben's") == normalize("ben's")


def test_to_entries_skips_empty_summaries():
    """Test that items without a summary are ignored."""
    entries = to_entries(
        [TodoItem(summary=None), TodoItem(summary="  "), make_item("Eggs (6)")]
    )
    assert [(entry.name, entry.count) for entry in entries] == [("Eggs", 6)]
    assert to_entries(None) == []


def test_find_entry_prefers_open_items():
    """Test that an open item wins over a completed one with the same name."""
    done = make_item("Milk", TodoItemStatus.COMPLETED)
    still_needed = make_item("milk (2)")
    entries = to_entries([done, still_needed])

    entry = find_entry(entries, "MILK")
    assert entry.item is still_needed
    assert entry.is_open

    entry = find_entry(to_entries([done]), "milk")
    assert entry.item is done
    assert not entry.is_open

    assert find_entry(entries, "eggs") is None


def test_sort_key():
    """Test that sorting ignores case and accents."""
    names = ["zucchini", "Éclairs", "eclairs", "Apples", "bananas"]
    assert sorted(names, key=sort_key) == [
        "Apples",
        "bananas",
        "eclairs",
        "Éclairs",
        "zucchini",
    ]


def test_due_date_order():
    """Test sorting by due date, with undated entries last."""
    entries = to_entries(
        [
            make_item("Undated"),
            make_item("Naive", due=datetime.datetime(2026, 10, 10, 12, 0)),
            make_item(
                "Aware",
                due=datetime.datetime(
                    2026, 10, 10, 11, 0, tzinfo=datetime.UTC
                ),
            ),
            make_item("Date", due=datetime.date(2026, 10, 10)),
        ]
    )
    assert [e.name for e in sorted(entries, key=due_date_order)] == [
        "Date",
        "Aware",
        "Naive",
        "Undated",
    ]
