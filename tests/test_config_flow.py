"""Tests for config_flow.py."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.todo_list_voice_management.config_flow import (
    TodoListVoiceConfigFlow,
)
from custom_components.todo_list_voice_management.const import DOMAIN


async def test_user_flow(hass, setup_todo):
    """Test adding the integration."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {}
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_single_instance(hass):
    """Test that only one entry can be added."""
    MockConfigEntry(domain=DOMAIN).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


def test_is_matching():
    """Test that flows are never considered duplicates of each other."""
    flow = TodoListVoiceConfigFlow()
    assert flow.is_matching(TodoListVoiceConfigFlow()) is False
