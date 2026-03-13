def calculate_energy_metrics(things_states: dict) -> dict:
    """
    Derive energy flow metrics from per-device state values.

    things_states: { "device_name": { "state_name": value, ... }, ... }

    Device name matching is case-insensitive substring:
      - PV inverters: "bph wr1", "bph wr2"  → currentPower (negative = producing)
      - Grid meter:   "hy-switch"            → currentPower (positive = import)
      - Battery:      "byd hvs"              → currentPower (negative = discharging)
    """

    def get(device_substr, state_name):
        for dev, states in things_states.items():
            if device_substr.lower() in dev.lower():
                val = states.get(state_name, 0)
                return float(val) if val is not None else 0.0
        return 0.0

    # PV: negative currentPower means producing → negate to get positive production
    pv_wr1 = -get("bph wr1", "currentPower")
    pv_wr2 = -get("bph wr2", "currentPower")
    pv_total = pv_wr1 + pv_wr2

    # Grid: positive = import from grid, negative = export to grid
    grid = get("hy-switch", "currentPower")
    grid_import = max(grid, 0)
    grid_export = max(-grid, 0)

    # Battery: negative = discharging, positive = charging
    battery = get("byd hvs", "currentPower")

    # House consumption = PV production + grid import - grid export - battery charging + battery discharging
    house = pv_total + grid_import - grid_export - max(battery, 0) + max(-battery, 0)

    return {
        "pv_power":          round(pv_total, 2),
        "grid_import":       round(grid_import, 2),
        "grid_export":       round(grid_export, 2),
        "battery_power":     round(-battery, 2),
        "house_consumption": round(max(house, 0), 2),
    }
