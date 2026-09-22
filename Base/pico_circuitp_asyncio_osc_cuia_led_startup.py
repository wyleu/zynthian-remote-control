import time
import os
import wifi
import socketpool
import microosc
import asyncio
import rotaryio
import digitalio
import board
import pwmio
import supervisor
# Optional MIDI
try:
    import usb_midi
    import adafruit_midi
    from adafruit_midi.control_change import ControlChange
    from adafruit_midi.note_on import NoteOn
    from adafruit_midi.note_off import NoteOff
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
if MIDI_AVAILABLE:
    print('MIDI AVAILABLE!!')
else:
    print('++++++++++   NO MIDI AVAILABLE!!    +++++++++')
VERSION = 2.011


# ====================== HELPERS ======================
def get_float(key, default):
    val = os.getenv(key)
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def get_int(key, default):
    val = os.getenv(key)
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def get_color(key, default=(65535, 65535, 65535)):
    val = os.getenv(key)
    if not val:
        return default
    try:
        parts = [int(x.strip()) for x in val.split(",")]
        return tuple(parts[:3])
    except:
        return default

def get_color_list(key, default_list):
    val = os.getenv(key)
    if not val:
        return default_list
    try:
        colors = []
        for item in val.split(";"):
            parts = [int(x.strip()) for x in item.split(",")]
            colors.append(tuple(parts[:3]))
        return colors
    except:
        return default_list

# ====================== CONFIG FROM settings.toml ======================
UDP_HOST = os.getenv("OSC_HOST", "zynthian-cajon7.local")
UDP_PORT = int(os.getenv("OSC_PORT", "1370"))

ssid = os.getenv("WIFI_SSID")
password = os.getenv("WIFI_PASSWORD")

MACHINE = os.getenv("MACHINE", "WHITE")
MIDI_CHANNEL = get_int("OUTPUT_MIDI_CHANNEL", 1)

# Output formats
enabled_formats_raw = os.getenv("OUTPUT_ENABLED_FORMATS", "log, midi, osc")
OUTPUT_FORMATS = {fmt.strip().lower() for fmt in enabled_formats_raw.split(",") if fmt.strip()}

# Brightness & Timing
FLASH_BRIGHTNESS = get_int("FLASH_BRIGHTNESS", 100)
READY_PULSE_BRIGHTNESS = get_float("READY_PULSE_BRIGHTNESS", 0.015)
STARTUP_BRIGHTNESS = get_float("STARTUP_BRIGHTNESS", 0.01)

SHORT_THRESHOLD = get_float("BUTTON_SHORT_THRESHOLD_SEC", 0.30)
BOLD_THRESHOLD = get_float("BUTTON_BOLD_THRESHOLD_SEC", 1.00)
LONG_THRESHOLD = get_float("BUTTON_LONG_THRESHOLD_SEC", 2.00)
FLASH_DURATION = get_float("LED_FLASH_DURATION_SEC", 0.40)
ROT_FLASH_DURATION = get_float("LED_ROT_FLASH_DURATION_SEC", 0.12)
POLL_INTERVAL = get_float("POLL_INTERVAL_SEC", 0.008)

print(f"Enabled outputs: {OUTPUT_FORMATS}")

# ====================== RGB LED SETUP ======================
RED = pwmio.PWMOut(getattr(board, os.getenv("LED_RED_PIN", "GP9")), frequency=1000, duty_cycle=0)
GREEN = pwmio.PWMOut(getattr(board, os.getenv("LED_GREEN_PIN", "GP10")), frequency=1000, duty_cycle=0)
BLUE = pwmio.PWMOut(getattr(board, os.getenv("LED_BLUE_PIN", "GP11")), frequency=1000, duty_cycle=0)

def set_rgb(r, g, b):
    RED.duty_cycle = min(65535, max(0, int(round(r))))
    GREEN.duty_cycle = min(65535, max(0, int(round(g))))
    BLUE.duty_cycle = min(65535, max(0, int(round(b))))

# ====================== LED COLORS ======================
ENCODER_FLASH_COLORS = [
    get_color("ENCODER_0_FLASH_COLOR", (65535, 0, 0)),
    get_color("ENCODER_1_FLASH_COLOR", (0, 40000, 0)),
    get_color("ENCODER_2_FLASH_COLOR", (0, 0, 65535)),
    get_color("ENCODER_3_FLASH_COLOR", (65535, 0, 65535))
]

