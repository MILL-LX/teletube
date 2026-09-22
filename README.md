# teletube
Payphone adapted to play videos

## Set up the Pi

### OS

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to create the OS image for your Pi.

This project has been developed on a Raspberry Pi 4 running *Trixie 64-bit Light* with SSH enabled and a public key installed. Installing the public key will make your life easier if you like to use the VSCode Remote SSH plugin to develop directly on the Pi. We use 64-bit to ease on-device development because VSCode Remote SSH stopped working on 32-bit. For final deployment 32-bit can save memory.

### Add WiFi Networks

If this will join networks besides the one configured when creatind the SD Card, you can add them with the Text UI for the Network Manager.

```bash
sudo nmtui
```

### Tooling

#### Update the OS packages

```bash
sudo apt update
sudo apt full-upgrade
```

### Touch Screen Setup

Edit `/boot/firmware/config.txt` and add:

```bash
dtoverlay=vc4-kms-v3d
dtoverlay=vc4-kms-dsi-waveshare-panel,4_0_inch
```

Edit `/boot/firmware/cmdline.txt` and prepend the following to the first line:

```bash
video=DSI-1:480x800e,rotate=90 
```

Reboot the Pi.

## Application Setup

### Install Dev Tools

```bash
sudo apt install \
    git \
    -y
```

### [uv](https://github.com/astral-sh/uv) for Python Dependency Management

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Add Application System Dependencies

```bash
sudo apt update
sudo apt install mpv \
                 libportaudio2 \
                 zlib1g-dev libjpeg-dev libfreetype6-dev # for buiding Pillow if used
```

### Clone this project

```bash
git clone https://github.com/MILL-LX/teletube.git
cd teletube
```

### Make the Project's Python Virtual Environment

```bash
cd app
uv sync
```

## Running

In production the application runs as a set of systemd services. See
[`app/systemd/README.md`](app/systemd/README.md) for how to install and
manage them.

## Diagnostics

### Message Monitor

`monitor.py` is a manual diagnostic tool that subscribes to every topic on
the broker and prints each message as it arrives. It is **not** a system
service — run it by hand when you want to watch the message traffic (for
example, to confirm keypad or hook events are being published).

The broker must already be running (via the systemd services or `start.sh`).
Then, from the `app` directory:

```bash
cd app
PYTHONPATH=src uv run python src/apps/monitor.py
```

Press `Ctrl+C` to stop. Output looks like:

```
Monitoring... Ctrl+C to stop
[phone_hook] {'state': 'lifted'}
[keypad] {'year_entered': '1976'}
```
