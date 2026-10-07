# Translating

There are two kinds of translatable text:

1. **The setup screen**, in `custom_components/todo_list_voice_management/translations/<language>.json`.  These are standard Home Assistant translation files; copy `en.json` and translate the values.
2. **The voice sentences and responses**, in `custom_components/todo_list_voice_management/sentences/<language>.yaml`.  This document is about those.

To add a language, copy `sentences/en.yaml` to `sentences/<language>.yaml`, where `<language>` is the language code (for example `it` or `pt-BR`), and translate it.  You don't need to translate the English sentences word for word.  Write whatever people actually say in your language.  A file that fails validation is skipped, and the error is logged, so check your Home Assistant log after restarting.

## Sentences
`sentences` has five groups, each a list of [hassil](https://github.com/OHF-Voice/hassil) templates, the same syntax used by Home Assistant's own sentences:

| Group | Meaning | Must contain |
| --- | --- | --- |
| `is_on_list` | Is an item on a list? | `<todo_list>` and `{item}`, once each |
| `list_items` | What's on a list? | `<todo_list>` once, and no `{item}` |
| `list_items_alphabetical` | What's on a list, in alphabetical order? | `<todo_list>` once, and no `{item}` |
| `list_items_by_due_date` | What's on a list, soonest due first? People may call this priority, so include those words too | `<todo_list>` once, and no `{item}` |
| `add_if_missing` | Add an item unless it's already on the list | `<todo_list>` and `{item}`, once each |

Template syntax:

- `(a|b|c)`: one of the alternatives is required.
- `[a|b]`: optional, and if present, one of the alternatives.
- `{item}`: matches whatever the user says there.  No other `{...}` is allowed.
- `<todo_list>`: replaced by each exposed list's name and aliases.

Some tips:

- Punctuation in what the user says (`?`, `,`, `.`) is ignored, so leave it out of templates.  Apostrophes and hyphens inside words are kept, so `qu'est-ce` and `ajoute-le` must appear exactly like that.  If speech-to-text might write them differently, list both spellings: `(ajoute-le|ajoute le)`.
- A template can start with `{item}`, but such templates match a lot, so they are always tried after the others.
- List names are often spoken with a word for "list" around them.  English uses `<todo_list> [list]`, so both "the groceries" and "the groceries list" work, as does "the shopping list" for a list named "Shopping List".  Use whatever fits your language: French uses `[liste [de|des|du]] <todo_list>`, and German uses `[liste] <todo_list> [liste]` for both "Einkaufsliste" and "Liste Einkaufen".

## item_prefixes
Words to remove from the start of `{item}` before it's looked up or added, usually articles and words like "some".  With `"du "` listed, "y a-t-il du lait" looks for "lait".  End a prefix with a space if it's a separate word (`"le "` must not remove the start of "lemon").  Leave the space off if it attaches directly, like `"l'"`.  This section is optional.

## Responses and formatting
Responses are [Jinja2 templates](https://www.home-assistant.io/docs/configuration/templating/), rendered by Home Assistant.  That's how plurals and grammar are handled: use `{% if %}` to choose the right words.

Variables:

| Response | Variables |
| --- | --- |
| `item_on_list`, `item_already_on_list` | `item`, `list`, `list_name` |
| `item_on_list_with_count`, `item_already_on_list_with_count` | `item`, `count`, `list`, `list_name` |
| `item_not_on_list`, `item_added` | `item`, `list`, `list_name` |
| `list_contents` | `items`, `item_count`, `list`, `list_name` |
| `list_empty`, `add_not_supported`, `error` | `list`, `list_name` |

- `item` is the item as written on the list when it was found there, and as spoken (minus `item_prefixes`) otherwise.
- `count` is the number from an item written like `Milk (2)`.
- `list` is the list name as rendered by `formatting.list_name`, for example "the shopping list".
- `list_name` is the list's name or alias as the user said it.
- `items` is every open item, each rendered by `formatting.list_entry` and then joined.  Items are in list order, in alphabetical order (ignoring case and accents) for `list_items_alphabetical` sentences, or soonest due first, with undated items last, for `list_items_by_due_date` sentences.  All three use the same `list_contents` and `list_empty` responses.
- `item_count` is how many open items there are.

`formatting` contains:

- `list_name`: a template with a `name` variable, deciding how a list is referred to.  English adds "list" unless the name already ends with "list".  German renders the dative, because every German response uses it after "auf" or "bei".
- `list_entry`: a template with `item` and `count` (which may be `none`), deciding how each item is read in `list_contents`.
- `separator`, `final_separator`, `pair_separator`: plain strings for joining items: "a`separator`b`final_separator`c", or "a`pair_separator`b" when there are only two.

### Plurals
Because the item is whatever the user named it, responses can't know whether it's singular or plural, or its gender.  The included languages avoid needing to know: "you've got eggs on the list" works for any item, whereas "eggs is on the list" doesn't.  French quotes the item instead: « Œufs » est bien sur la liste.

Counts and numbers of items are known, so pluralize those properly.  For example:

```yaml
# English: one / other
list_contents: >-
  {% if item_count == 1 %}There's just one thing on {{ list }}: {{ items }}.
  {%- else %}There are {{ item_count }} things on {{ list }}: {{ items }}.
  {%- endif %}

# French: 0 and 1 are singular
{% if item_count < 2 %}...{% else %}...{% endif %}

# Polish: one / few / many
{% if item_count == 1 %}jeden przedmiot
{%- elif item_count % 10 in [2, 3, 4] and item_count % 100 not in [12, 13, 14] %}{{ item_count }} przedmioty
{%- else %}{{ item_count }} przedmiotów{% endif %}
```

YAML's `>-` joins lines with spaces.  Use `{%-` to remove the space before a tag when it shouldn't be there.

## Testing
Add a few of your sentences to `test_other_languages` in `tests/test_conversation.py`, then run `./test.sh`.  `tests/test_language.py` already checks that every file in `sentences` is valid.
