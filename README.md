[![](https://img.shields.io/github/release/mtrab/danfoss_ally/all.svg?style=plastic)](https://github.com/mtrab/danfoss_ally/releases)
# Danfoss Ally

This is a custom component for Home Assistant to integrate the Danfoss Ally devices

**This is under development. use at own risk!**

### Installation:

#### HACS

- Ensure that HACS is installed.
- Search for and install the "Danfoss Ally" integration.
- Restart Home Assistant.

#### Manual installation

- Download the latest release.
- Unpack the release and copy the custom_components/danfoss_ally directory into the custom_components directory of your Home Assistant installation.
- Restart Home Assistant.

## Setup

First of all you need to go at get an api key and secret

* Navigate to https://developer.danfoss.com
* Create danfoss profile account and login
* Go to https://developer.danfoss.com/my-apps and click "New App"
* Give the app a name and description (naming and description is not of any importance as it's only for your use)
* Make sure to enable Danfoss Ally API
* Click create
* Save your key and secret - these will be used when adding the integration
* Go to Home Assistant > Settings > Integrations
* Add Danfoss Ally integration
* Enter API key and secret

Voila

## Known issues

* Climate and sensor entities are not grouped correctly under integrations - purely a visual issue and not functional
* Inconsistency between API and app, devices are not updating correctly between API and app and sometimes the devices renders offline in the app - this is a Danfoss issue and not this integration
* Floorheating modules (Icon) are not reporting the actual room temperature in the API - this is a Danfoss issue and not this integration
