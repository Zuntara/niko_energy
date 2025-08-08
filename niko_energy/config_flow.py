"""Config flow for Niko Energy Monitor."""
from __future__ import annotations
import logging
import socket
import json
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_NIKO_HOST, CONF_NIKO_PORT, CONF_MQTT_BROKER, CONF_MQTT_PORT, CONF_MQTT_USER, CONF_MQTT_PASS, CONF_CHANNELS, DEFAULT_PORT, DEFAULT_MQTT_PORT

_LOGGER = logging.getLogger(__name__)

async def detect_niko_channels(host, port):
    """Detect available channels from Niko controller."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            
            # Send commands
            commands = [
                {"cmd": "startevents"},
                {"cmd": "systeminfo"}
            ]
            
            for cmd in commands:
                s.sendall((json.dumps(cmd) + "\r\n").encode('utf-8'))
                s.recv(4096)  # Discard response
            
            # Get channels from listenergy
            s.sendall(b'{"cmd":"listenergy"}\r\n')
            response = s.recv(4096).decode('utf-8').strip()
            
            if response:
                data = json.loads(response)
                return [
                    {
                        "channel": str(ch["channel"]),
                        "name": ch["name"],
                        "type": ch["type"]
                    } for ch in data.get("data", [])
                ]
    except Exception as e:
        _LOGGER.error("Channel detection failed: %s", e)
    return []

class NikoEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Niko Energy Monitor."""
    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self.detected_channels = []
        self.user_input = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            self.user_input = user_input
            # Try to detect channels
            self.detected_channels = await detect_niko_channels(
                user_input[CONF_NIKO_HOST],
                user_input[CONF_NIKO_PORT]
            )
            
            if not self.detected_channels:
                errors["base"] = "no_channels"
            else:
                return await self.async_step_configure_channels()
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NIKO_HOST, default="192.168.3.40"): str,
                vol.Required(CONF_NIKO_PORT, default=DEFAULT_PORT): int
            }),
            errors=errors,
        )

    async def async_step_configure_channels(self, user_input=None) -> FlowResult:
        """Configure detected channels."""
        errors = {}
        if user_input is not None:
            # Save channel configuration
            channels_config = {}
            for channel in self.detected_channels:
                ch_id = channel["channel"]
                channels_config[ch_id] = {
                    "name": user_input.get(f"name_{ch_id}", channel["name"])
                }
            
            # Create final config entry
            data = {**self.user_input, CONF_CHANNELS: channels_config}
            return self.async_create_entry(
                title="Niko Energy Monitor", 
                data=data
            )
        
        # Create form with detected channels
        fields = {}
        for channel in self.detected_channels:
            ch_id = channel["channel"]
            fields[vol.Optional(
                f"name_{ch_id}", 
                default=channel["name"],
                description={"suggested_value": channel["name"]}
            )] = str
        
        return self.async_show_form(
            step_id="configure_channels",
            data_schema=vol.Schema(fields),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return NikoEnergyOptionsFlow(config_entry)

class NikoEnergyOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Niko Energy Monitor."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.channels_config = config_entry.data.get(CONF_CHANNELS, {})

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_configure_channels()

    async def async_step_configure_channels(self, user_input=None):
        """Configure channels mapping."""
        errors = {}
        if user_input is not None:
            # Update channel configuration
            new_config = {}
            for ch_id in self.channels_config:
                new_config[ch_id] = {
                    "name": user_input.get(f"name_{ch_id}", self.channels_config[ch_id]["name"])
                }
            
            # Update the entry
            data = {**self.config_entry.data, CONF_CHANNELS: new_config}
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            return self.async_create_entry(title="", data={})
        
        # Create form with current channels
        fields = {}
        for ch_id, config in self.channels_config.items():
            fields[vol.Optional(
                f"name_{ch_id}", 
                default=config["name"],
                description={"suggested_value": config["name"]}
            )] = str
        
        return self.async_show_form(
            step_id="configure_channels",
            data_schema=vol.Schema(fields),
            errors=errors,
        )