STARTUP_COLORS = get_color_list("STARTUP_COLORS", [
    (65535, 0, 0), (0, 65535, 0), (0, 0, 65535),
    (65535, 65535, 0), (65535, 0, 65535)
])

READY_PULSE_COLOR = get_color("READY_PULSE_COLOR", (65535, 65535, 65535))

LISTEN_OSC_PORT = int(os.getenv("LISTEN_OSC_PORT", "1371"))
BEAT_COLOR = get_color("BEAT_LED_COLOR", (65535, 0, 0))
BEAT_DURATION = get_float("BEAT_FLASH_DURATION_SEC", 0.08)

# ====================== OSC SERVER (for feedback) ======================
osc_server = None

def on_any_osc_message(msg):
    """Catch-all handler"""
    print(f"📥 OSC RECEIVED: {msg.addr} | args={msg.args}")

def on_osc_beat(msg):
    """Dedicated beat handler"""
    print(f"🎵 BEAT PULSE received: {msg.addr} | args={msg.args}")
    asyncio.create_task(beat_pulse())

async def beat_pulse():
    """Strong visual feedback"""
    print("   → Flashing RGB beat pulse")
    r, g, b = BEAT_COLOR
    set_rgb(r * 1.0, g * 0.3, b * 0.3)   # Bright red flash
    await asyncio.sleep(BEAT_DURATION)
    set_rgb(0, 0, 0)

def setup_osc_server():
    global osc_server
    try:
        pool = socketpool.SocketPool(wifi.radio)
        
        dispatch_map = {
            "/": on_any_osc_message,                    # Catch everything
            "/beat": on_osc_beat,
            "/CUIA/BEAT": on_osc_beat,
            "/transport/beat": on_osc_beat,
            "/transport/clock": on_osc_beat,
        }
        
        osc_server = microosc.OSCServer(pool, "", LISTEN_OSC_PORT, dispatch_map)
        
        print(f"✅ OSC Server ACTIVE on port {LISTEN_OSC_PORT}")
        return True
    except Exception as e:
        print(f"❌ OSC Server failed: {e}")
        return False
    
# ====================== MIDI SETUP ======================
midi_out = None
if MIDI_AVAILABLE and "midi" in OUTPUT_FORMATS:
    try:
        # IMPORTANT: Use ports[1] for OUTPUT on CircuitPython
        midi_out = adafruit_midi.MIDI(
            midi_out=usb_midi.ports[1], 
            out_channel=MIDI_CHANNEL - 1
        )
        print(f"✅ MIDI Output enabled on channel {MIDI_CHANNEL} (USB)")
    except Exception as e:
        print(f"⚠️ MIDI setup failed: {e}")
        midi_out = None
else:
    print("MIDI output disabled (not in OUTPUT_ENABLED_FORMATS or library missing)")
    


# ====================== ANNOUNCEMENT SYSTEM ======================
def get_my_ip():
    """Safe IP getter"""
    try:
        return str(wifi.radio.ipv4_address)
    except:
        return "0.0.0.0"
    
# ====================== UNIFIED DEVICE ANNOUNCEMENT ======================
def send_device_announcement():
    """Clean unified announcement"""
    my_ip = str(wifi.radio.ipv4_address) if hasattr(wifi.radio, 'ipv4_address') else "0.0.0.0"
    print(f"📢 Announcing Zynremote {MACHINE} @ {my_ip}")

    # 1. Universal Device Inquiry Response
    if midi_out:
        try:
            response = bytearray([
                0xF0, 0x7E, 0x00, 0x06, 0x02,   # UDI Reply
                0x7D,                           # Manufacturer (Local)
                0x00, 0x01,                     # Family
                0x00, 0x01,                     # Member
                0x02, 0x00, int(VERSION * 10) % 128,  # Version byte (fixed)
            ])
            
            for char in f"Zynremote {MACHINE}":
                response.append(ord(char))
            
            response.extend(b" IP:" + my_ip.encode())
            response.append(0xF7)

            usb_midi.ports[1].write(response)
            print("✅ Universal Device Inquiry sent")
        except Exception as e:
            print(f"MIDI UDI failed: {e}")

    # 2. OSC Announcement (most important for bidirectional)
    if "osc" in OUTPUT_FORMATS and 'osc_client' in globals():
        try:
            msg = microosc.OscMsg("/CUIA/ZYNREMOTE/ANNOUNCE", 
                                [MACHINE, VERSION, my_ip, LISTEN_OSC_PORT], 
                                ("s", "f", "s", "i"))
            osc_client.send(msg)
            print(f"✅ OSC Announcement sent → {my_ip}:{LISTEN_OSC_PORT}")
        except Exception as e:
            print(f"OSC announcement failed: {e}")

