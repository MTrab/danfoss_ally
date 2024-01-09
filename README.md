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

First of all you need to go and create an api-key and secret

- Navigate to https://developer.danfoss.com
- Create Danfoss developer account and login _<u><b>NOTE:</b> Use the same email as used in the Danfoss Ally app for pairing your gateway</u>_
- Go to https://developer.danfoss.com/my-apps and click "New App"
- Give the app a name and description (naming and description is not of any importance as it's only for your use)
- Make sure to enable Danfoss Ally API
- Click create
- Save your key and secret - these will be used when adding the integration
- Go to Home Assistant > Settings > Integrations
- Add Danfoss Ally integration _(If it doesn't show, try CTRL+F5 to force a refresh of the page)_
- Enter API key and secret

Voila

## Usage

See: [Usage.md](Usage.md)

## Known issues

- Inconsistency between API and app, devices are not updating correctly between API and app and sometimes the devices renders offline in the app - this is a Danfoss issue and not this integration
- Floorheating modules (Icon) are not reporting the actual room temperature in the API - this is a Danfoss issue and not this integration
