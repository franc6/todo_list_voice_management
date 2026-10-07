"""End-to-end tests through Home Assistant's default conversation agent."""

import datetime

import pytest
from homeassistant.components.homeassistant.exposed_entities import (
    async_expose_entity,
)
from homeassistant.components.todo import TodoItemStatus, TodoListEntityFeature
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.todo_list_voice_management.const import ASSISTANT

from .conftest import MockTodoList, make_item

pytestmark = pytest.mark.usefixtures("config_entry")


def summaries(todo_list, status=TodoItemStatus.NEEDS_ACTION):
    """Return the summaries of items with the given status."""
    return [i.summary for i in todo_list.todo_items if i.status == status]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "is bread on the shopping list?",
            "Yes, you've got Bread on the Shopping List.",
        ),
        (
            "Is there any milk on my shopping list?",
            "Yes, you've got Milk on the Shopping List, and you need 2.",
        ),
        (
            "do we have eggs on the shopping list already",
            "Yes, you've got Eggs on the Shopping List, and you need just "
            "one.",
        ),
        (
            "does the shopping list have cheese",
            "No, you don't have cheese on the Shopping List.",
        ),
        (
            # Completed items aren't on the list any more.
            "is butter on the shopping list",
            "No, you don't have butter on the Shopping List.",
        ),
        (
            "is bread on the groceries list",
            "No, you don't have bread on the Groceries list.",
        ),
    ],
)
async def test_is_on_list(converse, text, expected):
    """Test asking whether an item is on a list."""
    assert await converse(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "what's on the shopping list?",
        "What is on my shopping list",
        "what do we have on the shopping list",
        "read me the shopping list",
    ],
)
async def test_list_items(converse, text):
    """Test reading a list with several items."""
    assert await converse(text) == (
        "There are 3 things on the Shopping List: 2 Milk, 1 Eggs, and Bread."
    )


@pytest.mark.parametrize(
    "text",
    [
        "what's on the shopping list in alphabetical order?",
        "What is on my shopping list alphabetically",
        "read me the shopping list sorted alphabetically",
        "read me the alphabetized shopping list",
        "list everything on the shopping list from A to Z",
    ],
)
async def test_list_items_alphabetical(converse, text):
    """Test reading a list in alphabetical order."""
    assert await converse(text) == (
        "There are 3 things on the Shopping List: Bread, 1 Eggs, and 2 Milk."
    )


async def test_alphabetical_ignores_case_and_accents(converse, groceries):
    """Test that case and accents don't affect alphabetical order."""
    for summary in ("zucchini", "Éclairs", "apples (3)", "Bananas"):
        await groceries.async_create_todo_item(make_item(summary))
    assert await converse("read me the groceries alphabetically") == (
        "There are 4 things on the Groceries list: "
        "3 apples, Bananas, Éclairs, and zucchini."
    )


@pytest.mark.parametrize(
    "text",
    [
        "what's on the groceries list by due date?",
        "read me the groceries sorted by due date",
        "what do we have on the groceries list in order of priority",
        "list everything on the groceries in priority order",
    ],
)
async def test_list_items_by_due_date(converse, groceries, text):
    """Test reading a list soonest due first, undated items last."""
    utc = datetime.timezone.utc
    for item in (
        make_item("Rake"),
        make_item(
            "Paint", due=datetime.datetime(2026, 10, 10, 15, 0, tzinfo=utc)
        ),
        make_item("Nails", due=datetime.date(2026, 10, 9)),
        make_item("Tape", due=datetime.date(2026, 10, 10)),
        make_item("Glue"),
    ):
        await groceries.async_create_todo_item(item)
    # Tape is due at the start of the 10th, local time, before Paint.
    assert await converse(text) == (
        "There are 5 things on the Groceries list: "
        "Nails, Tape, Paint, Rake, and Glue."
    )


async def test_list_items_one_and_two(converse, groceries):
    """Test the singular response, and joining two items."""
    await groceries.async_create_todo_item(make_item("Apples (6)"))
    assert await converse("what's on the groceries list") == (
        "There's just one thing on the Groceries list: 6 Apples."
    )

    await groceries.async_create_todo_item(make_item("Pears"))
    assert await converse("what is on the groceries") == (
        "There are 2 things on the Groceries list: 6 Apples and Pears."
    )


