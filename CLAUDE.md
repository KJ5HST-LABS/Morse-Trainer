# CLAUDE.md

## SESSION PROTOCOL -- FOLLOW BEFORE DOING ANYTHING

**Read and follow `SESSION_RUNNER.md` step by step.** It is your operating procedure for every session. It tells you what to read, when to stop, and how to close out.

**Three rules you will be tempted to violate:**
1. **Orient first** -- Read SAFEGUARDS.md -> SESSION_NOTES.md -> git status -> report findings -> WAIT FOR THE USER TO SPEAK
2. **1 and done** -- One deliverable per session. When it's complete, close out. Do not start the next thing.
3. **Auto-close** -- When done: evaluate previous handoff, self-assess, document learnings, write handoff notes, commit, report, STOP.

## Project Overview

**Morse-Trainer** is an adaptive Morse code trainer for the ESP8266 (NodeMCU). It sends random characters as audible Morse code, accepts typed responses via serial/web/morse key, and dynamically adjusts character probabilities and speed based on accuracy.

Ported from [SensorsIot/Morse-Trainer](https://github.com/SensorsIot/Morse-Trainer) (Arduino) to ESP8266 with web UI, serial interface, OLED display, and morse key input.

- **Remote:** KJ5HST-LABS/Morse-Trainer
- **Author:** Terrell Deppe (KJ5HST)
- **License:** Original GPLv3 (from SensorsIot), port extensions by Terrell

## Architecture

### Event-Driven Design

The system uses a unified event callback pattern. The `Trainer` class emits `TrainerEvent` structs, and `main.cpp` broadcasts them to all output interfaces:

```
Trainer.update() -> onTrainerEvent() -> SerialInterface
                                     -> WebServer (WebSocket)
                                     -> OledDisplay
```

### Modules

```
src/
  main.cpp             -- Setup/loop, event routing to all interfaces
  trainer.cpp          -- Core training logic: adaptive probabilities, speed adjustment, queue management
  morse_engine.cpp     -- Morse code transmission: timing via Ticker, character-to-pattern lookup
  morse_table.cpp      -- Morse code lookup table (ASCII 33-90)
  buzzer.cpp           -- Tone output: active (DC) and passive (PWM) buzzer support
  morse_key.cpp        -- Physical key input: straight key and iambic paddle, debouncing
  serial_interface.cpp -- Serial CLI: /start, /stop, /speed, /profile, /help commands
  web_server.cpp       -- WiFi AP + ESPAsyncWebServer + WebSocket for browser UI
  oled_display.cpp     -- SSD1306/SH1106 OLED: character display, keying indicator, stats
  storage.cpp          -- LittleFS persistence: probability arrays, config (speed, profile, buzzer type)
  profiles.cpp         -- 10 preset training profiles (letters, numbers, punctuation, etc.)

include/
  config.h             -- Pin maps (NodeMCU vs OLED module), training constants, WiFi credentials
  trainer.h            -- TrainerEvent struct, Trainer class
  morse_engine.h       -- MorseEngine namespace
  buzzer.h             -- Buzzer namespace
  morse_key.h          -- MorseKey namespace
  serial_interface.h   -- SerialInterface namespace
  web_server.h         -- WebServer namespace
  oled_display.h       -- OledDisplay namespace
  storage.h            -- Storage namespace (LittleFS)
  profiles.h           -- Profile presets
  morse_table.h        -- Morse lookup

data/                  -- LittleFS filesystem image (uploaded to ESP8266 flash)
  index.html           -- Web UI
  app.js               -- Web UI JavaScript
  style.css            -- Web UI styles

bin/                   -- Pre-built firmware binaries
  firmware.bin         -- Application binary
  littlefs.bin         -- Filesystem image

MorseTrainer/          -- Arduino IDE version (synced from src/ via sync_arduino.py)
  MorseTrainer.ino     -- Arduino sketch (combined from all src/ files)

tools/
  MorseClient/         -- Java desktop client (Gradle)
  flash_firmware.bat   -- Windows flash script

docs/
  ORIGINAL_ANALYSIS.md -- Analysis of the original SensorsIot codebase
```

### Supported Boards

| Board | PlatformIO env | Build flag |
|-------|---------------|------------|
| NodeMCU v2 (ESP-12E) | `nodemcuv2` (default) | None |
| ESP8266 0.96" OLED module v2.1.0 | `esp8266_oled` | `-DBOARD_ESP8266_OLED` |

## Tech Stack

- **Language:** C++ (Arduino framework)
- **Platform:** ESP8266 (espressif8266)
- **Build:** PlatformIO (primary), Arduino IDE (via sync script)
- **Libraries:** ESPAsyncWebServer, ESPAsyncTCP, ArduinoJson 7, U8g2 (OLED)
- **Filesystem:** LittleFS (on-device config + web UI assets)
- **Connectivity:** WiFi AP mode, mDNS (morse.local), WebSocket

## Build Commands

```bash
# PlatformIO
pio run                          # Build default env (nodemcuv2)
pio run -e esp8266_oled          # Build for OLED module
pio run -t upload                # Flash firmware
pio run -t uploadfs              # Upload LittleFS filesystem
pio device monitor               # Serial monitor (115200 baud)

# Arduino IDE sync
python3 sync_arduino.py          # Sync src/ -> MorseTrainer/MorseTrainer.ino
```

## Backlog & Issues

Use **GitHub Issues** for backlog items, bugs, and cross-project coordination. Do not use BACKLOG.md — it has been migrated to GitHub Issues.

- View issues: `gh issue list`
- Create issue: `gh issue create --title "..." --body "..."`
- Cross-project issues: use the target repo's issue tracker

## Conventions

- All hardware modules use namespace pattern (e.g., `MorseEngine::begin()`, `Buzzer::setActive()`)
- Trainer is a class instance (`extern Trainer trainer`) — the only stateful object
- Events use value-type struct (`TrainerEvent`) with type enum discriminator
- Pin configuration centralized in `config.h` with board-specific `#ifdef` blocks
- Training constants (queue length, speed bounds, probability adjustments) in `config.h`
- WiFi defaults: AP SSID "MorseTrainer", password "morsecode", mDNS "morse"
