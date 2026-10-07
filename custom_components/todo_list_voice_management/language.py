"""Load and render the per-language sentences and responses."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from hassil.parse_expression import parse_sentence
from hassil.parser import ParseError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template

from .const import (
    FORMAT_FINAL_SEPARATOR,
    FORMAT_LIST_ENTRY,
    FORMAT_LIST_NAME,
    FORMAT_PAIR_SEPARATOR,
    FORMAT_SEPARATOR,
    FORMAT_STRING_KEYS,
    FORMAT_TEMPLATE_KEYS,
    ITEM_PLACEHOLDER,
    LIST_PLACEHOLDER,
    RESPONSE_KEYS,
    SENTENCE_KINDS,
    SENTENCES_DIR,
)
from .items import ListEntry

_LOGGER = logging.getLogger(__name__)


class LanguageError(ValueError):
    """Raised when a language file is invalid."""


@dataclass
class Language:
    """Sentences and responses for one language.

    :param code: The language code, e.g. "en"
    :type code: str
    :param sentences: Sentence templates, keyed by sentence kind
    :type sentences: dict[str, list[str]]
    :param responses: Response templates, keyed by response key
    :type responses: dict[str, Template]
    :param templates: Formatting templates, keyed by formatting key
    :type templates: dict[str, Template]
    :param separators: Separators for joining items, keyed by formatting key
    :type separators: dict[str, str]
    :param item_prefixes: Matches words (e.g. articles) to strip from the
        start of spoken items, or None if there are none
    :type item_prefixes: re.Pattern[str] | None
    """

    code: str
    sentences: dict[str, list[str]]
    responses: dict[str, Template]
    templates: dict[str, Template]
    separators: dict[str, str]
    item_prefixes: re.Pattern[str] | None

    def clean_item(self, spoken: str) -> str:
        """Strip leading articles and similar words from a spoken item.

        :param spoken: The item, as spoken
        :type spoken: str
        :returns: The item without leading prefixes, e.g. "milk" for
            "some milk"; spoken itself if nothing would be left
        :rtype: str
        """
        item = spoken.strip()
        if self.item_prefixes is None:
            return item
        while (rest := self.item_prefixes.sub("", item, count=1)) and (
            rest != item
        ):
            item = rest
        return item

    def list_name(self, name: str) -> str:
        """Return how a list is referred to in responses.

        :param name: The name of the list
        :type name: str
        :returns: The rendered reference, e.g. "the shopping list"
        :rtype: str
        """
        return _render(self.templates[FORMAT_LIST_NAME], name=name)

    def list_entry(self, entry: ListEntry) -> str:
        """Return how an entry is read when reading a whole list.

        :param entry: The entry to render
        :type entry: ListEntry
        :returns: The rendered entry, e.g. "2 milk"
        :rtype: str
        """
        return _render(
            self.templates[FORMAT_LIST_ENTRY],
            item=entry.name,
            count=entry.count,
        )

    def join(self, parts: list[str]) -> str:
        """Join parts the way a list of things is spoken in this language.

        :param parts: The parts to join
        :type parts: list[str]
        :returns: The joined text, e.g. "milk, eggs, and bread"
        :rtype: str
        """
        if len(parts) < 2:
            return "".join(parts)
        if len(parts) == 2:
            return parts[0] + self.separators[FORMAT_PAIR_SEPARATOR] + parts[1]
        return (
            self.separators[FORMAT_SEPARATOR].join(parts[:-1])
            + self.separators[FORMAT_FINAL_SEPARATOR]
            + parts[-1]
        )

    def respond(self, key: str, list_name: str, **variables: Any) -> str:
        """Render a response.

        :param key: The response key
        :type key: str
        :param list_name: The name of the list the response is about
        :type list_name: str
        :param variables: Additional variables for the template
        :returns: The rendered response
        :rtype: str
        """
        return _render(
            self.responses[key],
            list=self.list_name(list_name),
            list_name=list_name,
            **variables,
        )


def _render(template: Template, **variables: Any) -> str:
    """Render a template to a stripped string."""
    return str(template.async_render(variables, parse_result=False)).strip()


def _require_mapping(data: Any, what: str) -> dict[str, Any]:
    """Return data if it's a mapping, otherwise raise LanguageError."""
    if not isinstance(data, dict):
        raise LanguageError(f"{what} must be a mapping")
    return data


def _require_string(data: dict[str, Any], key: str, what: str) -> str:
    """Return data[key] if it's a string, otherwise raise LanguageError."""
    value = data.get(key)
    if not isinstance(value, str):
        raise LanguageError(f"{what}.{key} must be a string")
    return value