async def test_list_empty(converse):
    """Test reading an empty list."""
    assert await converse("what's on the groceries list") == (
        "There's nothing on the Groceries list."
    )


@pytest.mark.parametrize(
    "text",
    [
        "if paper towels isn't on the shopping list, add it",
        "add paper towels to the shopping list if it's not there",
        "add some paper towels to the shopping list if they aren't already "
        "on the list",
        "make sure paper towels are on the shopping list",
    ],
)
async def test_add_if_missing_adds(converse, shopping_list, text):
    """Test adding an item that isn't on the list."""
    assert await converse(text) == (
        "OK, I added paper towels to the Shopping List."
    )
    assert summaries(shopping_list)[-1] == "Paper towels"


async def test_add_if_missing_already_there(converse, shopping_list):
    """Test conditionally adding items that are already on the list."""
    before = summaries(shopping_list)
    assert await converse("if bread isn't on the shopping list, add it") == (
        "You've already got Bread on the Shopping List."
    )
    assert await converse(
        "add milk to the shopping list if it's not there"
    ) == ("You've already got Milk on the Shopping List, and you need 2.")
    assert summaries(shopping_list) == before


@pytest.mark.parametrize(
    "text",
    [
        "ADD paper towels TO THE SHOPPING LIST IF IT'S NOT THERE",
        "Make Sure paper towels Are On The Shopping List",
    ],
)
async def test_add_if_missing_ignores_sentence_case(
    converse, shopping_list, text
):
    """Test that the case of the sentence and list name doesn't matter."""
    assert await converse(text) == (
        "OK, I added paper towels to the Shopping List."
    )
    assert summaries(shopping_list)[-1] == "Paper towels"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "ADD MILK TO THE SHOPPING LIST IF IT'S NOT THERE",
            "You've already got Milk on the Shopping List, and you need 2.",
        ),
        (
            "If Bread Isn't On The Shopping List, Add It",
            "You've already got Bread on the Shopping List.",
        ),
        (
            "IS BREAD ON THE SHOPPING LIST?",
            "Yes, you've got Bread on the Shopping List.",
        ),
    ],
)
async def test_existing_item_ignores_case(
    converse, shopping_list, text, expected
):
    """Test that items are found whatever case they're spoken in."""
    before = summaries(shopping_list)
    assert await converse(text) == expected
    assert summaries(shopping_list) == before


async def test_add_if_missing_refreshes_first(converse, shopping_list):
    """Test that items added at the source since the last poll are seen."""
    shopping_list.unfetched = [make_item("rain gauge")]
    assert (
        await converse("add Rain Gauge to the shopping list if it's not there")
        == "You've already got rain gauge on the Shopping List."
    )
    assert summaries(shopping_list).count("rain gauge") == 1
    assert "Rain gauge" not in summaries(shopping_list)


async def test_refresh_failure_uses_known_items(converse, shopping_list):
    """Test that a failed refresh falls back to the items already known."""
    shopping_list.fail_update_with = HomeAssistantError("offline")
    assert await converse("is bread on the shopping list?") == (
        "Yes, you've got Bread on the Shopping List."
    )


async def test_add_if_missing_reopens_completed(converse, shopping_list):
    """Test that a completed item is reopened rather than duplicated."""
    butter = next(i for i in shopping_list.todo_items if i.summary == "Butter")
    butter.description = "Salted"
    butter.due = datetime.date(2026, 10, 1)
    butter.completed = datetime.datetime(2026, 10, 2, tzinfo=datetime.UTC)

    assert await converse(
        "add butter to the shopping list if it's not there"
    ) == ("OK, I added Butter to the Shopping List.")

    butters = [i for i in shopping_list.todo_items if i.summary == "Butter"]
    assert len(butters) == 1
    assert butters[0].status == TodoItemStatus.NEEDS_ACTION
    assert butters[0].completed is None
    assert butters[0].description == "Salted"
    assert butters[0].due == datetime.date(2026, 10, 1)


