"""Actions behind each kind of sentence."""

import logging
from dataclasses import replace
from typing import Any, Callable

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.exceptions import HomeAssistantError

from .const import (
    RESPONSE_ADD_NOT_SUPPORTED,
    RESPONSE_ITEM_ADDED,
    RESPONSE_ITEM_ALREADY_ON_LIST,
    RESPONSE_ITEM_ALREADY_ON_LIST_COUNT,
    RESPONSE_ITEM_NOT_ON_LIST,
    RESPONSE_ITEM_ON_LIST,
    RESPONSE_ITEM_ON_LIST_COUNT,
    RESPONSE_LIST_CONTENTS,
    RESPONSE_LIST_EMPTY,
)
from .items import ListEntry, find_entry, to_entries
from .language import Language

_LOGGER = logging.getLogger(__name__)


async def _async_entries(entity: TodoListEntity) -> list[ListEntry]:
    """Refresh a list from its source, then return its entries.

    Lists backed by a cloud service only poll every so often, so their
    items may be out of date.  If the refresh fails, the items already
    known are used.
    """
    try:
        await entity.async_update_ha_state(force_refresh=True)
    except HomeAssistantError as err:
        _LOGGER.warning("Unable to refresh %s: %s", entity.entity_id, err)
    return to_entries(entity.todo_items)


async def _async_open_entry(
    entity: TodoListEntity, spoken: str
) -> ListEntry | None:
    """Return the open entry matching spoken, if any."""
    entry = find_entry(await _async_entries(entity), spoken)
    return entry if entry is not None and entry.is_open else None


def _found_response(
    language: Language,
    list_name: str,
    entry: ListEntry,
    keys: tuple[str, str],
) -> str:
    """Render keys[0], or keys[1] if the entry has a count."""
    if entry.count is None:
        return language.respond(keys[0], list_name, item=entry.name)
    return language.respond(
        keys[1], list_name, item=entry.name, count=entry.count
    )


async def async_is_on_list(
    language: Language, entity: TodoListEntity, list_name: str, spoken: str
) -> str:
    """Answer whether an item is on a list.

    :param language: The language to answer in
    :type language: Language
    :param entity: The to-do list
    :type entity: TodoListEntity
    :param list_name: The name the user used for the list
    :type list_name: str
    :param spoken: The item, as spoken
    :type spoken: str
    :returns: The response
    :rtype: str
    """
    if (entry := await _async_open_entry(entity, spoken)) is None:
        return language.respond(
            RESPONSE_ITEM_NOT_ON_LIST, list_name, item=spoken
        )
    return _found_response(
        language,
        list_name,
        entry,
        (RESPONSE_ITEM_ON_LIST, RESPONSE_ITEM_ON_LIST_COUNT),
    )


async def async_list_items(
    language: Language,
    entity: TodoListEntity,
    list_name: str,
    order: Callable[[ListEntry], Any] | None = None,
) -> str:
    """Read the open items on a list.

    :param language: The language to answer in
    :type language: Language
    :param entity: The to-do list
    :type entity: TodoListEntity
    :param list_name: The name the user used for the list
    :type list_name: str
    :param order: A sort key for reading the items in some other order
        than the list's, or None for the list's order
    :type order: Callable[[ListEntry], Any] | None
    :returns: The response
    :rtype: str
    """
    entries = [e for e in await _async_entries(entity) if e.is_open]
    if order is not None:
        entries.sort(key=order)
    if not entries:
        return language.respond(RESPONSE_LIST_EMPTY, list_name)
    return language.respond(
        RESPONSE_LIST_CONTENTS,
        list_name,
        items=language.join([language.list_entry(e) for e in entries]),
        item_count=len(entries),
    )


async def async_add_if_missing(
    language: Language, entity: TodoListEntity, list_name: str, spoken: str
) -> str:
    """Add an item to a list unless it's already there.

    A completed item with the same name is marked as needing action again,
    instead of adding a duplicate, when the list supports it.

    :param language: The language to answer in
    :type language: Language
    :param entity: The to-do list
    :type entity: TodoListEntity
    :param list_name: The name the user used for the list
    :type list_name: str
    :param spoken: The item, as spoken
    :type spoken: str
    :returns: The response
    :rtype: str
    """
    entry = find_entry(await _async_entries(entity), spoken)
    if entry is not None and entry.is_open:
        return _found_response(
            language,
            list_name,
            entry,
            (
                RESPONSE_ITEM_ALREADY_ON_LIST,
                RESPONSE_ITEM_ALREADY_ON_LIST_COUNT,
            ),
        )

    features = entity.supported_features or 0
    if (
        entry is not None
        and entry.item.uid
        and features & TodoListEntityFeature.UPDATE_TODO_ITEM
    ):
        # Keep the due date, description, etc.
        await entity.async_update_todo_item(
            replace(
                entry.item, status=TodoItemStatus.NEEDS_ACTION, completed=None
            )
        )
        return language.respond(
            RESPONSE_ITEM_ADDED, list_name, item=entry.name
        )

    if not features & TodoListEntityFeature.CREATE_TODO_ITEM:
        return language.respond(RESPONSE_ADD_NOT_SUPPORTED, list_name)

    # Capitalize the first letter, like HA's own HassListAddItem intent.
    summary = spoken[:1].upper() + spoken[1:]
    await entity.async_create_todo_item(
        TodoItem(summary=summary, status=TodoItemStatus.NEEDS_ACTION)
    )
    return language.respond(RESPONSE_ITEM_ADDED, list_name, item=spoken)
