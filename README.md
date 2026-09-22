# Zynthian remote control

CircuitPython remotes for a Zynthian (OSC / CUIA + LED).

Two physical controllers share the same program and differ by settings
(and LED colours):

| Folder | Device |
|---|---|
| `Base/` | Shared / latest `code.py`, startup program, `web_config.py`, ctrldev helper, fullest `lib/` |
| `BlueGreen/` | Blue–green unit |
| `YellowWhite/` | Yellow–white unit |

Master copy: `~/Code/Zynthian-remote-control` on the Pi. CIRCUITPY is a stamp.

CircuitPython runs `code.py`, which starts
`pico_circuitp_asyncio_osc_cuia_led_startup.py`.

Wi-Fi and colours live in local `settings.toml` (not in git). Copy
`settings.example.toml` → `settings.toml` and fill SSID/password on the Pi.

Deploy: copy that colour’s `code.py`, startup `.py`, `lib/`, and local
`settings.toml` onto a **writable** CIRCUITPY. Do not Save from Thonny
onto the volume. Run = unplug / plug in.
