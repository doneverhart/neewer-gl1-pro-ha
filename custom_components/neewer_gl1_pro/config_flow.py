"""Config flow for Neewer GL1 Pro integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, LOCAL_NAME_PREFIX

_LOGGER = logging.getLogger(__name__)


class NeewerGL1ProConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Neewer GL1 Pro."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the Bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        assert self._discovery_info is not None
        discovery_info = self._discovery_info

        title = discovery_info.name or f"Neewer GL1 Pro ({discovery_info.address})"

        if user_input is not None:
            return self.async_create_entry(title=title, data={
                CONF_ADDRESS: discovery_info.address,
            })

        self._set_confirm_only()
        placeholders = {"name": title}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=placeholders,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick a discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            title = self._discovered_devices.get(
                address, f"Neewer GL1 Pro ({address})"
            )
            return self.async_create_entry(title=title, data={
                CONF_ADDRESS: address,
            })

        current_addresses = self._async_current_ids()
        for info in async_discovered_service_info(self.hass):
            if (
                info.address not in current_addresses
                and info.name
                and info.name.startswith(LOCAL_NAME_PREFIX)
            ):
                self._discovered_devices[info.address] = info.name

        if not self._discovered_devices:
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices),
            }),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual address entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            if len(address) != 17 or address.count(":") != 5:
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address, raise_on_progress=False)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Neewer GL1 Pro ({address})",
                    data={CONF_ADDRESS: address},
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): str,
            }),
            errors=errors,
        )
