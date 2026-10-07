"""Config flow for todo_list_voice_management."""

from typing import Any, Self

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class TodoListVoiceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow; there is nothing to configure beyond confirming."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding the integration.

        :param user_input: The submitted form, or None to show the form
        :type user_input: dict[str, Any] | None
        :returns: The next step of the flow
        :rtype: ConfigFlowResult
        """
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="To-do List Voice", data={})

    def is_matching(self, _other_flow: Self) -> bool:
        """Return False; single_config_entry already prevents duplicates.

        :param _other_flow: Another in-progress flow
        :type _other_flow: Self
        :returns: False
        :rtype: bool
        """
        return False
