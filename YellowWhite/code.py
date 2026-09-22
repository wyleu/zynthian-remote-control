# code.py - Enhanced launcher with flat settings.toml, helper dict, critical checks, and save support

import sys
import os
import time

#DEFAULT_PROGRAM = "pico_circuitp_LED_smooth_asyncio_01.py"  # ← e.g. "fallback.py" if desired
DEFAULT_PROGRAM = "pico_circuitp_asyncio_osc_cuia_led_startup.py"
# ────────────────────────────────────────────────
# Critical keys that MUST be present for normal operation
CRITICAL_KEYS = [
    "WIFI_SSID",
    "WIFI_PASSWORD",        # Most common blocker on Pico W projects
    # Add others if needed, e.g. "API_KEY", "MQTT_BROKER"
]

# ────────────────────────────────────────────────
def load_settings():
    """
    Load all known settings into a dict with proper type conversion.
    Returns a dict you can pass around or use like settings['output_midi_channel']
    """
    settings = {}

    # WiFi
    settings['wifi_ssid'] = os.getenv("WIFI_SSID", "NOWRH81L")
    settings['wifi_password'] = os.getenv("WIFI_PASSWORD")  # No default → None if missing

    # Output / MIDI
    settings['output_midi_channel'] = int(os.getenv("OUTPUT_MIDI_CHANNEL", "0"))
    raw_formats = os.getenv("OUTPUT_ENABLED_FORMATS", "log")
    settings['output_enabled_formats'] = [
        fmt.strip() for fmt in raw_formats.split(",") if fmt.strip()
    ]
    raw_test = os.getenv("OUTPUT_TEST_ENABLED", "false").lower()
    settings['output_test_enabled'] = raw_test in ("true", "1", "yes", "on")
    settings['test_programme_1'] = os.getenv("TEST_PROGRAMME_1", "false").lower()

    # Startup
    settings['startup_program'] = os.getenv("STARTUP_PROGRAM", DEFAULT_PROGRAM)

    # Optional / future examples
    # settings['logging_level']     = os.getenv("LOGGING_LEVEL", "INFO").upper()
    # settings['display_brightness'] = float(os.getenv("DISPLAY_BRIGHTNESS", "0.8"))

    return settings

# ────────────────────────────────────────────────
def check_critical_settings():
    """Warn about missing critical keys — returns True if all present"""
    missing = []
    for key in CRITICAL_KEYS:
        if os.getenv(key) is None:
            missing.append(key)
    
    if missing:
        print("!" * 60)
        print("WARNING: Missing critical settings in settings.toml:")
        for m in missing:
            print(f"  - {m}")
        print("Some features (e.g. WiFi) may not work until these are set.")
        print("!" * 60)
        return False
    
    return True

# ────────────────────────────────────────────────

# Main execution
settings = load_settings()

# Print summary
print("Loaded settings:")
for k, v in sorted(settings.items()):
    print(f"  {k: <22}: {v}")
print("-" * 50)

# Check critical ones
check_critical_settings()

# ────────────────────────────────────────────────
def get_start_program():
    prog = settings.get('startup_program')
    if not prog:
        print("No STARTUP_PROGRAM defined")
        return None
    if prog not in os.listdir():
        print(f"Startup program not found: '{prog}'")
        print("Available files:", os.listdir())
        return None
    if not prog.endswith(".py"):
        print(f"Warning: '{prog}' does not end with .py")
    return prog

# ────────────────────────────────────────────────
start_file = get_start_program()

if start_file:
    print(f"Launching: {start_file}")
    time.sleep(0.8)

    try:
        with open(start_file, "r") as f:
            code = f.read()
        exec(code, globals(), locals())
        print(f"→ {start_file} completed (or running in background)")
    except SyntaxError as e:
        print(f"Syntax error in {start_file}:\n{e}")
    except Exception as e:
        print(f"Error running {start_file}:")
        sys.print_exception(e)

else:
    print("\nNo auto-start program.")
    print("REPL ready. Example:")
    print("  exec(open('your_program.py').read())")
    while True:
        time.sleep(10)

# ────────────────────────────────────────────────
# Example usage from other programs:
#   from code import settings, save_settings_changes
#   settings['output_test_enabled'] = True
#   save_settings_changes({"OUTPUT_TEST_ENABLED": True})
