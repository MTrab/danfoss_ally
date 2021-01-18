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