import json
import logging
from datetime import datetime


_LOGGER = logging.getLogger(__file__)


class MeaterApi(object):
    """Meater api object"""

    def __init__(self, aiohttp_session):
        self._jwt = None
        self._session = aiohttp_session

    async def get_devices(self, device_id=None):
        """Get all the device states."""
        device_states = await self.__get_raw_state(device_id)
        devices = []
        for index, device in enumerate(device_states):
            _LOGGER.debug(f"Device: {device}")
            probe = MeaterProbe(
                device.get("id"),
                device.get("temperature").get("internal"),
                device.get("temperature").get("ambient"),
                device.get("cook"),
                device.get("updated_at"),
                index + 1,
            )
            devices.append(probe)

        return devices

    async def get_device(self, device_id):
        """Get specific device state."""
        return await self.get_devices(device_id)

    async def __get_raw_state(self, device_id=None):
        """Get raw device state from the Meater API. We have to have authenticated before now."""
        if not self._jwt:
            raise AuthenticationError(
                "You need to authenticate before making requests to the API."
            )

        headers = {"Authorization": "Bearer " + self._jwt}
        url = "https://public-api.cloud.meater.com/v1/devices/"
        if device_id is not None:
            url += device_id

        async with self._session.get(
            url,
            headers=headers,
        ) as device_state_request:
            if device_state_request.status == 404:
                raise UnknownDeviceError(
                    "The specified device could not be found, it might not be connected to Meater Cloud"
                )

            if device_state_request.status == 401:
                raise AuthenticationError("Unable to authenticate with the Meater API")

            if device_state_request.status == 500:
                raise ServiceUnavailableError("The service is currently unavailable")

            if device_state_request.status == 429:
                raise TooManyRequestsError(
                    "Too many requests have been made to the API"
                )

            if device_state_request.status != 200:
                raise Exception("Error connecting to Meater")

            device_state_body = await device_state_request.json()
            if len(device_state_body) == 0:
                raise Exception("The server did not return a valid response")

            if device_id is not None:
                return device_state_body.get("data")
            else:
                return device_state_body.get("data").get("devices")

    async def authenticate(self, email, password):
        """Authenticate with Meater."""

        headers = {"Content-Type": "application/json"}
        body = {"email": email, "password": password}

        async with self._session.post(
            "https://public-api.cloud.meater.com/v1/login",
            data=json.dumps(body),
            headers=headers,
        ) as meater_auth_req:
            if meater_auth_req.status == 401:
                raise AuthenticationError("The specified credientals were incorrect")

            if meater_auth_req.status == 500:
                raise ServiceUnavailableError("The service is currently unavailable")

            if meater_auth_req.status == 429:
                raise TooManyRequestsError(
                    "Too many requests have been made to the API"
                )

            if meater_auth_req.status != 200:
                raise Exception("Couldn't authenticate with the Meater API")

            auth_body = await meater_auth_req.json()

            jwt = auth_body.get("data").get("token")  # The JWT is valid indefinitely...

            if not jwt:
                raise AuthenticationError(
                    "Unable to obtain an auth token from the Meater API"
                )

            # Set JWT local variable
            self._jwt = jwt

            return True


class MeaterProbe(object):
    """Meater probe class."""

    def __init__(
        self, id, internal_temp, ambient_temp, cookdata, time_updated, index=1
    ):
        """Initialization for MeaterProbe class."""
        self.id = id
        self.index = index
        self.internal_temperature = float(internal_temp)  # Always in degrees celcius
        self.ambient_temperature = float(ambient_temp)  # Always in degrees celcius
        self.cook = None if cookdata is None else MeaterCook(cookdata)
        self.time_updated = datetime.fromtimestamp(time_updated)

    def __str__(self):
        return f"\nMeaterprobe {self.index} - Temp: {self.internal_temperature}°C Ambient: {self.ambient_temperature}°C Updated: {self.time_updated} \nCook: {str(self.cook)}"


class MeaterCook(object):
    """Meater cook class."""

    def __init__(
        self,
        cookdata,
    ):
        """Initialization for MeaterCook class."""

        self.id = cookdata.get("id", None)
        self.name = cookdata.get("name", None)
        self.state = cookdata.get("state", None)

        # Temperatures in Celsius
        self.target_temperature = float(cookdata.get("temperature").get("target"))
        self.peak_temperature = float(cookdata.get("temperature").get("peak"))

        # Time in seconds
        self.time_remaining = int(cookdata.get("time").get("remaining"))
        self.time_elapsed = int(cookdata.get("time").get("elapsed"))

    def __str__(self):
        return f"MeaterCook - {self.name} State: {self.state} Target: {self.target_temperature}°C Peak: {self.peak_temperature}°C Elapsed: {self.time_elapsed}sec Remaining: {self.time_remaining}sec"


class UnknownDeviceError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class ServiceUnavailableError(Exception):
    pass


class TooManyRequestsError(Exception):
    pass
