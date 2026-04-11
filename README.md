[![danfoss_ally](https://img.shields.io/github/release/mtrab/danfoss_ally/all.svg?style=plastic&label=Current%20release)](https://github.com/mtrab/danfoss_ally) [![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=plastic)](https://github.com/custom-components/hacs) [![downloads](https://img.shields.io/github/downloads/mtrab/danfoss_ally/total?style=plastic&label=Total%20downloads)](https://github.com/mtrab/danfoss_ally) [![Buy me a coffee](https://img.shields.io/static/v1?label=Buy%20me%20a%20coffee&message=and%20say%20thanks&color=orange&logo=buymeacoffee&logoColor=white&style=plastic)](https://www.buymeacoffee.com/mtrab)

# Danfoss Ally

This is a custom component for Home Assistant to integrate the Danfoss Ally and Icon devices via Danfoss Ally gateway

### Installation:

#### HACS

- Ensure that HACS is installed.
- Add this repository as a custom repository
- Search for and install the "Danfoss Ally" integration.
- Restart Home Assistant.

#### Manual installation

- Download the latest release.
- Unpack the release and copy the custom_components/danfoss_ally directory into the custom_components directory of your Home Assistant installation.
- Restart Home Assistant.

## Setup

First of all you need to create a Consumer Key and Consumer Secret

- Navigate to https://developer.danfoss.com
- Create Danfoss developer account and login _<u><b>NOTE:</b> Use the same email as used in the Danfoss Ally app for pairing your gateway</u>_
- Go to https://developer.danfoss.com/user/apps and click `Add App`
- Give the app a name and description (naming and description is not of any importance as it's only for your use)
- Make sure to enable Danfoss Ally API
- Click `Submit`
- Click on your app (the name you gave it)
- Save your `Consumer Key` and `Consumer Secret` - these will be used when adding the integration
- Go to `Home Assistant > Settings > Integrations`
- Add Danfoss Ally integration _(If it doesn't show, try CTRL+F5 to force a refresh of the page)_
- Enter your `Consumer Key` and `Consumer Secret`

Voila

## Usage

This integration is built from public Danfoss documentation and hands-on testing. We do not have access to Danfoss internal documentation, so parts of the behavior described below are based on what we have been able to observe in practice.

### Pre-heat

- The **Pre-Heat** switch in the configuration section turns pre-heat on and off.
- The **Pre-Heating** binary sensor shows when the device is currently pre-heating.
- When enabled, the thermostat tries to learn how early it should start heating before a scheduled change from `Away` to `Home`.

### Temperature readings

The available temperature readings vary a bit depending on the device type.

- **Temperature**: The local temperature measured by the device itself.
- **Floor temperature**: Available on supported Danfoss Icon room thermostats with an infrared floor sensor.
- **External sensor temperature**: The temperature currently being sent to a radiator thermostat from an external source.
- **Climate control current temperature**: Usually the local temperature, but on radiator thermostats it may show the external temperature instead, depending on mode.
- **Radiator covered**: Controls how a radiator thermostat uses an external temperature reading.

For radiator thermostats:

- In `Room Sensor Mode` for covered radiators, the thermostat uses the external temperature directly.
- In `Auto Offset Mode` for uncovered radiators, the thermostat uses the external reading to calculate an offset against its own measurement.

### External temperature sensors

Radiator thermostats can use an external temperature sensor selected directly in the thermostat configuration in Home Assistant.

Open the thermostat, choose the temperature sensor you want to use, and save the change. From there, the integration keeps the thermostat updated automatically.

This replaces the old Blueprint-based setup for most users and makes the feature much easier to configure and maintain.

### Device actions and services

- **Set preset temperature** lets you set a target temperature for a specific preset mode, or for the active preset if no preset is supplied.
- **Set HVAC mode** switches between `heat` and `auto`, which maps to `manual` and `home`.
- **Set preset mode** lets you switch between `Home`, `Away`, `Pause`, and `Holiday`.

### Open window

This feature reduces heating when a window is open. The thermostat can detect this itself, and Home Assistant can also set the state through the `Danfoss Ally: Set window open state` service.

- **Open window detection** enables or disables the feature.
- **Open window** shows whether the thermostat currently considers a window to be open.

### Window pause automation

Radiator thermostats can also pause heating from Home Assistant when a selected window sensor, or a Home Assistant group of window sensors, stays open for more than one minute.

Open the thermostat in Home Assistant, choose the `Window sensor source`, and save the change. When the selected entity stays open for more than one minute, the integration switches the thermostat to pause mode. When it has stayed closed for more than one minute, the previous thermostat mode and target temperature are restored.

The previous thermostat state is stored persistently, so the pause or restore flow still resumes correctly after a Home Assistant restart. On startup, the integration re-checks the current window sensor state before deciding whether it should pause heating or restore it.

This feature is disabled in `Room Sensor Mode`.

### Diagnostic entities

Depending on device type, additional entities may be available.

- **Mounting mode control** and **Mounting mode active** are radiator-only diagnostics related to installation state.
- **Valve opening** shows how far the radiator valve is open, from `0%` to `100%`.
- **Load room mean**, **Load estimate**, and **Load balance** are radiator-only entities related to load balancing in rooms with multiple radiators.
- **Heat supply request** and **Heat available** expose heat availability related signals for radiator devices.
- **Adaptation run status** and **Adaptation run valve characteristic found** show whether a radiator thermostat is currently tuning itself.
- **Heating Control Scaling** adjusts how aggressively the thermostat regulates the valve, with `Quick`, `Moderate`, and `Slow` options.
- **Thermal Actuator** is an Icon-only binary sensor that indicates whether the actuator is open or closed.

Radiator-only entities are marked in Home Assistant by where they appear and on which devices they are created. The same goes for Icon-only entities.

## Known issues

- Inconsistency between API and app, devices are not updating correctly between API and app and sometimes the devices renders offline in the app - this is a Danfoss issue and not this integration
- Danfoss Ally cloud/API synchronization is not real-time. Changes made from Home Assistant, the Danfoss app, or directly on a device may take a few minutes before they are reflected consistently across the API and the physical device state.
- For debugging API performance or timeout issues, you can inspect API analytics in `Danfoss Developer Portal > Apps > [app name] > Analytics`, next to `Credentials`.