@pytest.mark.parametrize(
    "todo_lists",
    [
        lambda: [
            MockTodoList(
                "Shopping List",
                [make_item("Butter", TodoItemStatus.COMPLETED)],
                TodoListEntityFeature.CREATE_TODO_ITEM,
            )
        ]
    ],
    indirect=True,
)
async def test_add_if_missing_without_update_support(converse, todo_lists):
    """Test that a new item is added when completed ones can't be reopened."""
    assert await converse(
        "add butter to the shopping list if it's not there"
    ) == ("OK, I added butter to the Shopping List.")
    assert summaries(todo_lists[0]) == ["Butter"]


@pytest.mark.parametrize(
    "todo_lists",
    [lambda: [MockTodoList("Shopping List", features=0)]],
    indirect=True,
)
async def test_add_if_missing_not_supported(converse, todo_lists):
    """Test a list that can't be added to."""
    assert await converse(
        "add milk to the shopping list if it's not there"
    ) == ("Sorry, I can't add things to the Shopping List.")
    assert todo_lists[0].todo_items == []


async def test_add_if_missing_error(converse, groceries):
    """Test a list that fails when adding."""
    groceries.fail_with = HomeAssistantError("offline")
    assert await converse(
        "add milk to the groceries list if it's not there"
    ) == ("Sorry, something went wrong with the Groceries list.")


async def test_plain_add_is_left_to_home_assistant(converse, shopping_list):
    """Test that HA's built-in intent still handles a plain add."""
    await converse("add bread to the shopping list")
    assert summaries(shopping_list).count("Bread") == 2


async def test_aliases_and_renames(hass, converse, shopping_list):
    """Test that aliases and renames are picked up."""
    registry = er.async_get(hass)
    registry.async_update_entity(
        shopping_list.entity_id, aliases=[er.COMPUTED_NAME, "Errands"]
    )
    await hass.async_block_till_done()
    assert await converse("is bread on the errands list") == (
        "Yes, you've got Bread on the Errands list."
    )

    registry.async_update_entity(shopping_list.entity_id, name="Store")
    await hass.async_block_till_done()
    assert await converse("is bread on the store list") == (
        "Yes, you've got Bread on the Store list."
    )
    assert "Bread" not in await converse("is bread on the shopping list")


async def test_unexposed_lists_are_ignored(hass, converse, shopping_list):
    """Test that only lists exposed to Assist get sentences."""
    async_expose_entity(hass, ASSISTANT, shopping_list.entity_id, False)
    await hass.async_block_till_done()
    assert "Bread" not in await converse("is bread on the shopping list")

    async_expose_entity(hass, ASSISTANT, shopping_list.entity_id, True)
    await hass.async_block_till_done()
    assert await converse("is bread on the shopping list") == (
        "Yes, you've got Bread on the Shopping List."
    )


@pytest.mark.parametrize(
    "todo_lists",
    [lambda: [MockTodoList("Shopping"), MockTodoList("Shopping List")]],
    indirect=True,
)
async def test_longest_name_wins(converse, todo_lists):
    """Test that "shopping list" isn't taken as the "shopping" list."""
    await converse("add milk to the shopping list if it's not there")
    assert summaries(todo_lists[0]) == []
    assert summaries(todo_lists[1]) == ["Milk"]


@pytest.mark.parametrize(
    "todo_lists",
    [
        lambda: [
            MockTodoList("Home Improvement To Do", [make_item("Paint")]),
            MockTodoList("Garden To-Do", [make_item("Weed")]),
        ]
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "is paint on the home improvement to do list",
            "Yes, you've got Paint on the Home Improvement To Do list.",
        ),
        (
            "is paint on the home improvement todo list",
            "Yes, you've got Paint on the Home Improvement To Do list.",
        ),
        (
            "is weed on the garden to do list",
            "Yes, you've got Weed on the Garden To-Do list.",
        ),
        (
            "is weed on the garden todo list",
            "Yes, you've got Weed on the Garden To-Do list.",
        ),
    ],
)
async def test_list_name_spacing(converse, text, expected):
    """Test list names with hyphens or words run together."""
    assert await converse(text) == expected


