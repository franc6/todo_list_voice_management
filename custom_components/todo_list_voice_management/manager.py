"""Register sentences with the conversation agent and dispatch matches."""

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

from hassil.recognize import RecognizeResult
from hassil.util import remove_punctuation
from homeassistant.components.conversation import ConversationInput
from homeassistant.components.conversation.agent_manager import (
    get_agent_manager,
)
from homeassistant.components.homeassistant.exposed_entities import (
    async_listen_entity_updates,
    async_should_expose,
)
from homeassistant.components.todo import DOMAIN as TODO_DOMAIN
from homeassistant.components.todo.const import DATA_COMPONENT
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, intent

from .const import (
    ASSISTANT,
    ITEM_PLACEHOLDER,
    ITEM_SLOT,
    KIND_ADD_IF_MISSING,
    KIND_IS_ON_LIST,
    KIND_LIST_ITEMS,
    KIND_LIST_ITEMS_ALPHABETICAL,
    KIND_LIST_ITEMS_BY_DUE_DATE,
    LIST_PLACEHOLDER,
    RESPONSE_ERROR,
)
from .handlers import async_add_if_missing, async_is_on_list, async_list_items
from .items import alphabetical_order, due_date_order
from .language import Language

_LOGGER = logging.getLogger(__name__)

# Characters with a meaning in hassil templates.
_TEMPLATE_SYNTAX = re.compile(r"[()\[\]{}<>|;\\]")
_WHITESPACE = re.compile(r"\s+")
_TODO_PREFIX = f"{TODO_DOMAIN}."

# Handlers for the kinds of sentence that include an {item}.
_ITEM_HANDLERS = {
    KIND_IS_ON_LIST: async_is_on_list,
    KIND_ADD_IF_MISSING: async_add_if_missing,
}

# Sort keys for the kinds of sentence that read a list; None is list order.
_LIST_ORDERS = {
    KIND_LIST_ITEMS: None,
    KIND_LIST_ITEMS_ALPHABETICAL: alphabetical_order,
    KIND_LIST_ITEMS_BY_DUE_DATE: due_date_order,
}


@dataclass(frozen=True)
class SentenceTarget:
    """What a generated sentence refers to.

    :param language: The language code of the sentence
    :type language: str
    :param kind: The kind of sentence
    :type kind: str
    :param entity_id: The to-do list entity
    :type entity_id: str
    :param list_name: The list name or alias used in the sentence
    :type list_name: str
    """

    language: str
    kind: str
    entity_id: str
    list_name: str


def template_name(name: str) -> str:
    """Make a list name safe to embed in a hassil template.

    :param name: A list name or alias
    :type name: str
    :returns: The name without punctuation or template syntax
    :rtype: str
    """
    name = _TEMPLATE_SYNTAX.sub(" ", remove_punctuation(name))
    return _WHITESPACE.sub(" ", name).strip().lower()


def _word_expression(word: str) -> str:
    """Return a hassil expression for one word of a list name.

    Speech-to-text may write a hyphenated word with a space or as one word,
    so "to-do" also matches "to do" and "todo".
    """
    parts = [part for part in word.split("-") if part]
    if len(parts) < 2:
        return word
    return f"({word}|{' '.join(parts)}|{''.join(parts)})"


def name_expression(name: str) -> str:
    """Return a hassil expression matching a list name when spoken.

    Hyphenated words also match with a space or as one word, and any two
    neighbouring words also match as one word, so "home to do" also matches
    "home todo".  Only one pair is joined, to keep the expression small.

    :param name: The list name, as returned by template_name
    :type name: str
    :returns: The expression, e.g. "(to do|todo)"
    :rtype: str
    """
    words = name.split()
    variants = [words] + [
        words[:i] + [words[i] + words[i + 1]] + words[i + 2 :]
        for i in range(len(words) - 1)
    ]
    expressions = (
        " ".join(_word_expression(word) for word in variant)
        for variant in variants
    )
    return "(" + "|".join(dict.fromkeys(expressions)) + ")"