# ====================== STARTUP + READY PULSE ======================
async def ready_pulse_task():
    brightness = READY_PULSE_BRIGHTNESS
    r, g, b = READY_PULSE_COLOR
    while True:
        set_rgb(r * brightness, g * brightness, b * brightness)
        await asyncio.sleep(0.01)
        set_rgb(0, 0, 0)
        await asyncio.sleep(0.99)

def initial_startup_sequence():
    print("Initial startup done → Ready pulse + feedback active.")
    
    print("Running initial LED startup sequence...")
    brightness = STARTUP_BRIGHTNESS
    r, g, b = READY_PULSE_COLOR
    set_rgb(r * brightness, g * brightness, b * brightness)
    time.sleep(0.25)
    set_rgb(0, 0, 0)
    time.sleep(0.12)

    for r, g, b in STARTUP_COLORS:
        set_rgb(r * brightness, g * brightness, b * brightness)
        time.sleep(0.16)
        set_rgb(0, 0, 0)
        time.sleep(0.08)
        
    # Send announcement AFTER WiFi + OSC client is ready
    send_device_announcement()

    print("Initial startup done → Ready pulse active.")

# ====================== OUTPUT HELPERS ======================
async def flash_led_for_encoder(enc_idx: int, duration=None, brightness=None):
    if not (0 <= enc_idx <= 3):
        return
    if duration is None:
        duration = FLASH_DURATION
    if brightness is None:
        brightness = FLASH_BRIGHTNESS / 100.0
    else:
        brightness = brightness / 100.0

    r, g, b = ENCODER_FLASH_COLORS[enc_idx]
    set_rgb(r * brightness, g * brightness, b * brightness)
    await asyncio.sleep(duration)
    set_rgb(0, 0, 0)
    
# ====================== MAIN LOOP UPDATES ======================
async def feedback_listener():
    """Poll OSC server"""
    while True:
        if osc_server:
            try:
                osc_server.poll()
            except:
                pass
        await asyncio.sleep(0.01)

def send_midi_cc(controller: int, value: int):
    """Send MIDI Control Change"""
    if midi_out:
        try:
            midi_out.send(ControlChange(controller, max(0, min(127, value))))
            print(f"MIDI CC {controller} = {value}")  # temporary debug
        except Exception as e:
            print(f"MIDI CC send failed: {e}")

def send_midi_note(note: int, velocity: int = 100, on=True):
    """Send Note On/Off"""
    if midi_out:
        try:
            if on:
                midi_out.send(NoteOn(note, velocity))
            else:
                midi_out.send(NoteOff(note, 0))
            print(f"MIDI Note {note} {'ON' if on else 'OFF'}")  # temporary debug
        except Exception as e:
            print(f"MIDI Note send failed: {e}")

# ====================== BUTTON & ENCODER CLASSES ======================
class ButtonBase:
    def __init__(self, idx, name, pin_name):
        self.idx = idx
        self.name = name
        sw_pin = getattr(board, pin_name)
        self.switch = digitalio.DigitalInOut(sw_pin)
        self.switch.switch_to_input(pull=digitalio.Pull.UP)
        self.press_start = None
        self.long_sent = False
        self.last_value = self.switch.value

    def _send_action(self, action_type: str):
        # OSC
        if "osc" in OUTPUT_FORMATS:
            try:
                msg = microosc.OscMsg("/CUIA/ZYNSWITCH", [self.idx, action_type], ("i", "s"))
                osc_client.send(msg)
                print(f"ZYNSWITCH {self.name} ({self.idx}): {action_type}")
            except Exception as e:
                print(f"OSC send failed: {e}")

        # MIDI (simple mapping)
        if "midi" in OUTPUT_FORMATS and midi_out:
            note = 60 + self.idx * 2   # Example mapping: S0=60, S1=62, etc.
            if action_type in ("S", "P"):
                send_midi_note(note, 100, True)
            elif action_type == "L":
                send_midi_note(note, 0, False)

        # Visual feedback
        if 0 <= self.idx <= 3:
            asyncio.create_task(flash_led_for_encoder(self.idx))

    def check_button(self, now: float):
        pressed = not self.switch.value
        if pressed != self.last_value:
            self.last_value = pressed

        if pressed:
            if self.press_start is None:
                self.press_start = now
                self.long_sent = False
                self._send_action("P")
            elif not self.long_sent and (now - self.press_start) >= LONG_THRESHOLD:
                self._send_action("L")
                self.long_sent = True
        else:
            if self.press_start is not None:
                duration = now - self.press_start
                if duration < SHORT_THRESHOLD:
                    self._send_action("S")
                elif duration < LONG_THRESHOLD:
                    self._send_action("B")
                else:
                    self._send_action("L")
                self.press_start = None
                self.long_sent = False

