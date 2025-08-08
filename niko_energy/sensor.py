import logging
import socket
import json
import threading
import asyncio
from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfEnergy
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.core import callback
from .const import DOMAIN, CONF_NIKO_HOST, CONF_NIKO_PORT, CONF_CHANNELS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    monitor = NikoMonitor(hass, config_entry)
    
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][config_entry.entry_id] = monitor

    monitor.start()
    
    await hass.async_add_executor_job(monitor.initialized.wait)

    async def _shutdown_listener(event):
        _LOGGER.warn("Stopping Niko monitor on shutdown.")
        monitor.stop()
        await hass.async_add_executor_job(monitor.join)

    hass.bus.async_listen_once("homeassistant_stop", _shutdown_listener)
    
    entities = []
    channels = config_entry.data.get(CONF_CHANNELS, {})
    for ch_id, ch_conf in channels.items():
        entities.append(NikoPowerSensor(monitor, ch_id, ch_conf["name"]))
        entities.append(NikoEnergySensor(monitor, ch_id, ch_conf["name"]))

    async_add_entities(entities)

    return True

class NikoMonitor(threading.Thread):
    def __init__(self, hass, config_entry):
        super().__init__(daemon=True)
        self.hass = hass
        self.config_entry = config_entry
        self.values = {"power": {}, "energy": {}}
        self._last_update_time = {} 
        self.socket = None
        self.running = True
        self.initialized = threading.Event()
        self._lock = threading.Lock()

        # Houd een lijst bij van update callbacks van sensoren
        self._update_callbacks = []

    def register_update_callback(self, callback):
        self._update_callbacks.append(callback)

    def ask_live_results(self, channels):
        for ch_id in channels:
            self._send_command({"cmd": "getlive", "channel": int(ch_id)})
            self._receive_response()
        
    def run(self):
        _LOGGER.warn("Starting NikoMonitor thread.")
        try:
            config = self.config_entry.data
            niko_host = config[CONF_NIKO_HOST]
            niko_port = config[CONF_NIKO_PORT]
            channels = config.get(CONF_CHANNELS, {})

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((niko_host, niko_port))

            self._send_command({"cmd": "startevents"})
            self._receive_response()
            self._send_command({"cmd": "systeminfo"})
            self._receive_response()

            self.ask_live_results(channels)
            counter = 0
            
            self.initialized.set()

            buffer = b""
            while self.running:
                try:
                    data = self.socket.recv(1024)
                    if not data:
                        break
                    buffer += data
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        decoded = line.decode("utf-8").strip()
                        if decoded.startswith("{"):
                            self._process_message(decoded)
                            
                    counter += 1
                    if counter >= 5:
                        self.ask_live_results(channels)
                        counter = 0
    
                except socket.timeout:
                    continue
                except Exception as e:
                    _LOGGER.error("Error in main loop: %s", e)
                    break
        except Exception as e:
            _LOGGER.error("Connection failed: %s", e)
        finally:
            self.stop()

    def _process_message(self, message):
        try:
            msg = json.loads(message)
            if msg.get("event") == "getlive":
                ch_id = str(msg["data"]["channel"])
                watt = msg["data"]["v"]
    
                now = datetime.utcnow()
    
                with self._lock:
                    # update power
                    self.values["power"][ch_id] = watt
    
                    # bereken energie op basis van tijdverschil sinds laatste update
                    if ch_id in self._last_update_time:
                        elapsed_seconds = (now - self._last_update_time[ch_id]).total_seconds()
                        # energie in kWh = (W / 1000) * (seconden / 3600)
                        delta_kwh = (watt / 1000) * (elapsed_seconds / 3600)
                        self.values["energy"][ch_id] = self.values["energy"].get(ch_id, 0) + delta_kwh
                        #_LOGGER.warn("Update energy: Channel %s - Energy: %s kWh", ch_id, delta_kwh)
                    else:
                        # Eerste keer: init energie
                        self.values["energy"][ch_id] = self.values["energy"].get(ch_id, 0)
                        #_LOGGER.warn("Init energy: Channel %s - Energy: %s kWh", ch_id, 0)
    
                    self._last_update_time[ch_id] = now
    
                self._notify_sensors(ch_id)
        except Exception as e:
            _LOGGER.error("Error processing message: %s", e)

    def _notify_sensors(self, ch_id):
        for callback in self._update_callbacks:
            try:
                future = asyncio.run_coroutine_threadsafe(callback(ch_id), self.hass.loop)
            except Exception as e:
                _LOGGER.error("Failed to schedule sensor update: %s", e)
    
    def _send_command(self, cmd_dict):
        try:
            self.socket.sendall((json.dumps(cmd_dict) + "\r\n").encode("utf-8"))
        except Exception as e:
            _LOGGER.error("Command send failed: %s", e)

    def _receive_response(self, timeout=100):
        try:
            self.socket.settimeout(timeout)
            response = self.socket.recv(4096).decode("utf-8").strip()
            #_LOGGER.warn("NHC response: %s", response)
            return response
        except Exception as e:
            _LOGGER.error("Error receiving message: %s", e)
            return None

    def stop(self):
        _LOGGER.warn("Stopping NikoMonitor thread.")
        self.running = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)  # sluit beide richtingen
            except Exception:
                pass
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None


class NikoPowerSensor(SensorEntity):
    def __init__(self, monitor, channel_id, channel_name):
        self.monitor = monitor
        self.channel_id = channel_id
        self._attr_name = f"{channel_name} Power"
        self._attr_unique_id = f"niko_power_{channel_id}"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = None

    async def async_added_to_hass(self):
        async def _update(ch_id):
            if ch_id == self.channel_id:
                self.async_write_ha_state()

        self.monitor.register_update_callback(_update)

    @property
    def native_value(self):
        return self.monitor.values["power"].get(self.channel_id)

    @property
    def should_poll(self):
        return False

class NikoEnergySensor(SensorEntity):
    def __init__(self, monitor, channel_id, channel_name):
        self.monitor = monitor
        self.channel_id = channel_id
        self._attr_name = f"{channel_name} Energy"
        self._attr_unique_id = f"niko_energy_{channel_id}"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._state = 0

    async def async_added_to_hass(self):
        async def _update(ch_id):
            if ch_id == self.channel_id:
                self.async_write_ha_state()
    
        self.monitor.register_update_callback(_update)

    @property
    def native_value(self):
        return self.monitor.values["energy"].get(self.channel_id, 0.0)

    @property
    def should_poll(self):
        return False
