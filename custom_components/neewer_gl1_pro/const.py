"""Constants for the Neewer GL1 Pro integration."""

DOMAIN = "neewer_gl1_pro"

# GATT characteristics
WRITE_CHARACTERISTIC_UUID = "69400002-b5a3-f393-e0a9-e50e24dcca99"
NOTIFY_CHARACTERISTIC_UUID = "69400003-b5a3-f393-e0a9-e50e24dcca99"

# NEEWER protocol: [0x78, tag, length, data..., checksum]
# Checksum = sum of all preceding bytes & 0xFF
# Power tag = 0x81, data = 0x01 (on) or 0x02 (off)
POWER_ON_COMMAND = bytes([0x78, 0x81, 0x01, 0x01, 0xFB])
POWER_OFF_COMMAND = bytes([0x78, 0x81, 0x01, 0x02, 0xFC])

# Status response: [0x78, 0x02, 0x01, state, checksum]
# state = 0x01 (on) or 0x02 (off)
STATUS_TAG = 0x02
STATUS_ON = 0x01
STATUS_OFF = 0x02

# BLE local name prefix for discovery
LOCAL_NAME_PREFIX = "NEEWER-GL1"
