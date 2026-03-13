from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

# Maps Nymea unit strings -> (ha_unit, device_class, state_class)
UNIT_MAP: dict[str, tuple[str | None, str | None, str | None]] = {
    "UnitWatt":                   ("W",       SensorDeviceClass.POWER,       SensorStateClass.MEASUREMENT),
    "UnitKiloWatt":               ("kW",      SensorDeviceClass.POWER,       SensorStateClass.MEASUREMENT),
    "UnitWattHour":               ("Wh",      SensorDeviceClass.ENERGY,      SensorStateClass.TOTAL_INCREASING),
    "UnitKiloWattHour":           ("kWh",     SensorDeviceClass.ENERGY,      SensorStateClass.TOTAL_INCREASING),
    "UnitVolt":                   ("V",       SensorDeviceClass.VOLTAGE,     SensorStateClass.MEASUREMENT),
    "UnitAmpere":                 ("A",       SensorDeviceClass.CURRENT,     SensorStateClass.MEASUREMENT),
    "UnitHertz":                  ("Hz",      SensorDeviceClass.FREQUENCY,   SensorStateClass.MEASUREMENT),
    "UnitPercentage":             ("%",       SensorDeviceClass.BATTERY,     SensorStateClass.MEASUREMENT),
    "UnitDegreeCelsius":          ("°C",      SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    "UnitEuroCentPerKiloWattHour":("ct/kWh",  None,                           SensorStateClass.MEASUREMENT),
    "UnitEuroPerKiloWattHour":    ("EUR/kWh", None,                           SensorStateClass.MEASUREMENT),
    "UnitHours":                  ("h",       SensorDeviceClass.DURATION,    SensorStateClass.MEASUREMENT),
    "UnitUnixTime":               (None,      SensorDeviceClass.TIMESTAMP,   None),
    "UnitNone":                   (None,      None,                           None),
}

# Override device_class for specific state names where the unit-based guess is wrong.
# e.g. "batteryLevel" has UnitPercentage but device_class should be BATTERY not generic %.
# "currentPower" with UnitWatt on a battery should stay POWER.
STATE_CLASS_OVERRIDE: dict[str, str | None] = {
    # Energy totals (cumulative) – must be TOTAL_INCREASING for Energy Dashboard
    "totalEnergyProduced":   SensorStateClass.TOTAL_INCREASING,
    "totalEnergyConsumed":   SensorStateClass.TOTAL_INCREASING,
    "feedBatteryTotal":      SensorStateClass.TOTAL,
    "feedBatteryMonth":      SensorStateClass.TOTAL,
    "feedBatteryToday":      SensorStateClass.TOTAL,
    "capacity":              SensorStateClass.MEASUREMENT,
}

DEVICE_CLASS_OVERRIDE: dict[str, str | None] = {
    "batteryLevel":  SensorDeviceClass.BATTERY,
    "setMaxSoC":     SensorDeviceClass.BATTERY,
    "currentSlot":   SensorDeviceClass.TIMESTAMP,
    "validUntil":    SensorDeviceClass.TIMESTAMP,
    "validSince":    SensorDeviceClass.TIMESTAMP,
    # Price sensors
    "currentTotalCost":   SensorDeviceClass.MONETARY,
    "currentEnergyCost":  SensorDeviceClass.MONETARY,
    "currentLeviesCost":  SensorDeviceClass.MONETARY,
    "currentGridFeeCost": SensorDeviceClass.MONETARY,
    "averageTotalCost":   SensorDeviceClass.MONETARY,
    "lowestPrice":        SensorDeviceClass.MONETARY,
    "highestPrice":       SensorDeviceClass.MONETARY,
}


def get_sensor_meta(
    state_name: str, nymea_unit: str
) -> tuple[str | None, str | None, str | None]:
    """
    Return (ha_unit, device_class, state_class) for a given
    Nymea state name and unit string.
    """
    ha_unit, device_class, state_class = UNIT_MAP.get(nymea_unit, (None, None, None))

    # Apply overrides
    if state_name in DEVICE_CLASS_OVERRIDE:
        device_class = DEVICE_CLASS_OVERRIDE[state_name]
    if state_name in STATE_CLASS_OVERRIDE:
        state_class = STATE_CLASS_OVERRIDE[state_name]

    return ha_unit, device_class, state_class
