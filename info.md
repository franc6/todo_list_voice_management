# todo_list_voice_management
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![todo_list_voice_management](https://img.shields.io/github/v/release/franc6/todo_list_voice_management.svg?1)](https://github.com/franc6/todo_list_voice_management)
[![Coverage](https://codecov.io/gh/franc6/todo_list_voice_management/branch/releases/graph/badge.svg)](https://app.codecov.io/gh/franc6/todo_list_voice_management/branch/releases)
![Maintained:yes](https://img.shields.io/maintenance/yes/2026.svg)
[![License](https://img.shields.io/github/license/franc6/todo_list_voice_management.svg)](LICENSE)

Lets you ask Home Assistant's Assist what's on your to-do lists, and add things to a list only when they aren't already there.

Home Assistant can already add items to a to-do list by voice, but it can't tell you whether something is on a list, read a list back to you, or skip adding something that's already there.  This integration adds those sentences, in several languages, for every to-do list exposed to Assist.

> **NOTE**: If your voice assistant uses an LLM-based conversation agent (OpenAI, Anthropic, Google, Ollama, etc.), you must turn on **Prefer handling commands locally** for that assistant (Settings → Voice assistants → your assistant).  Otherwise the LLM gets your request first, and these sentences are never used.

## What you can say
`<list>` is the name of any to-do list exposed to Assist, or one of its aliases.  `<item>` is whatever you say there.  A few examples in English; each has many more variations.

| You say | You might hear |
| --- | --- |
| Is milk on the shopping list? | Yes, you've got Milk on the Shopping List, and you need 2. |
| Do we have eggs on the groceries list? | No, you don't have eggs on the Groceries list. |
| What's on the shopping list? | There are 3 things on the Shopping List: 2 Milk, Eggs, and Bread. |
| What's on the shopping list in alphabetical order? | There are 3 things on the Shopping List: Bread, Eggs, and 2 Milk. |
| If paper towels isn't on the shopping list, add it. | OK, I added paper towels to the Shopping List. |
| Add milk to the shopping list if it's not there. | You've already got Milk on the Shopping List, and you need 2. |

The full list of sentences for each language is in [custom_components/todo_list_voice_management/sentences](custom_components/todo_list_voice_management/sentences).  The English sentences include:

- **Is it on the list?** "is/are `<item>` on the `<list>` list", "is there `<item>` on…", "do we have `<item>` on…", "have I added `<item>` to…", "has `<item>` been added to…", "does the `<list>` list have `<item>`", "check if `<item>` is on…"
- **What's on the list?** "what's/what is on the `<list>` list", "what do we have on…", "what items are on…", "read me the `<list>` list", "tell me what's on…", "list everything on…"
- **What's on the list, alphabetically?** Any of the above followed by "in alphabetical order", "alphabetically", "sorted alphabetically", or "from A to Z", or "read me the alphabetized `<list>` list"
- **What's on the list, by due date?** Any of the "what's on the list" sentences followed by "by due date", "sorted by due date", "in order of priority", or "in priority order".  Items due soonest come first, and items without a due date come last, in list order.
- **Add it if it's missing.** "if `<item>` isn't on the `<list>` list, add it", "if we don't have `<item>` on…, add it", "add `<item>` to the `<list>` list if it's not there", "…unless it's already there", "…if it's missing", "make sure `<item>` is on the `<list>` list"

The word "list" after the list's name is optional, and "the", "my", and "our" are all accepted before it.  A plain "add `<item>` to the `<list>` list" is still handled by Home Assistant itself, as before.

### Counts
If an item on a list looks like `Milk (2)`, with a number in parentheses at the end, the number is treated as how many you need.  Asking about milk gets "Yes, you've got Milk on the Shopping List, and you need 2."  Reading the list says "2 Milk".  Any digits work, including non-ASCII digits.

This is the convention [OurGroceries](https://www.ourgroceries.com/) uses for quantities.  Other ways of writing a count aren't recognized yet; support for other conventions may be added in the future (submit a PR or issue).

### How items are matched
- Matching ignores case and extra spaces, so "milk" matches "Milk".
- Leading words such as "the", "some", or "any" are ignored, so "is there any milk on the list" looks for "milk".  Each language has its own list of these words.
- Completed (checked-off) items don't count as being on the list.
- If you ask to add something that's on the list but completed, it's marked as not completed again instead of being added a second time, as long as the list supports updating items.  Its due date and description are kept.

## Requirements
- Home Assistant 2026.9 or later.
- The to-do lists must be exposed to Assist (Settings → Voice assistants → Expose).  To-do lists are exposed by default.
- The sentences are handled by Home Assistant's built-in conversation agent.  If your voice assistant uses an LLM-based agent instead, turn on **Prefer handling commands locally** for that assistant.

## Languages
English, German, Spanish, and French are included.  Sentences for every included language are always active, and the answer is in the language of the sentence you used.

Responses are templates, so each language can handle plurals and grammar its own way.  To add or improve a language, see [TRANSLATING.md](TRANSLATING.md).  The German, Spanish, and French files would benefit from review by native speakers.

## Configuration
Go to Settings → Devices & services → Add integration, and choose **To-do List Voice Management**.  There's nothing else to configure.  New lists, renamed lists, aliases, and changes to which lists are exposed are picked up automatically.
