# Home Assistant Integration for Inim Cloud

A custom Home Assistant integration to control and monitor Inim Cloud alarm systems. This integration allows you to:

- Monitor your Inim alarm system status
- Control your alarm (arm, disarm)
- View device information and scenarios

## Features

- Alarm control panel support (arm away, arm home, disarm)
- Device information
- Real-time status updates

## Installation

### HACS (Home Assistant Community Store)

1. Add this repository to HACS as a custom repository
2. Search for "Inim Cloud" in HACS and install it
3. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/inim_cloud` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Home Assistant Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Inim Cloud"
4. Follow the configuration steps

## Requirements

- An Inim Cloud account
- Inim alarm system connected to Inim Cloud

## Supported Models

This integration has been tested with:

- Inim SmartLiving

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License.
