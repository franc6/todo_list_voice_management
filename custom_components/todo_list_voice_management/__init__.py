"""Voice queries and conditional adds for Home Assistant to-do lists."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .language import async_load_languages
from .manager import TodoListVoiceManager

type TodoListVoiceConfigEntry = ConfigEntry[TodoListVoiceManager]


async def async_setup_entry(
    hass: HomeAssistant, entry: TodoListVoiceConfigEntry
) -> bool:
    """Set up todo_list_voice_management from a config entry.

    :param hass: The Home Assistant instance
    :type hass: HomeAssistant
    :param entry: The config entry
    :type entry: TodoListVoiceConfigEntry
    :returns: True
    :rtype: bool
    """
    manager = TodoListVoiceManager(hass, await async_load_languages(hass))
    manager.async_start()
    entry.runtime_data = manager
    return True


async def async_unload_entry(
    _hass: HomeAssistant, entry: TodoListVoiceConfigEntry
) -> bool:
    """Unload a config entry.

    :param _hass: The Home Assistant instance
    :type _hass: HomeAssistant
    :param entry: The config entry
    :type entry: TodoListVoiceConfigEntry
    :returns: True
    :rtype: bool
    """
    entry.runtime_data.async_stop()
    return True
