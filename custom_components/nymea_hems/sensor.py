import logging
from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device_map import get_sensor_meta

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [NymeaSensor(coordinator, key) for key in coordinator.data]
    async_add_entities(sensors, update_before_add=False)


class NymeaSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, key: str):
        super().__init__(coordinator)
        self.key = key
        data = coordinator.data[key]
        self._attr_unique_id = f"nymea_{key}"
        self._attr_name = f"{data['device']} {data['state']}"

    def _get_meta(self):
        data = self.coordinator.data.get(self.key, {})
        state_name = data.get("state", "")
        nymea_unit = data.get("unit", "UnitNone")
        return get_sensor_meta(state_name, nymea_unit)

    @property
    def native_unit_of_measurement(self):
        return self._get_meta()[0]

    @property
    def device_class(self):
        return self._get_meta()[1]

    @property
    def state_class(self):
        return self._get_meta()[2]

    @property
    def native_value(self):
        data = self.coordinator.data.get(self.key)
        if data is None:
            return None
        value = data["value"]
        if self.device_class == SensorDeviceClass.TIMESTAMP and isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, float):
            return round(value, 3)
        return value

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.key in self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data.get(self.key, {})
        device_name = data.get("device", "Nymea")
        return DeviceInfo(
            identifiers={(DOMAIN, device_name)},
            name=device_name,
            manufacturer="Consolinno / Nymea",
        )

    @property
    def should_poll(self) -> bool:
        return False

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator, ignoring validation errors."""
        try:
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.debug("Skipping state write for %s: %s", self.key, err)
