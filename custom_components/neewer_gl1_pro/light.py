"""Light platform for Neewer GL1 Pro."""

from __future__ import annotations

import logging
from typing import Any

from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    POWER_OFF_COMMAND,
    POWER_ON_COMMAND,
    WRITE_CHARACTERISTIC_UUID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Neewer GL1 Pro light from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    async_add_entities([NeewerGL1ProLight(hass, entry, address)])


class NeewerGL1ProLight(LightEntity):
    """Representation of a Neewer GL1 Pro light."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF
    _attr_assumed_state = True

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, address: str
    ) -> None:
        """Initialize the light."""
        self._hass = hass
        self._address = address
        self._attr_unique_id = address.replace(":", "_")
        self._attr_is_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=entry.title,
            manufacturer="Neewer",
            model="GL1 Pro",
        )

    async def _send_command(self, command: bytes) -> None:
        """Connect to the device and send a GATT write command."""
        try:
            # Try HA's Bluetooth integration first (works with auto-discovered devices)
            ble_device = async_ble_device_from_address(self._hass, self._address)
            if ble_device is not None:
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    ble_device,
                    self._address,
                )
                try:
                    await client.write_gatt_char(
                        WRITE_CHARACTERISTIC_UUID, command
                    )
                finally:
                    await client.disconnect()
                return

            # Fallback: connect directly by address (for manually added devices)
            _LOGGER.debug(
                "Device %s not in HA Bluetooth cache, connecting directly",
                self._address,
            )
            client = BleakClient(self._address)
            await client.connect()
            try:
                await client.write_gatt_char(
                    WRITE_CHARACTERISTIC_UUID, command
                )
            finally:
                await client.disconnect()
        except BleakError as err:
            _LOGGER.error(
                "Failed to send command to %s: %s", self._address, err
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._send_command(POWER_ON_COMMAND)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._send_command(POWER_OFF_COMMAND)
        self._attr_is_on = False
        self.async_write_ha_state()
