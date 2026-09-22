# code.py - Enhanced launcher for CircuitPython (Pico W)

import sys
import os
import time

DEFAULT_PROGRAM = "pico_circuitp_asyncio_osc_cuia_led_startup.py"

# Critical keys
CRITICAL_KEYS = [
    "WIFI_SSID",
    "WIFI_PASSWORD",
    "OSC_HOST",
    "OSC_PORT",
]

# ====================== SETTINGS LOADER ======================
def load_settings():
    """Load all settings with proper type conversion"""
    settings = {}

    # Core Network
    settings['wifi_ssid'] = os.getenv("WIFI_SSID", "NOWRH81L")
    settings['wifi_password'] = os.getenv("WIFI_PASSWORD")
    settings['osc_host'] = os.getenv("OSC_HOST", "zynthian-cajon7.local")
    settings['osc_port'] = int(os.getenv("OSC_PORT", "1370"))

    # Output & Startup
    settings['output_midi_channel'] = int(os.getenv("OUTPUT_MIDI_CHANNEL", "1"))
    raw_formats = os.getenv("OUTPUT_ENABLED_FORMATS", "log, midi, osc")
    settings['output_enabled_formats'] = [fmt.strip() for fmt in raw_formats.split(",") if fmt.strip()]
    settings['output_test_enabled'] = os.getenv("OUTPUT_TEST_ENABLED", "false").lower() in ("true", "1", "yes")
    settings['startup_program'] = os.getenv("STARTUP_PROGRAM", DEFAULT_PROGRAM)
    settings['machine'] = os.getenv("MACHINE", "UNKNOWN")

    # Brightness
    settings['display_brightness'] = float(os.getenv("DISPLAY_BRIGHTNESS", "45"))
    settings['flash_brightness'] = int(os.getenv("FLASH_BRIGHTNESS", "100"))
    settings['ready_pulse_brightness'] = float(os.getenv("READY_PULSE_BRIGHTNESS", "0.015"))
    settings['startup_brightness'] = float(os.getenv("STARTUP_BRIGHTNESS", "0.01"))

    # LED Colors
    def parse_color(key, default=(65535, 65535, 65535)):
        val = os.getenv(key)
        if not val:
            return default
        try:
            return tuple(int(x.strip()) for x in val.split(",")[:3])
        except:
            return default

    settings['encoder_flash_colors'] = [
        parse_color(f"ENCODER_{i}_FLASH_COLOR") for i in range(4)
    ]
    settings['ready_pulse_color'] = parse_color("READY_PULSE_COLOR")

    return settings


# ====================== PRINT SUMMARY ======================
def print_settings_summary(settings):
    print(f"\n=== {settings.get('machine', 'CONTROLLER')} CONTROLLER ===")
    
    print("\n📡 Network:")
    print(f"  WiFi SSID     : {settings['wifi_ssid']}")
    print(f"  OSC Target    : {settings['osc_host']}:{settings['osc_port']}")

    print("\n🎨 LED Settings:")
    print(f"  Flash Brightness     : {settings['flash_brightness']}%")
    print(f"  Ready Pulse Bright   : {settings['ready_pulse_brightness']}")
    print(f"  Startup Brightness   : {settings['startup_brightness']}")
    
    print("  Encoder Flash Colors:")
    for i, color in enumerate(settings['encoder_flash_colors']):
        print(f"    Encoder {i}: {color}")

    print(f"  Ready Pulse Color    : {settings['ready_pulse_color']}")
    print("-" * 60)


# ====================== SAVE SUPPORT ======================
def save_settings_changes(updates: dict):
    """Save changes back to settings.toml (CircuitPython compatible)"""
    try:
        with open("settings.toml", "r") as f:
            lines = f.readlines()
        
        new_lines = []
        updated = set()
        
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue
            
            for key, value in updates.items():
                if stripped.startswith(key + " =") or stripped.startswith(key + "="):
                    if isinstance(value, bool):
                        value_str = str(value).lower()
                    elif isinstance(value, (list, tuple)):
                        value_str = ",".join(str(x) for x in value)
                    else:
                        value_str = str(value)
                    new_lines.append(f'{key} = "{value_str}"\n')
                    updated.add(key)
                    break
            else:
                new_lines.append(line)
        
        with open("settings.toml", "w") as f:
            f.writelines(new_lines)
        
        print(f"✅ Saved {len(updated)} setting(s) to settings.toml")
        return True
    except Exception as e:
        print(f"❌ Failed to save settings: {e}")
        return False


# ====================== MAIN ======================
print("Loading settings.toml...")
settings = load_settings()
print_settings_summary(settings)

# Critical check
missing = [k for k in CRITICAL_KEYS if os.getenv(k) is None]
if missing:
    print("⚠️  WARNING: Missing critical settings:", missing)

# Launch startup program
start_file = settings.get('startup_program')

print(f"\nChecking for startup program: {start_file}")

# CircuitPython-friendly file check
try:
    with open(start_file, "r") as f:
        print(f"✅ Found {start_file}")
        code = f.read()
except OSError:
    print(f"❌ Startup program '{start_file}' not found!")
    print("Available files:", os.listdir())
    start_file = None

if start_file:
    print(f"🚀 Launching: {start_file}")
    time.sleep(0.8)
    
    try:
        exec(code, globals(), locals())
    except Exception as e:
        print(f"Error running {start_file}:")
        sys.print_exception(e)
else:
    print("\nNo auto-start program found. Dropping to REPL.")

print("\nController launcher finished.")