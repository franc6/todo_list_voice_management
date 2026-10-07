"""Tests for manager.py that are awkward to reach through conversation."""

from types import SimpleNamespace

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.todo_list_voice_management.manager import (
    name_expression,
    template_name,
)

from .conftest import MockTodoList


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Shopping List", "shopping list"),
        ("  Groceries  ", "groceries"),
        ("Bob's (weekend) [list]", "bob's weekend list"),
        ("a|b <c> {d}; e\\f", "a b c d e f"),
        ("!!!", ""),
    ],
)
def test_template_name(name, expected):
    """Test making list names safe for hassil templates."""
    assert template_name(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("groceries", "(groceries)"),
        ("to do", "(to do|todo)"),
        ("home to do", "(home to do|hometo do|home todo)"),
        ("to-do", "((to-do|to do|todo))"),
        (
            "garden to-do",
            "(garden (to-do|to do|todo)"
            "|(gardento-do|gardento do|gardentodo))",
        ),
        ("x--ray", "((x--ray|x ray|xray))"),
    ],
)
def test_name_expression(name, expected):
    """Test matching list names with different spacing and hyphens."""
    assert name_expression(name) == expected


async def test_sentences_and_unknown_targets(hass, config_entry):
    """Test sentence generation and results that aren't ours."""
    manager = config_entry.runtime_data
    sentences = manager.sentences
    assert "is {item} on [the|my|our] (groceries) [list]" not in sentences
    assert any("(groceries)" in sentence for sentence in sentences)

    # pylint: disable-next=protected-access
    handle = manager._async_handle_trigger
    assert await handle(None, SimpleNamespace(intent_sentence=None)) is None
    unknown = SimpleNamespace(
        intent_sentence=SimpleNamespace(text="not one of ours"), entities={}
    )
    assert await handle(None, unknown) is None


async def test_unavailable_list(hass, config_entry, converse, groceries):
    """Test answering for a list whose entity is gone but still registered.

    HA leaves a restored "unavailable" state behind, so the sentences stay
    and the user hears that something went wrong, rather than that they
    weren't understood.
    """
    await groceries.async_remove()
    await hass.async_block_till_done()
    assert await converse("what's on the groceries list") == (
        "Sorry, something went wrong with the Groceries list."
    )


async def test_no_lists_registers_nothing(hass, config_entry):
    """Test that the trigger is removed when there are no lists left."""
    manager = config_entry.runtime_data
    registry = er.async_get(hass)
    for entity_id in hass.states.async_entity_ids("todo"):
        registry.async_remove(entity_id)
    await hass.async_block_till_done()
    assert manager.sentences == []


@pytest.mark.parametrize(
    "todo_lists",
    [lambda: [MockTodoList("???"), MockTodoList("Groceries")]],
    indirect=True,
)
async def test_unusable_names_are_skipped(config_entry):
    """Test that a name with nothing left after cleaning gets no sentences."""
    sentences = config_entry.runtime_data.sentences
    assert sentences
    assert not any("()" in sentence for sentence in sentences)