@pytest.mark.parametrize(
    ("language", "text", "expected"),
    [
        (
            "fr",
            "Est-ce qu'il y a du lait sur la liste de courses ?",
            "Oui, « Lait » est bien sur la liste de courses, et il en faut 2.",
        ),
        (
            "fr",
            "Le pain est-il sur ma liste de courses ?",
            "Oui, « Pain » est bien sur la liste de courses.",
        ),
        (
            "fr",
            "Qu'est-ce qu'il y a sur la liste de courses ?",
            "Il y a 2 choses sur la liste de courses : 2 Lait et Pain.",
        ),
        (
            "fr",
            "Si le beurre n'est pas sur la liste de courses, ajoute-le.",
            "D'accord, j'ai ajouté « beurre » à la liste de courses.",
        ),
        (
            "es",
            "¿Hay leche en la lista de la compra?",
            "Sí, tienes Leche en la lista de la compra y necesitas solo una "
            "unidad.",
        ),
        (
            "es",
            "¿Qué hay en la lista de la compra?",
            "En la lista de la compra solo hay una cosa: 1 Leche.",
        ),
        (
            "es",
            "Asegúrate de que el pan está en la lista de la compra",
            "Vale, he añadido pan a la lista de la compra.",
        ),
        (
            "de",
            "Steht Milch auf der Einkaufsliste?",
            "Ja, du hast Milch auf der Einkaufsliste, und du brauchst 3.",
        ),
        (
            "de",
            "Was steht auf der Einkaufsliste?",
            "Auf der Einkaufsliste stehen 2 Sachen: 3 Milch und Brot.",
        ),
        (
            "de",
            "Was steht auf der Einkaufsliste alphabetisch sortiert?",
            "Auf der Einkaufsliste stehen 2 Sachen: Brot und 3 Milch.",
        ),
        (
            "de",
            "Lies mir die Einkaufsliste in alphabetischer Reihenfolge vor",
            "Auf der Einkaufsliste stehen 2 Sachen: Brot und 3 Milch.",
        ),
        (
            "fr",
            "Qu'est-ce qu'il y a sur la liste de courses par ordre "
            "alphabétique ?",
            "Il y a 2 choses sur la liste de courses : 2 Lait et Pain.",
        ),
        (
            "es",
            "Léeme la lista de la compra en orden alfabético",
            "En la lista de la compra solo hay una cosa: 1 Leche.",
        ),
        (
            "de",
            "Was steht auf der Einkaufsliste nach Fälligkeit sortiert?",
            "Auf der Einkaufsliste stehen 2 Sachen: 3 Milch und Brot.",
        ),
        (
            "fr",
            "Lis-moi la liste de courses par ordre de priorité",
            "Il y a 2 choses sur la liste de courses : 2 Lait et Pain.",
        ),
        (
            "es",
            "¿Qué hay en la lista de la compra por fecha de vencimiento?",
            "En la lista de la compra solo hay una cosa: 1 Leche.",
        ),
        (
            "de",
            "Haben wir noch Eier auf der Einkaufsliste?",
            "Nein, du hast Eier nicht auf der Einkaufsliste.",
        ),
    ],
)
@pytest.mark.parametrize(
    "todo_lists",
    [
        lambda: [
            MockTodoList(
                "Liste de courses",
                [make_item("Lait (2)"), make_item("Pain")],
            ),
            MockTodoList("Lista de la compra", [make_item("Leche (1)")]),
            MockTodoList(
                "Einkaufsliste", [make_item("Milch (3)"), make_item("Brot")]
            ),
        ]
    ],
    indirect=True,
)
async def test_other_languages(converse, language, text, expected):
    """Test sentences and responses in other languages."""
    assert await converse(text, language) == expected


async def test_unload(hass, converse, config_entry):
    """Test that unloading removes the sentences."""
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert "Bread" not in await converse("is bread on the shopping list")
