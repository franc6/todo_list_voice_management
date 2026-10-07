"""Helpers for interpreting to-do items."""

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from hassil.util import remove_punctuation
from homeassistant.components.todo import TodoItem, TodoItemStatus
from homeassistant.util import dt as dt_util

# Matches "<name> (<digits>)"; \d also matches non-ASCII decimal digits,
# which int() understands.
_COUNT_PATTERN = re.compile(r"^(?P<name>.*?)\s*\((?P<count>\d+)\)$")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class ListEntry:
    """An item on a to-do list, with any count split out of its summary.

    :param name: The item's name, without the count
    :type name: str
    :param count: The count, or None if the summary has no count
    :type count: int | None
    :param item: The to-do item itself
    :type item: TodoItem
    """

    name: str
    count: int | None
    item: TodoItem

    @property
    def is_open(self) -> bool:
        """Return True if the item still needs action."""
        return self.item.status == TodoItemStatus.NEEDS_ACTION


def parse_summary(summary: str) -> tuple[str, int | None]:
    """Split "<name> (<digits>)" into name and count.

    :param summary: The summary of a to-do item
    :type summary: str
    :returns: The name, and the count or None if there is no count
    :rtype: tuple[str, int | None]
    """
    summary = summary.strip()
    if (match := _COUNT_PATTERN.match(summary)) and match["name"]:
        return match["name"], int(match["count"])
    return summary, None


def normalize(text: str) -> str:
    """Normalize text so spoken and written names can be compared.

    :param text: The text to normalize
    :type text: str
    :returns: The text without punctuation, case or extra whitespace
    :rtype: str
    """
    return _WHITESPACE.sub(" ", remove_punctuation(text)).strip().casefold()


def sort_key(name: str) -> tuple[str, str]:
    """Return a key for sorting names alphabetically.

    Case and accents are ignored, so "Äpfel" sorts with "apples" rather than
    after "zucchini"; names differing only in accents keep a stable order.

    :param name: The name to sort
    :type name: str
    :returns: The key
    :rtype: tuple[str, str]
    """
    folded = normalize(name)
    unaccented = "".join(
        char
        for char in unicodedata.normalize("NFKD", folded)
        if not unicodedata.combining(char)
    )
    return unaccented, folded


def alphabetical_order(entry: ListEntry) -> tuple[str, str]:
    """Return a key for sorting entries alphabetically by name.

    :param entry: The entry to sort
    :type entry: ListEntry
    :returns: The key
    :rtype: tuple[str, str]
    """
    return sort_key(entry.name)


def due_date_order(entry: ListEntry) -> tuple[bool, datetime]:
    """Return a key for sorting entries by due date, soonest first.

    Entries without a due date sort last.  A due date without a time counts
    as the start of that day in Home Assistant's time zone, so it sorts
    before items due at a time on the same day.

    :param entry: The entry to sort
    :type entry: ListEntry
    :returns: The key
    :rtype: tuple[bool, datetime]
    """
    due = entry.item.due
    if due is None:
        return True, datetime.min.replace(tzinfo=UTC)
    if not isinstance(due, datetime):
        return False, dt_util.start_of_local_day(due)
    if due.tzinfo is None:
        due = due.replace(tzinfo=dt_util.get_default_time_zone())
    return False, due


def to_entries(items: Iterable[TodoItem] | None) -> list[ListEntry]:
    """Convert to-do items to ListEntry objects, skipping empty summaries.

    :param items: The items of a to-do list
    :type items: Iterable[TodoItem] | None
    :returns: The entries, in list order
    :rtype: list[ListEntry]
    """
    entries = []
    for item in items or ():
        if not item.summary or not item.summary.strip():
            continue
        name, count = parse_summary(item.summary)
        entries.append(ListEntry(name, count, item))
    return entries


def find_entry(entries: Iterable[ListEntry], spoken: str) -> ListEntry | None:
    """Find the entry whose name matches spoken text.

    Open entries are preferred over completed ones.

    :param entries: The entries to search
    :type entries: Iterable[ListEntry]
    :param spoken: The item name as spoken
    :type spoken: str
    :returns: The best matching entry, or None
    :rtype: ListEntry | None
    """
    wanted = normalize(spoken)
    matches = [entry for entry in entries if normalize(entry.name) == wanted]
    for entry in matches:
        if entry.is_open:
            return entry
    return matches[0] if matches else None
