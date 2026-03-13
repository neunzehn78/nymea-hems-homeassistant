import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .energy_calculations import calculate_energy_metrics
from .nymea_client import NymeaClient, NymeaConnectionError, NymeaAuthError

_LOGGER = logging.getLogger(__name__)


class NymeaCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, client: NymeaClient):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            # No update_interval – we drive polling ourselves via async_track_time_interval
            update_interval=None,
        )
        self.client = client
        self._state_type_map: dict[str, dict] = {}
        self._unsub_timer = None
        self._poll_lock = asyncio.Lock()

    async def async_start_polling(self) -> None:
        """Start the periodic poll timer. Call after first_refresh."""
        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._timer_callback,
            timedelta(seconds=SCAN_INTERVAL),
        )
        _LOGGER.debug("Nymea polling started, interval=%ss", SCAN_INTERVAL)

    def async_stop_polling(self) -> None:
        """Stop the periodic poll timer."""
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _timer_callback(self, _now) -> None:
        """Called by async_track_time_interval – schedule an async refresh."""
        self.hass.async_create_task(self._do_poll())

    async def _do_poll(self) -> None:
        """Fetch new data and push it to all listeners."""
        if self._poll_lock.locked():
            _LOGGER.debug("Poll skipped – previous poll still running")
            return
        async with self._poll_lock:
            await self._do_poll_locked()

    async def _do_poll_locked(self) -> None:
        """Actual poll logic, protected by lock."""
        _LOGGER.debug("Poll started")
        try:
            sensors = await asyncio.wait_for(self._fetch_data(), timeout=25)
        except asyncio.TimeoutError:
            _LOGGER.warning("Nymea poll timed out after 25s")
            await self.client.disconnect()
            self.last_update_success = False
            self.async_update_listeners()
            return
        except UpdateFailed as err:
            _LOGGER.warning("Nymea poll failed: %s", err)
            self.last_update_success = False
            self.async_update_listeners()
            return

        self.last_update_success = True
        try:
            self.async_set_updated_data(sensors)
        except Exception as err:
                # Set data and notify listeners manually if async_set_updated_data failed
            self.data = sensors
            self.last_update_success = True
            self.async_update_listeners()
        _LOGGER.debug("Poll done, %d sensors", len(sensors))

    async def _async_update_data(self) -> dict:
        """Called by DataUpdateCoordinator for the initial refresh only."""
        return await self._fetch_data()

    async def _fetch_data(self) -> dict:
        """Connect, authenticate, fetch Things, return sensor dict."""
        try:
            await self.client.disconnect()
            await self.client.authenticate()

            if not self._state_type_map:
                await self._build_state_type_map()

            things = await self.client.get_things()

        except NymeaAuthError as err:
            await self.client.disconnect()
            raise UpdateFailed(f"Authentication error: {err}") from err
        except NymeaConnectionError as err:
            await self.client.disconnect()
            raise UpdateFailed(f"Connection error: {err}") from err

        await self.client.disconnect()
        sensors: dict = {}
        things_states: dict = {}

        for thing in things:
            device_name: str = thing.get("name", "Unknown")
            things_states[device_name] = {}
            for state in thing.get("states", []):
                state_type_id: str = state.get("stateTypeId", "")
                value = state.get("value")

                meta = self._state_type_map.get(state_type_id, {})
                state_name: str = meta.get("name", state_type_id)
                unit: str = meta.get("unit", "")

                key = f"{device_name}_{state_name}"
                sensors[key] = {
                    "device": device_name,
                    "state": state_name,
                    "value": value,
                    "unit": unit,
                }
                things_states[device_name][state_name] = value

        calculated = calculate_energy_metrics(things_states)
        for metric, value in calculated.items():
            sensors[f"energy_{metric}"] = {
                "device": "Energy System",
                "state": metric,
                "value": value,
                "unit": "UnitWatt",
            }

        return sensors

    async def _build_state_type_map(self) -> None:
        thing_classes = await self.client.get_thing_classes()
        self._state_type_map.clear()
        for tc in thing_classes.values():
            for st in tc.get("stateTypes", []):
                st_id = st.get("id")
                if st_id:
                    self._state_type_map[st_id] = {
                        "name": st.get("name", st_id),
                        "unit": st.get("unit", ""),
                    }
        _LOGGER.debug("State type map built: %d entries", len(self._state_type_map))
