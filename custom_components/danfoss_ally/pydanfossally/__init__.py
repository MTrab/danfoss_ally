import logging

from .danfossallyapi import *

_LOGGER = logging.getLogger(__name__)

__version__ = "0.0.26"


class DanfossAlly:
    """Danfoss Ally API connector."""

    def __init__(self):
        """Init the API connector variables."""
        self._authorized = False
        self._token = None
        self.devices = {}

        self._api = DanfossAllyAPI()

    def initialize(self, key, secret):
        """Authorize and initialize the connection."""

        token = self._api.getToken(key, secret)

        if token is False:
            self._authorized = False
            _LOGGER.error("Error in authorization")
            return False

        _LOGGER.debug("Token received: %s", self._api.token)
        self._token = self._api.token
        self._authorized = True
        return self._authorized

    def getDeviceList(self):
        """Get device list."""
        devices = self._api.get_devices()

        if devices is None:
            _LOGGER.error("No devices loaded, API error?!")
            return

        if not devices:
            _LOGGER.error("No devices loaded, API connection error?!")
            return

        if not "result" in devices:
            _LOGGER.error("Something went wrong loading devices!")
            return

        for device in devices["result"]:
            self.handleDeviceDate(device)

    def handleDeviceDate(self, device):
        self.devices[device["id"]] = {}
        self.devices[device["id"]]["isThermostat"] = False
        self.devices[device["id"]]["name"] = device["name"].strip()
        self.devices[device["id"]]["online"] = device["online"]
        self.devices[device["id"]]["update"] = device["update_time"]
        if "model" in device:
            self.devices[device["id"]]["model"] = device["model"]

        bHasFloorSensor = False
        for status in device["status"]:
            if status["code"] == "floor_sensor":
                bHasFloorSensor = status["value"]
        self.devices[device["id"]]["floor_sensor"] = bHasFloorSensor

        for status in device["status"]:
            # if status["code"] == "temp_set":
            #     setpoint = float(status["value"])
            #     setpoint = setpoint / 10
            #     self.devices[device["id"]]["setpoint"] = setpoint
            #     self.devices[device["id"]]["isThermostat"] = True
            if status["code"] in ["manual_mode_fast", "at_home_setting", "leaving_home_setting", "pause_setting", "holiday_setting"]:
                setpoint = float(status["value"])
                setpoint = setpoint / 10
                self.devices[device["id"]][status["code"]] = setpoint
                self.devices[device["id"]]["isThermostat"] = True
            elif status["code"] == "temp_current":
                temperature = float(status["value"])
                temperature = temperature / 10
                self.devices[device["id"]]["temperature"] = temperature
            elif status["code"] == "MeasuredValue" and bHasFloorSensor:       # Floor sensor
                temperature = float(status["value"])
                temperature = temperature / 10
                self.devices[device["id"]]["floor temperature"] = temperature
            elif status["code"] == "upper_temp":
                temperature = float(status["value"])
                temperature = temperature / 10
                self.devices[device["id"]]["upper_temp"] = temperature
            elif status["code"] == "lower_temp":
                temperature = float(status["value"])
                temperature = temperature / 10
                self.devices[device["id"]]["lower_temp"] = temperature
            elif status["code"] == "va_temperature":
                temperature = float(status["value"])
                temperature = temperature / 10
                self.devices[device["id"]]["temperature"] = temperature
            elif status["code"] == "va_humidity":
                humidity = float(status["value"])
                humidity = humidity / 10
                self.devices[device["id"]]["humidity"] = humidity
            elif status["code"] == "battery_percentage":
                battery = status["value"]
                self.devices[device["id"]]["battery"] = battery
            elif status["code"] == "window_state":
                window = status["value"]
                if window == "open":
                    self.devices[device["id"]]["window_open"] = True
                else:
                    self.devices[device["id"]]["window_open"] = False
            elif status["code"] == "child_lock":
                childlock = status["value"]
                self.devices[device["id"]]["child_lock"] = childlock
            elif status["code"] == "mode":
                self.devices[device["id"]]["mode"] = status["value"]
            elif status["code"] == "work_state":
                self.devices[device["id"]]["work_state"] = status["value"]


    def getDevice(self, device_id):
        """Get device data."""
        device = self._api.get_device(device_id)

        if device is None or not device:
            _LOGGER.error("No device loaded, API error?!")
            return
        if not "result" in device:
            _LOGGER.error("Something went wrong loading devices!")
            return

        self.handleDeviceDate(device["result"])

    @property
    def authorized(self):
        """Return authorized status."""
        return self._authorized

    def setTemperature(self, device_id: str, temp: float, code = "manual_mode_fast") -> bool:
        """Updates temperature setpoint for given device."""
        temperature = int(temp * 10)

        result = self._api.set_temperature(device_id, temperature, code)

        return result


    def setMode(self, device_id: str, mode: str) -> bool:
        """Updates operating mode for given device."""
        result = self._api.set_mode(device_id, mode)

        return result
