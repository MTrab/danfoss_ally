import base64
import datetime
import json
import logging

import requests

API_HOST = "https://api.danfoss.com"

_LOGGER = logging.getLogger(__name__)


class DanfossAllyAPI:
    def __init__(self):
        """Init API."""
        self._key = ""
        self._secret = ""
        self._token = ""
        self._refresh_at = datetime.datetime.now()

    def _call(self, path, headers_data, payload=None):
        """Do the actual API call async."""

        self._refresh_token()
        try:
            if payload:
                req = requests.post(
                    API_HOST + path, json=payload, headers=headers_data, timeout=10
                )
            else:
                req = requests.get(API_HOST + path, headers=headers_data, timeout=10)

            if not req.ok:
                return False
        except TimeoutError:
            _LOGGER.warning("Timeout communication with Danfoss Ally API")
            return False
        except:
            _LOGGER.warning(
                "Unexpected error occured in communications with Danfoss Ally API!"
            )
            return False

        return req.json()

    def _refresh_token(self):
        """Refresh OAuth2 token if expired."""
        if self._refresh_at > datetime.datetime.now():
            return False

        self.getToken()

    def _generate_base64_token(self, key: str, secret: str) -> str:
        """Generates a base64 token"""
        key_secret = key + ":" + secret
        key_secret_bytes = key_secret.encode("ascii")
        base64_bytes = base64.b64encode(key_secret_bytes)
        base64_token = base64_bytes.decode("ascii")

        return base64_token

    def getToken(self, key=None, secret=None) -> str:
        """Get token."""

        if not key is None:
            self._key = key
        if not secret is None:
            self._secret = secret

        base64_token = self._generate_base64_token(self._key, self._secret)

        header_data = {}
        header_data["Content-Type"] = "application/x-www-form-urlencoded"
        header_data["Authorization"] = "Basic " + base64_token
        header_data["Accept"] = "application/json"

        post_data = "grant_type=client_credentials"
        try:
            req = requests.post(
                API_HOST + "/oauth2/token",
                data=post_data,
                headers=header_data,
                timeout=10,
            )

            if not req.ok:
                return False
        except TimeoutError:
            _LOGGER.warning("Timeout communication with Danfoss Ally API")
            return False
        except:
            _LOGGER.warning(
                "Unexpected error occured in communications with Danfoss Ally API!"
            )
            return False

        callData = req.json()

        if callData is False:
            return False

        expires_in = float(callData["expires_in"])
        self._refresh_at = datetime.datetime.now()
        self._refresh_at = self._refresh_at + datetime.timedelta(seconds=expires_in)
        self._refresh_at = self._refresh_at + datetime.timedelta(seconds=-30)
        self._token = callData["access_token"]
        return True

    def get_devices(self):
        """Get list of all devices."""

        header_data = {}
        header_data["Accept"] = "application/json"
        header_data["Authorization"] = "Bearer " + self._token

        callData = self._call("/ally/devices", header_data)

        return callData

    def get_device(self, device_id: str):
        """Get device details."""

        header_data = {}
        header_data["Accept"] = "application/json"
        header_data["Authorization"] = "Bearer " + self._token

        callData = self._call("/ally/devices/" + device_id, header_data)

        return callData

    def set_temperature(self, device_id: str, temp: int, code = "manual_mode_fast") -> bool:
        """Set temperature setpoint."""

        header_data = {}
        header_data["Accept"] = "application/json"
        header_data["Authorization"] = "Bearer " + self._token

        #request_body = {"commands": [{"code": "temp_set", "value": temp}]}
        request_body = {"commands": [{"code": code, "value": temp}]}

        callData = self._call(
            "/ally/devices/" + device_id + "/commands", header_data, request_body
        )

        _LOGGER.debug("Set temperature for device %s: %s", device_id, json.dumps(request_body))

        return callData["result"]



    def set_mode(self, device_id: str, mode: str) -> bool:
        """Set device operating mode."""

        header_data = {}
        header_data["Accept"] = "application/json"
        header_data["Authorization"] = "Bearer " + self._token

        request_body = {"commands": [{"code": "mode", "value": mode}]}

        callData = self._call(
            "/ally/devices/" + device_id + "/commands", header_data, request_body
        )

        return callData["result"]

    def set_mode(self, device_id, mode) -> bool:
        """Set mode."""

        header_data = {}
        header_data["Accept"] = "application/json"
        header_data["Authorization"] = "Bearer " + self._token

        request_body = {"commands": [{"code": "mode", "value": mode}]}

        callData = self._call(
            "/ally/devices/" + device_id + "/commands", header_data, request_body
        )

        return callData["result"]

    @property
    def token(self) -> str:
        """Return token."""
        return self._token
