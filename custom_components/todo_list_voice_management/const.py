"""Constants for todo_list_voice_management."""

from typing import Final

DOMAIN: Final = "todo_list_voice_management"

# Assistant identifier used by HA when deciding whether an entity is exposed
# to Assist.
ASSISTANT: Final = "conversation"

# Directory (relative to this file) holding one YAML file per language.
SENTENCES_DIR: Final = "sentences"

# Placeholder translators use in sentence templates for the to-do list name.
LIST_PLACEHOLDER: Final = "<todo_list>"

# Slot holding the item in sentence templates.
ITEM_SLOT: Final = "item"
ITEM_PLACEHOLDER: Final = "{" + ITEM_SLOT + "}"

# Kinds of sentences, i.e. the keys under "sentences" in a language file.
KIND_IS_ON_LIST: Final = "is_on_list"
KIND_LIST_ITEMS: Final = "list_items"
KIND_LIST_ITEMS_ALPHABETICAL: Final = "list_items_alphabetical"
KIND_LIST_ITEMS_BY_DUE_DATE: Final = "list_items_by_due_date"
KIND_ADD_IF_MISSING: Final = "add_if_missing"

# Whether each kind of sentence must include the {item} slot.
SENTENCE_KINDS: Final = {
    KIND_IS_ON_LIST: True,
    KIND_LIST_ITEMS: False,
    KIND_LIST_ITEMS_ALPHABETICAL: False,
    KIND_LIST_ITEMS_BY_DUE_DATE: False,
    KIND_ADD_IF_MISSING: True,
}

# Keys under "responses" in a language file.
RESPONSE_ITEM_ON_LIST: Final = "item_on_list"
RESPONSE_ITEM_ON_LIST_COUNT: Final = "item_on_list_with_count"
RESPONSE_ITEM_NOT_ON_LIST: Final = "item_not_on_list"
RESPONSE_LIST_CONTENTS: Final = "list_contents"
RESPONSE_LIST_EMPTY: Final = "list_empty"
RESPONSE_ITEM_ADDED: Final = "item_added"
RESPONSE_ITEM_ALREADY_ON_LIST: Final = "item_already_on_list"
RESPONSE_ITEM_ALREADY_ON_LIST_COUNT: Final = "item_already_on_list_with_count"
RESPONSE_ADD_NOT_SUPPORTED: Final = "add_not_supported"
RESPONSE_ERROR: Final = "error"

RESPONSE_KEYS: Final = (
    RESPONSE_ITEM_ON_LIST,
    RESPONSE_ITEM_ON_LIST_COUNT,
    RESPONSE_ITEM_NOT_ON_LIST,
    RESPONSE_LIST_CONTENTS,
    RESPONSE_LIST_EMPTY,
    RESPONSE_ITEM_ADDED,
    RESPONSE_ITEM_ALREADY_ON_LIST,
    RESPONSE_ITEM_ALREADY_ON_LIST_COUNT,
    RESPONSE_ADD_NOT_SUPPORTED,
    RESPONSE_ERROR,
)

# Keys under "formatting" in a language file.
FORMAT_LIST_NAME: Final = "list_name"
FORMAT_LIST_ENTRY: Final = "list_entry"
FORMAT_SEPARATOR: Final = "separator"
FORMAT_FINAL_SEPARATOR: Final = "final_separator"
FORMAT_PAIR_SEPARATOR: Final = "pair_separator"

FORMAT_TEMPLATE_KEYS: Final = (FORMAT_LIST_NAME, FORMAT_LIST_ENTRY)
FORMAT_STRING_KEYS: Final = (
    FORMAT_SEPARATOR,
    FORMAT_FINAL_SEPARATOR,
    FORMAT_PAIR_SEPARATOR,
)