class TodoListVoiceManager:
    """Keep the conversation trigger in sync with the to-do lists."""

    def __init__(
        self, hass: HomeAssistant, languages: dict[str, Language]
    ) -> None:
        """Construct the manager.

        :param hass: The Home Assistant instance
        :type hass: HomeAssistant
        :param languages: The languages to register sentences for
        :type languages: dict[str, Language]
        """
        self._hass = hass
        self._languages = languages
        self._targets: dict[str, SentenceTarget] = {}
        self._unregister_trigger: CALLBACK_TYPE | None = None
        self._unsubscribes: list[Callable[[], None]] = []

    @property
    def sentences(self) -> list[str]:
        """Return the currently registered sentences."""
        return list(self._targets)

    @callback
    def async_start(self) -> None:
        """Register the trigger and start listening for list changes."""
        self._unsubscribes = [
            self._hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED,
                self._async_refresh_event,
                event_filter=_is_todo_registry_event,
            ),
            self._hass.bus.async_listen(
                EVENT_STATE_CHANGED,
                self._async_refresh_event,
                event_filter=_is_todo_name_change,
            ),
            async_listen_entity_updates(
                self._hass, ASSISTANT, self.async_refresh
            ),
        ]
        self.async_refresh()

    @callback
    def async_stop(self) -> None:
        """Unregister the trigger and stop listening."""
        for unsubscribe in self._unsubscribes:
            unsubscribe()
        self._unsubscribes = []
        if self._unregister_trigger is not None:
            self._unregister_trigger()
            self._unregister_trigger = None
        self._targets = {}

    @callback
    def _async_refresh_event(self, _event: Event[Any]) -> None:
        """Refresh after a relevant event."""
        self.async_refresh()

    @callback
    def async_refresh(self) -> None:
        """Rebuild the sentences, re-registering only if they changed."""
        targets = self._build_targets()
        if targets == self._targets:
            return
        if self._unregister_trigger is not None:
            self._unregister_trigger()
            self._unregister_trigger = None
        self._targets = targets
        if targets:
            self._unregister_trigger = get_agent_manager(
                self._hass
            ).register_trigger(list(targets), self._async_handle_trigger)
        _LOGGER.debug("Registered %d sentences", len(targets))

    def _list_names(self) -> list[tuple[str, str, str]]:
        """Return (template name, name, entity_id) for every exposed list.

        Longer names come first, so that "shopping list" wins over
        "shopping" when both are lists.
        """
        registry = er.async_get(self._hass)
        names = []
        for state in self._hass.states.async_all(TODO_DOMAIN):
            if not async_should_expose(self._hass, ASSISTANT, state.entity_id):
                continue
            for name in intent.async_get_entity_aliases(
                self._hass, registry.async_get(state.entity_id), state=state
            ):
                if safe_name := template_name(name):
                    names.append((safe_name, name.strip(), state.entity_id))
        names.sort(key=lambda entry: (-len(entry[0]), entry[0], entry[2]))
        return names

    def _templates(self) -> list[tuple[str, str, str]]:
        """Return (template, language, kind) for every sentence template.

        hassil reports matches in sentence order, and the first match wins.
        Templates starting with {item} match almost anything ending the
        right way, so they come last.
        """
        templates = [
            (template, language.code, kind)
            for language in self._languages.values()
            for kind, kind_templates in language.sentences.items()
            for template in kind_templates
        ]
        templates.sort(key=lambda entry: entry[0].startswith(ITEM_PLACEHOLDER))
        return templates

    def _build_targets(self) -> dict[str, SentenceTarget]:
        """Generate every sentence, mapped to what it refers to."""
        targets: dict[str, SentenceTarget] = {}
        templates = self._templates()
        for safe_name, name, entity_id in self._list_names():
            expression = name_expression(safe_name)
            for template, language, kind in templates:
                sentence = template.replace(LIST_PLACEHOLDER, expression)
                # First wins for duplicate names; see _list_names.
                targets.setdefault(
                    sentence, SentenceTarget(language, kind, entity_id, name)
                )
        return targets

    async def _async_handle_trigger(
        self, _user_input: ConversationInput, result: RecognizeResult
    ) -> str | None:
        """Answer a matched sentence."""
        if (
            result.intent_sentence is None
            or (target := self._targets.get(result.intent_sentence.text))
            is None
        ):
            return None
        language = self._languages[target.language]
        entity = self._hass.data[DATA_COMPONENT].get_entity(target.entity_id)
        if entity is None:
            return language.respond(RESPONSE_ERROR, target.list_name)

        item = ""
        if ITEM_SLOT in result.entities:
            item = language.clean_item(str(result.entities[ITEM_SLOT].value))

        try:
            if target.kind in _LIST_ORDERS:
                return await async_list_items(
                    language,
                    entity,
                    target.list_name,
                    order=_LIST_ORDERS[target.kind],
                )
            return await _ITEM_HANDLERS[target.kind](
                language, entity, target.list_name, item
            )
        except HomeAssistantError as err:
            _LOGGER.error(
                "Unable to handle '%s' for %s: %s",
                result.intent_sentence.text,
                target.entity_id,
                err,
            )
        return language.respond(RESPONSE_ERROR, target.list_name)


@callback
def _is_todo_registry_event(data: er.EventEntityRegistryUpdatedData) -> bool:
    """Return True for registry changes to to-do entities."""
    return data["entity_id"].startswith(_TODO_PREFIX) or data.get(
        "old_entity_id", ""
    ).startswith(_TODO_PREFIX)


@callback
def _is_todo_name_change(data: Any) -> bool:
    """Return True if a to-do list was added, removed or renamed."""
    if not data["entity_id"].startswith(_TODO_PREFIX):
        return False
    old_state = data["old_state"]
    new_state = data["new_state"]
    return (
        old_state is None
        or new_state is None
        or old_state.name != new_state.name
    )
