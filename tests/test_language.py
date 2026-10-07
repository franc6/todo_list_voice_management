"""Tests for language.py and the bundled language files."""

import copy
from pathlib import Path

import pytest
import yaml

from custom_components.todo_list_voice_management.const import (
    RESPONSE_ITEM_ON_LIST_COUNT,
    RESPONSE_LIST_CONTENTS,
    SENTENCES_DIR,
)
from custom_components.todo_list_voice_management.language import (
    LanguageError,
    async_load_languages,
    parse_language,
)

BUNDLED = (
    Path(__file__).parent.parent
    / "custom_components"
    / "todo_list_voice_management"
    / SENTENCES_DIR
)


@pytest.fixture(name="english")
def english_fixture():
    """Return the parsed contents of the bundled English file."""
    with open(BUNDLED / "en.yaml", encoding="utf-8") as file_handle:
        return yaml.safe_load(file_handle)


async def test_bundled_languages_load(hass):
    """Test that every bundled language file is valid."""
    languages = await async_load_languages(hass)
    expected = {path.stem for path in BUNDLED.glob("*.yaml")}
    assert set(languages) == expected
    assert {"en", "de", "es", "fr"} <= expected


@pytest.mark.parametrize(
    ("code", "one", "many"),
    [
        ("en", "and you need just one.", "and you need 3."),
        ("de", "und du brauchst nur eins.", "und du brauchst 3."),
        ("es", "necesitas solo una unidad.", "necesitas 3 unidades."),
        ("fr", "il en faut un seul.", "il en faut 3."),
    ],
)
async def test_count_plurals(hass, code, one, many):
    """Test that counts of one and many are phrased differently."""
    language = (await async_load_languages(hass))[code]
    respond = language.respond
    assert respond(
        RESPONSE_ITEM_ON_LIST_COUNT, "X", item="Y", count=1
    ).endswith(one)
    assert respond(
        RESPONSE_ITEM_ON_LIST_COUNT, "X", item="Y", count=3
    ).endswith(many)


async def test_join_and_entries(hass):
    """Test joining items in English."""
    language = (await async_load_languages(hass))["en"]
    assert language.join([]) == ""
    assert language.join(["milk"]) == "milk"
    assert language.join(["milk", "eggs"]) == "milk and eggs"
    assert language.join(["milk", "eggs", "bread"]) == "milk, eggs, and bread"
    assert (
        language.respond(
            RESPONSE_LIST_CONTENTS, "Groceries", items="milk", item_count=1
        )
        == "There's just one thing on the Groceries list: milk."
    )


@pytest.mark.parametrize(
    ("spoken", "expected"),
    [
        ("milk", "milk"),
        ("some milk", "milk"),
        ("The Milk", "Milk"),
        ("any more milk", "milk"),
        ("the", "the"),
        ("theater tickets", "theater tickets"),
    ],
)
async def test_clean_item(hass, spoken, expected):
    """Test stripping articles from spoken items."""
    language = (await async_load_languages(hass))["en"]
    assert language.clean_item(spoken) == expected


async def test_clean_item_elision(hass):
    """Test prefixes without a trailing space, like French "l'"."""
    language = (await async_load_languages(hass))["fr"]
    assert language.clean_item("l'eau") == "eau"
    assert language.clean_item("de la farine") == "farine"


def _break(data, path, value):
    """Set the value at path (a tuple of keys) in a copy of data."""
    data = copy.deepcopy(data)
    target = data
    for key in path[:-1]:
        target = target[key]
    if value is KeyError:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return data


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("sentences",), KeyError, "sentences must be a mapping"),
        (("sentences", "is_on_list"), [], "must be a non-empty list"),
        (("sentences", "is_on_list"), [1], "must only contain strings"),
        (
            ("sentences", "is_on_list"),
            ["is {item} on the list"],
            "must contain <todo_list> exactly once",
        ),
        (
            ("sentences", "is_on_list"),
            ["is it on <todo_list>"],
            "must contain {item} exactly once",
        ),
        (
            ("sentences", "list_items"),
            ["what is {item} on <todo_list>"],
            "must contain {item} zero times",
        ),
        (
            ("sentences", "is_on_list"),
            ["is {item} on {where} <todo_list>"],
            "may only use {item}",
        ),
        (
            ("sentences", "is_on_list"),
            ["is {item} on (the <todo_list>"],
            "is invalid",
        ),
        (("responses", "item_added"), KeyError, "responses.item_added"),
        (("formatting", "separator"), 1, "formatting.separator"),
        (("item_prefixes",), "the", "item_prefixes must be a list"),
        (("item_prefixes",), ["  "], "item_prefixes must be a list"),
    ],
)
def test_invalid_language(hass, english, path, value, message):
    """Test that invalid language files are rejected."""
    with pytest.raises(LanguageError, match=message):
        parse_language(hass, "en", _break(english, path, value))


def test_not_a_mapping(hass):
    """Test that a file must contain a mapping."""
    with pytest.raises(LanguageError, match="file must be a mapping"):
        parse_language(hass, "en", ["nope"])


async def test_bad_files_are_skipped(hass, tmp_path, english, caplog):
    """Test that broken files are logged and skipped."""
    (tmp_path / "en.yaml").write_text(yaml.safe_dump(english), "utf-8")
    (tmp_path / "xx.yaml").write_text("sentences: [", "utf-8")
    (tmp_path / "yy.yaml").write_text("sentences: {}", "utf-8")

    languages = await async_load_languages(hass, tmp_path)

    assert set(languages) == {"en"}
    assert "Unable to read" in caplog.text
    assert "Ignoring language yy" in caplog.text


def test_no_item_prefixes(hass, english):
    """Test that item_prefixes is optional."""
    language = parse_language(
        hass, "en", _break(english, ("item_prefixes",), KeyError)
    )
    assert language.clean_item(" the milk ") == "the milk"
