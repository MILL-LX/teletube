# teletube
Payphone adapted to play videos

## Set up the Pi

### OS

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to create the OS image for your Pi.

This project has been developed on a Raspberry Pi 4 running *Trixie 32-bit Light* with SSH enabled and a public key installed. Installing the public key will make your life easier if you like to use the VSCode Remote SSH plugin to develop directly on the Pi.

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
sudo apt install mpv
```

### Clone this project

```bash
git clone https://github.com/MILL-LX/teletube.git
cd teletube
```

### Make the Project's Python Virtual Environment

```bash
cd teletube/app
uv sync
```
