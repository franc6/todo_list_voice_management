"""Fixtures and helpers for tests."""

import uuid

import pytest
from homeassistant.components import conversation
from homeassistant.components.todo import (
    DOMAIN as TODO_DOMAIN,
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    setup_test_component_platform,
)

from custom_components.todo_list_voice_management.const import DOMAIN

ALL_FEATURES = (
    TodoListEntityFeature.CREATE_TODO_ITEM
    | TodoListEntityFeature.UPDATE_TODO_ITEM
    | TodoListEntityFeature.DELETE_TODO_ITEM
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in every test."""
    yield


def make_item(summary, status=TodoItemStatus.NEEDS_ACTION, **kwargs):
    """Return a TodoItem with a unique uid.

    :param summary: The summary of the item
    :type summary: str
    :param status: The status of the item
    :type status: TodoItemStatus
    :param kwargs: Additional TodoItem fields
    :returns: The item
    :rtype: TodoItem
    """
    return TodoItem(
        summary=summary, uid=str(uuid.uuid4()), status=status, **kwargs
    )


class MockTodoList(TodoListEntity):
    """A to-do list kept in memory."""

    _attr_has_entity_name = False

    def __init__(self, name, items=None, features=ALL_FEATURES):
        """Construct the list.

        :param name: The name of the list
        :type name: str
        :param items: The initial items
        :type items: list[TodoItem] | None
        :param features: The supported features
        :type features: TodoListEntityFeature
        """
        self._attr_name = name
        self._attr_unique_id = name.lower().replace(" ", "_")
        self._attr_todo_items = list(items or [])
        self._attr_supported_features = features
        self.fail_with = None
        # Items added at the source but not yet fetched, like a cloud list
        # between polls; async_update fetches them.
        self.unfetched = []
        self.fail_update_with = None

    async def async_update(self):
        """Fetch items added at the source."""
        if self.fail_update_with is not None:
            raise self.fail_update_with
        self._attr_todo_items.extend(self.unfetched)
        self.unfetched = []

    async def async_create_todo_item(self, item):
        """Add an item."""
        if self.fail_with is not None:
            raise self.fail_with
        item.uid = str(uuid.uuid4())
        self._attr_todo_items.append(item)
        self.async_write_ha_state()

    async def async_update_todo_item(self, item):
        """Replace an item."""
        self._attr_todo_items = [
            item if existing.uid == item.uid else existing
            for existing in self._attr_todo_items
        ]
        self.async_write_ha_state()

    async def async_delete_todo_items(self, uids):
        """Delete items."""
        self._attr_todo_items = [
            item for item in self._attr_todo_items if item.uid not in uids
        ]
        self.async_write_ha_state()


@pytest.fixture
def shopping_list():
    """Return a shopping list with a few items."""
    return MockTodoList(
        "Shopping List",
        [
            make_item("Milk (2)"),
            make_item("Eggs (1)"),
            make_item("Bread"),
            make_item("Butter", TodoItemStatus.COMPLETED),
        ],
    )


@pytest.fixture
def groceries():
    """Return an empty list whose name doesn't end with "list"."""
    return MockTodoList("Groceries")


@pytest.fixture
def todo_lists(request, shopping_list, groceries):
    """Return the to-do lists to set up.

    Tests can parametrize this indirectly with a function returning the
    lists, so each test gets fresh entities.
    """
    if hasattr(request, "param"):
        return request.param()
    return [shopping_list, groceries]


@pytest.fixture
async def setup_todo(hass: HomeAssistant, todo_lists):
    """Set up conversation and the to-do lists."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "conversation", {})
    setup_test_component_platform(hass, TODO_DOMAIN, todo_lists)
    assert await async_setup_component(
        hass, TODO_DOMAIN, {TODO_DOMAIN: {"platform": "test"}}
    )
    await hass.async_block_till_done()


@pytest.fixture
async def config_entry(hass: HomeAssistant, setup_todo):
    """Set up the integration and return its config entry."""
    entry = MockConfigEntry(domain=DOMAIN, title="To-do List Voice")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
def converse(hass: HomeAssistant):
    """Return a function that speaks to the default agent."""

    async def _converse(text, language="en"):
        result = await conversation.async_converse(
            hass, text, None, Context(), language=language
        )
        return result.response.speech["plain"]["speech"]

    return _converse
