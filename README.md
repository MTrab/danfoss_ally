# Danfoss Ally


This integration is forked from: **[MTrab / danfoss_ally](https://github.com/MTrab/danfoss_ally)**  v1.0.7
  
### Additions

- Reading and writing setpoints using: `manual_mode_fast`, `at_home_setting`, `leaving_home_setting`, `pause_setting`, `holiday_setting` depending on the preset mode, rather than using `temp_set` as before.
It seems to work, so far.
 
- Holiday preset mode added.
 
- Quicker reaction to changes performed in the UI
 
- Added floor temperature sensor
 
- Fix for setmode issue

- Added action and service call to set target temperature for a specific preset mode.  
Preset mode is optional, and writes to current preset mode when not specified.

- Added an indication for 'banner control' (local override).  
When setpoint is changed locally from the thermostate it raises this flag and uses this as manual target setpoint.  


##### Things to note in the Danfoss Ally app

- The app shows the floor temperature (when present) in the overview, and the room temperature on the details page. That is somewhat confusing, I think. Especially when it doesn't indicate it which is which.

- When switching to manual mode from the app, it will take the previous taget temparature as target also for manual. Thus, overwrite target temperature for manual preset.
Switching from this integration will just switch to manual and not overwrite target temperature, unless specifically set. 
  
*Note: Changes are limited tested with radiator thermostates*
<br/>
<br/>
<br/>
<br/>
<br/>
<br/>
<br/>
<br/>

---
Previous README

---
<br/>

[![](https://img.shields.io/github/release/mtrab/danfoss_ally/all.svg?style=plastic)](https://github.com/mtrab/danfoss_ally/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=plastic)](https://github.com/custom-components/hacs)

<a href="https://www.buymeacoffee.com/mtrab" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>
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

First of all you need to go at get an api key and secret

* Navigate to https://developer.danfoss.com
* Create danfoss profile account and login
* Go to https://developer.danfoss.com/my-apps and click "New App"
* Give the app a name and description (naming and description is not of any importance as it's only for your use)
* Make sure to enable Danfoss Ally API
* Click create
* Save your key and secret - these will be used when adding the integration
* Go to Home Assistant > Settings > Integrations
* Add Danfoss Ally integration *(If it doesn't show, try CTRL+F5 to force a refresh of the page)*
* Enter API key and secret

Voila

## Known issues

* Inconsistency between API and app, devices are not updating correctly between API and app and sometimes the devices renders offline in the app - this is a Danfoss issue and not this integration
* Floorheating modules (Icon) are not reporting the actual room temperature in the API - this is a Danfoss issue and not this integration
