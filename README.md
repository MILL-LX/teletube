# teletube
Payphone adapted to play videos

## Set up the Pi

### OS

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to create the OS image for your Pi.

This project has been developed on a Raspberry Pi 4 running *Trixie 64-bit Light* with SSH enabled and a public key installed. Installing the public key will make your life easier if you like to use the VSCode Remote SSH plugin to develop directly on the Pi.

### Tooling

#### Update the OS packages

```bash
sudo apt update
sudo apt full-upgrade
```

#### Install Tools and Dependencies

```bash
sudo apt install \
    git \
    python3 \
    python3-pip
```

# telejuke

Telephone World Jukebox

## OS

Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to create the OS image for your Pi.

This project has been developed on a Raspberry Pi 4 running Bookworm Desktop 32-bit* with SSH enabled.

Drop your public SSH key in ```~/.ssh/authorized_keys``` if you like. Installing the public key will make your life easier if you like to use the VSCode Remote SSH plugin to develop directly on the Pi.

## System Packages for Python Development and FBCP Build

```bash
sudo apt update
sudo apt full-upgrade
sudo apt install \
    git \
    python3 \
    python3-pip \
    python3-venv \
    # cmake \
    # libraspberrypi-dev \
    # libraspberrypi0 \
    # xserver-xorg-video-fbturbo \
    -y

python -m venv env --system-site-packages
```

## Configure Waveshare Display as a second Wayland display

### Edit /boot/firmwre/config.txt

```bash
# Enable KMS (Wayland-compatible)
dtoverlay=vc4-kms-v3d

# HDMI config for Waveshare 4-inch LCD
dtparam=spi=on
hdmi_force_hotplug=1
# dtoverlay=waveshare35a
max_usb_current=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 480 320 60 6 0 0 0
hdmi_drive=2
display_rotate=180
```

## Add WiFi Networks

If this will join networks besides the one configured when creatind the SD Card, you can add them with the Text UI for the Network Manager.

```bash
sudo nmtui
```

## [uv](https://github.com/astral-sh/uv) for Python Dependency Management

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Touch Screen Setup

Based on the [Waveshare Wiki](https://www.waveshare.com/wiki/3.5inch_RPi_LCD_(A)_Manual_Configuration#For_Raspberry_Pi_4_.26_Raspberry_Pi_5)

Download and install the driver:

```bash
mkdir waveshare-install
cd waveshare-install
wget https://files.waveshare.com/upload/1/1e/Waveshare35a.zip
unzip Waveshare35a.zip
sudo cp waveshare35a.dtbo /boot/overlays
```

Edit `/boot/firmware/config.txt`:

Comment out:

```bash
# Enable DRM VC4 V3D driver
dtoverlay=vc4-kms-v3d
max_framebuffers=2
```

Add:

```bash
dtparam=spi=on
dtoverlay=waveshare35a
hdmi_force_hotplug=1
max_usb_current=1
hdmi_group=2
hdmi_mode=1
hdmi_mode=87
hdmi_cvt 480 320 60 6 0 0 0
hdmi_drive=2
display_rotate=180
```

## Application Setup

### Add OS Dependencies - REVISIT BASED ON ACTUAL PYTHON LIBRARIES USED

```bash
sudo apt update
sudo apt install ffmpeg libffi-dev
sudo apt install libportaudio2 libportaudiocpp0 portaudio19-dev
# MOFIX - unnecessary? sudo apt install python3-dev python3-pip python3-venv gfortran libopenblas-dev liblapack-dev build-essential meson ninja-build
```

### Clone this project

```bash
git clone https://github.com/MILL-LX/teletube.git
cd teletube
```

### Make the Project's Python Virtual Environment

```bash
cd teletube/app
uv venv #MOFIX --system-site-packages
uv sync
```
