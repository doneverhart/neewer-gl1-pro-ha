"""Light platform for Neewer GL1 Pro."""

from __future__ import annotations

import asyncio
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
    NOTIFY_CHARACTERISTIC_UUID,
    POWER_OFF_COMMAND,
    POWER_ON_COMMAND,
    STATUS_OFF,
    STATUS_ON,
    STATUS_TAG,
    WRITE_CHARACTERISTIC_UUID,
)

_LOGGER = logging.getLogger(__name__)

# Timeout for waiting for a status notification after sending a command
NOTIFY_TIMEOUT = 5.0


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

    async def _connect(self) -> BleakClient:
        """Connect to the device, trying HA Bluetooth cache first, then direct."""
        ble_device = async_ble_device_from_address(self._hass, self._address)
        if ble_device is not None:
            return await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                self._address,
            )

        _LOGGER.debug(
            "Device %s not in HA Bluetooth cache, connecting directly",
            self._address,
        )
        client = BleakClient(self._address)
        await client.connect()
        return client

    async def _send_command(self, command: bytes) -> bool | None:
        """Send a command and wait for the status notification.

        Returns True if on, False if off, None if no response received.
        """
        status_event = asyncio.Event()
        result: list[bool | None] = [None]

        def on_notify(_sender: Any, data: bytearray) -> None:
            # Status response: [0x78, 0x02, 0x01, state, checksum]
            if len(data) >= 4 and data[1] == STATUS_TAG:
                state = data[3]
                if state == STATUS_ON:
                    result[0] = True
                elif state == STATUS_OFF:
                    result[0] = False
                status_event.set()

        try:
            client = await self._connect()
            try:
                await client.start_notify(NOTIFY_CHARACTERISTIC_UUID, on_notify)
                await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, command)

                try:
                    await asyncio.wait_for(status_event.wait(), NOTIFY_TIMEOUT)
                except TimeoutError:
                    _LOGGER.debug(
                        "No status notification from %s within %ss",
                        self._address,
                        NOTIFY_TIMEOUT,
                    )

                await client.stop_notify(NOTIFY_CHARACTERISTIC_UUID)
            finally:
                await client.disconnect()
        except BleakError as err:
            _LOGGER.error(
                "Failed to send command to %s: %s", self._address, err
            )

        return result[0]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        status = await self._send_command(POWER_ON_COMMAND)
        self._attr_is_on = status if status is not None else True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        status = await self._send_command(POWER_OFF_COMMAND)
        self._attr_is_on = status if status is not None else False
        self.async_write_ha_state()
