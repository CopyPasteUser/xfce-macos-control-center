# XFCE macOS Control Center

> A fast, macOS-inspired control center for XFCE/X11—with practical Linux controls instead of a visual clone.

![Platform](https://img.shields.io/badge/platform-XFCE%20%2F%20X11-2284F2)
![Python](https://img.shields.io/badge/Python-GTK3-3776AB?logo=python&logoColor=white)
![Vibe coded](https://img.shields.io/badge/development-vibe--coded-8A2BE2)

> **Vibe-coded project:** the product direction, UX decisions, testing, and hardware-specific validation are mine; AI-assisted development was used to implement and refine parts of the project.

## Project status

This repository currently contains the project documentation. The existing application source and release package still need to be uploaded before the installation commands below can be used unchanged.

## Goals

- Open almost instantly from an XFCE panel or keyboard shortcut
- Keep common controls in one compact, dark interface
- Work well on laptops while remaining adaptable to other XFCE devices
- Degrade gracefully when optional hardware features are unavailable
- Avoid silently changing the user's desktop theme, panel, wallpaper, or dock

## Feature overview

- Wi-Fi, Bluetooth, VPN, airplane-mode-style and connectivity controls
- Audio output, volume, microphone, brightness and media controls
- Quick actions for screenshots, file sharing, power and session tasks
- Three-state keyboard backlight control when supported
- Battery, CPU, memory, temperature and storage information
- Storage analyzer with useful cleanup guidance
- Fan information and controls on supported hardware
- Multiple quick notes with persistent storage
- Configurable themes, animations, language and control-center behavior
- Clear fallbacks for unavailable commands or unsupported hardware

## Target environment

- Linux Mint or another modern Linux distribution
- XFCE on X11
- Python 3
- GTK 3 and PyGObject

Typical Debian/Ubuntu dependencies:

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0
```

Optional integrations may use tools such as `nmcli`, `bluetoothctl`, `pactl`, `playerctl`, `brightnessctl`, `upower`, `sensors`, `systemctl`, and `xfconf-query`.

## Development launch

After the application source is uploaded:

```bash
git clone https://github.com/CopyPasteUser/xfce-macos-control-center.git
cd xfce-macos-control-center
python3 main.py
```

The final repository layout and launcher command will be documented alongside the uploaded source. Do not run installation commands from third-party forks without reviewing them first.

## Design principles

- Dark charcoal surfaces with white accents
- Opaque window rendering for reliable GTK/X11 behavior
- Compact, discoverable controls instead of hidden gestures
- System changes only after an explicit user action
- No assumption that every XFCE machine has the same hardware

## Security

Some controls can invoke privileged system tools. The application should never store sudo passwords, expose private VPN keys, or grant unrelated Flatpak filesystem permissions.

## License

A license will be selected when the source is uploaded.