class Encoder(ButtonBase):
    def __init__(self, idx, name, switch_pin, a_pin_name, b_pin_name):
        super().__init__(idx, name, switch_pin)
        a = getattr(board, a_pin_name)
        b = getattr(board, b_pin_name)
        self.encoder = rotaryio.IncrementalEncoder(a, b)
        self.last_pos = self.encoder.position
        self.cc_number = 20 + idx   # Example: Encoder 0 = CC20, etc.

    async def monitor(self):
        while True:
            now = time.monotonic()
            pos = self.encoder.position
            if pos != self.last_pos:
                delta = pos - self.last_pos
                # OSC
                if "osc" in OUTPUT_FORMATS:
                    try:
                        msg = microosc.OscMsg("/CUIA/ZYNPOT", [self.idx, delta], ("i", "i"))
                        osc_client.send(msg)
                        print(f"ZYNPOT {self.name} ({self.idx}): {delta:+d}")
                    except Exception as e:
                        print(f"OSC send failed: {e}")

                # MIDI
                if "midi" in OUTPUT_FORMATS and midi_out:
                    # Simple relative CC (you can improve this later)
                    send_midi_cc(self.cc_number, (delta * 4) % 128)

                asyncio.create_task(flash_led_for_encoder(self.idx, ROT_FLASH_DURATION))
                self.last_pos = pos

            self.check_button(now)
            await asyncio.sleep(POLL_INTERVAL)

class SimpleSwitch(ButtonBase):
    async def monitor(self):
        while True:
            now = time.monotonic()
            self.check_button(now)
            await asyncio.sleep(POLL_INTERVAL)


# ====================== MAIN START ======================
print(f"Starting Zynremote Controller v{VERSION} - {MACHINE}")

print("Connecting to WiFi:", ssid)
wifi.radio.connect(ssid, password)
print("IP:", wifi.radio.ipv4_address)

socket_pool = socketpool.SocketPool(wifi.radio)
osc_client = microosc.OSCClient(socket_pool, UDP_HOST, UDP_PORT)

print("OSC ready →", UDP_HOST, UDP_PORT)

# OSC Server (incoming feedback)
setup_osc_server()

# Build hardware objects...
encoders = []
for i in range(4):
    prefix = f"ENCODER_{i}_"
    name = os.getenv(prefix + "NAME")
    sw = os.getenv(prefix + "SWITCH")
    a = os.getenv(prefix + "A")
    b = os.getenv(prefix + "B")
    if all([name, sw, a, b]):
        encoders.append(Encoder(i, name, sw, a, b))

simple_switches = []
for i in range(4, 8):
    prefix = f"SWITCH_{i}_"
    name = os.getenv(prefix + "NAME")
    pin = os.getenv(prefix + "PIN")
    if all([name, pin]):
        simple_switches.append(SimpleSwitch(i, name, pin))

initial_startup_sequence()

# # Web Server (optional)
# try:
#     from web_config import WebConfig
#     web = WebConfig(settings=load_settings_from_code_if_you_have_it(), 
#                    save_callback=save_settings_changes)
#     web.start()
#     tasks.append(asyncio.create_task(web.poll()))
# except ImportError:
#     print("Web interface not available (web_config.py missing)")

print("Starting main loop...")
try:
    async def main():
        tasks = [asyncio.create_task(enc.monitor()) for enc in encoders]
        tasks += [asyncio.create_task(sw.monitor()) for sw in simple_switches]
        tasks.append(asyncio.create_task(ready_pulse_task()))
        tasks.append(asyncio.create_task(feedback_listener()))
        await asyncio.gather(*tasks)

    asyncio.run(main())
except Exception as e:
    print("Error:", e)
finally:
    set_rgb(0, 0, 0)
    print("Shutdown complete")