def _validate_sentence(kind: str, sentence: Any) -> str:
    """Validate one sentence template and return it."""
    if not isinstance(sentence, str):
        raise LanguageError(f"sentences.{kind} must only contain strings")
    if sentence.count(LIST_PLACEHOLDER) != 1:
        raise LanguageError(
            f"'{sentence}' must contain {LIST_PLACEHOLDER} exactly once"
        )
    needs_item = SENTENCE_KINDS[kind]
    if (sentence.count(ITEM_PLACEHOLDER) == 1) != needs_item:
        raise LanguageError(
            f"'{sentence}' must contain {ITEM_PLACEHOLDER} "
            + ("exactly once" if needs_item else "zero times")
        )
    # Any other {slot} would silently become a wildcard, so reject it.
    if sentence.replace(ITEM_PLACEHOLDER, "").count("{"):
        raise LanguageError(f"'{sentence}' may only use {ITEM_PLACEHOLDER}")
    try:
        parse_sentence(sentence.replace(LIST_PLACEHOLDER, "(list)"))
    except ParseError as err:
        raise LanguageError(f"'{sentence}' is invalid: {err}") from err
    return sentence


def _parse_item_prefixes(data: dict[str, Any]) -> re.Pattern[str] | None:
    """Parse and validate the optional "item_prefixes" section."""
    prefixes = data.get("item_prefixes", [])
    if not isinstance(prefixes, list) or not all(
        isinstance(prefix, str) and prefix.strip() for prefix in prefixes
    ):
        raise LanguageError("item_prefixes must be a list of strings")
    if not prefixes:
        return None
    # Longest first, so "de la " wins over "de ".  A trailing space in the
    # file means a whole word ("le " must not match "lemon"); without one the
    # prefix attaches directly, like "l'".
    alternatives = "|".join(
        re.escape(prefix.strip()) + (r"\s+" if prefix.endswith(" ") else "")
        for prefix in sorted(prefixes, key=lambda p: -len(p.strip()))
    )
    return re.compile(f"^(?:{alternatives})", re.IGNORECASE)


def _parse_sentences(data: dict[str, Any]) -> dict[str, list[str]]:
    """Parse and validate the "sentences" section."""
    section = _require_mapping(data.get("sentences"), "sentences")
    sentences = {}
    for kind in SENTENCE_KINDS:
        templates = section.get(kind)
        if not isinstance(templates, list) or not templates:
            raise LanguageError(f"sentences.{kind} must be a non-empty list")
        sentences[kind] = [_validate_sentence(kind, s) for s in templates]
    return sentences


def parse_language(hass: HomeAssistant, code: str, data: Any) -> Language:
    """Build a Language from the contents of a language file.

    :param hass: The Home Assistant instance
    :type hass: HomeAssistant
    :param code: The language code
    :type code: str
    :param data: The parsed YAML content
    :type data: Any
    :returns: The language
    :rtype: Language
    :raises LanguageError: if the content is invalid
    """
    data = _require_mapping(data, "file")
    responses = _require_mapping(data.get("responses"), "responses")
    formatting = _require_mapping(data.get("formatting"), "formatting")
    return Language(
        code=code,
        sentences=_parse_sentences(data),
        responses={
            key: Template(_require_string(responses, key, "responses"), hass)
            for key in RESPONSE_KEYS
        },
        templates={
            key: Template(_require_string(formatting, key, "formatting"), hass)
            for key in FORMAT_TEMPLATE_KEYS
        },
        separators={
            key: _require_string(formatting, key, "formatting")
            for key in FORMAT_STRING_KEYS
        },
        item_prefixes=_parse_item_prefixes(data),
    )


def _read_language_files(directory: Path) -> dict[str, Any]:
    """Read every language file in directory (runs in the executor)."""
    contents = {}
    for path in sorted(directory.glob("*.yaml")):
        with path.open(encoding="utf-8") as file_handle:
            try:
                contents[path.stem] = yaml.safe_load(file_handle)
            except yaml.YAMLError as err:
                _LOGGER.error("Unable to read %s: %s", path, err)
    return contents


async def async_load_languages(
    hass: HomeAssistant, directory: Path | None = None
) -> dict[str, Language]:
    """Load every valid language file.

    Invalid files are logged and skipped, so one bad translation does not
    break the others.

    :param hass: The Home Assistant instance
    :type hass: HomeAssistant
    :param directory: Where to find the files, defaults to the bundled ones
    :type directory: Path | None
    :returns: The languages, keyed by language code
    :rtype: dict[str, Language]
    """
    if directory is None:
        directory = Path(__file__).parent / SENTENCES_DIR
    contents = await hass.async_add_executor_job(
        _read_language_files, directory
    )
    languages = {}
    for code, data in contents.items():
        try:
            languages[code] = parse_language(hass, code, data)
        except LanguageError as err:
            _LOGGER.error("Ignoring language %s: %s", code, err)
    return languages
