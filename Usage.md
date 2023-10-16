## Usage

This integration has been made by enthusiasts with no insights to internal Danfoss documentation.
We are only able to find the same public information as you are.
Some good information can be found here though:

- [Programming reference for Danfoss eTRV](https://assets.danfoss.com/documents/202524/AU417130778872en-000101.pdf)
- [Zigbee specification for Danfoss eTRV](https://assets.danfoss.com/documents/193613/AM375549618098en-000102.pdf)

The following is our understanding after the reading the linked documents and experimenting with the settings.
We urge you to experiment with the features you would like to make use of.

&nbsp;

#### Banner control

Banner control is a binary sensor that indicates if the setpoint is overridden locally from the thermostat.
This is also reported in the Ally app as a "Temporary setpoint".

&nbsp;

#### Pre-heat

- **Pre-Heat** switch located in the Configuration section can be used to turn on and off the pre-heat feature.
  It is similar to the switch in the Ally mobile app.
- **Pre-Heating** is a binary sensor that indicates it is it currently pre-heating.
  With pre-heating it attempts to automatically determine how long before before a switch from `Away` to `Home` it should start to heat, to reach the target temperature when the scheduled time is reached.

&nbsp;

#### Temparature readings

As the integration has evolved more and more temperature readings are becoming available, and it also differs depending on device type.

- **Temperature** sensor: This is the temperature measured locally by the thermostat.
  For a radiator it is measured by the thermostat, for Icon it is the one measured by the room 'thermostat' and for an Ally room sensor it is obviously the one measure by it.
- **Floor temperature** sensor: In addition to the air temperature, some Danfoss Icon room 'thermostats' also measure the floor temperature by utilizing an infrared sensor. This sensor reports the measured value.
  The sensor only appears when the room 'thermostat' has the infrared sensor.
- **External sensor temperature**: This is the temperature measurement that is being sent to a radiator thermostat, typically by an Ally room sensor. However, this external temperature can also be sent through the API (see service call).
- **Climate control current temparature**: This value most often shows the local temperature. However, for a radiator thermostat it can also show the external temperature here. It depends what mode it is in:
  - `Room Sensor Mode` (Covered radiators): Reports the external sensor temparature as current measurement
    (This is new from version 1.2.0. This is similar to the Ally mobile app)
  - `Auto Offset Mode` (Exposed radiators / uncovered): Reports the local temperature as current measurement
- **Radiator covered** switch: This is a switch that can be used to control mode. Basically it determines how it uses an external temperature measurement.
  - When covered it is in `Room Sensor Mode`: Here it uses the external temperature solely and bases valve regulation on it.
  - When not covered it is in `Auto Offset Mode`: Here the external temperature is used to calculate an offset up to ± 2.5°C. Then it uses this offset and its local temperature while regulating the valve.
    (we are not currently able to read the offset from the API)
- Service call **Danfoss Ally: Set external temperature**: This service call can send an external temperature to a radiator thermostat, similar to an Ally room sensor. If the radiator is placed so it cannot reliably determine temperature in the room, or you have another sensor placed better, you can now use it instead of an Ally room sensor. It means of course it is not a one-off call, it needs to be activated whenever the temperature changes.
  Example automation:

      alias: Set radiator external temperature
      description: ""
      trigger:
        - platform: state
          entity_id:
            - sensor.some_temperature_entity
          from: null
        - platform: time_pattern
          minutes: /30
      condition: []
      action:
        - service: danfoss_ally.set_external_temperature
          data:
            temperature: "{{ states('sensor.some_temperature_entity') }}"
          target:
            entity_id: climate.danfoss_allytm_radiator_thermostat
      mode: single

  It calls the service whenever the source entity changes, but note that it also does every 30 minutes.
  When in Room Sensor Mode it must be called at least every 30 minutes. After 35 minutes without an update it goes back to using the local temperature.
  When in Auto Offset Mode it must instead be called at least every 3 hours.
  To preserve battery it is also recommended not to set value more frequent than every 5 minutes (30 in offset mode). The integration will automatically avoid too frequent calls with the same value.

  To actively disable the feature and go back to local measurement, send temperature -80°C or any non-numeric value.

  Use this feature to try out how an external sensor temperature would work. Realibility-wise do not expect it to be as reliable as an Ally room sensor.
  Just consider the communication path. The ally room sensor is using Zigbee like the thermostat, meaning that in theory it can send readings directly (it is unknown if it actually does, or if it goes through the gateway). Meaning not being dependent of the Ally gateway, power, internet or the Danfoss cloud, at least for a while. If the external temperature is set by Home Assistant, it is dependent of all this, including HA, your other sensor and possibly another Zigbee network.
  However it does work and you can usually set an an external temperature this way. Just also consider what happens if/when disrupted.
  Note: Currently we are not able to see if/when it switches back to using its own temperature reading.

  You can import the blueprint below for updating your radiator thermostats with an external temperature reading. Selecting several temperature sensors will update the thermostat with an average of the measured temperatures. If you select multiple radiator thermostats they'll all be updated with the measured temperature.
  
  Create one automation per room where you have external temperature sensors and Ally thermostats.

  [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgist.github.com%2Ftbarnekov%2F02962fb065d8a6831d11ebeead4d6141)
  
  
&nbsp;

#### Set target temperature

To set target temperature for a thermostat there is a function named "Set preset temperature". This is exposed both as a service call and as a device action in automations.
In both cases there are two arguments:

- Temperature (required)
- Preset mode (optional)
  Preset mode determines which mode the target temperature is set for, ex. `Manual`, `Home`, `Away` etc. If not specified, target temperature will be set for the current preset mode.

&nbsp;

#### Set HVAC mode

With this device action we can switch between `heat` and `auto`.
Basically it is translated to preset modes `manual` and `home` respectively.

&nbsp;

#### Set preset mode

With this device action we can switch switch to preset modes: `Home`, `Away`, `Manual`, `Pause`, `Holiday (Home)` & `Holiday (Away)`

&nbsp;

#### Open Window _(\*1)_

This feature turns off heat to a radiator if an open window is detected. It has the ability to detect this itself, but we can also tell it that a window is open.
However this feature is disabled in `Room Sensor Mode` (covered)

- **Open window detection**: is a switch that enables and disables the open window feature.
  It is similar to the switch in the Ally app.
- **Open window**: A windows is open and it will reduce heat.
- Service call **Danfoss Ally: Set window open state**: By calling this service we can tell it if a window is currently open or not.

&nbsp;

#### Mounting mode _(\*1)_

In the Diagnostic sections radiators will have two binary sensors:

- **Mounting mode control**: This indicates if the thermostat is in mounting mode, like when you initially mounted it on the valve. You can also make to go into this mode afterwards by holding the button for one second, an M is written in the display and preasure on the valve is released (opens valve fully).
  The API allows for this to be set, but to avoid costly mistakes this integration shows it as read only. There is little reason to set it in mounting mode from Home Assistant anyway.
- **Mounting mode active**: This indicates if it has detected that it is mounted (probably detected some resistance to push the valve).

&nbsp;

#### Valve opening _(\*1)_

In the Diagnostic sections radiators will have a sensor with a percentage value saying how much open the valve is. 0% means it is closed, 100% that it is fully open. The thermostat regulates this valve in attempt to reach the target temperature.
This value is read-only, we can only use it to get some insights.

&nbsp;

#### Load balance _(\*1)_

In rooms with multiple radiadors this feature can be used. It lets Ally determine how much load should be delivered by each radiator (see Programming reference for a more details).
We have two sensors and a switch made available:

- **Load room mean**: A value calculated by the gateway and sent to all radiators in the room.
- **Load estimate**: The load on each radiator.
- **Load balance** switch: An enable/disable switch. Indicates if you want to use the feature or not.

&nbsp;

#### Heat available _(\*1)_

In this section we have two binary sensors and a switch:

- **Boiler relay**: Likely a signal to a gas boiler or similar to indicate heat is needed.
- **Heat supply request**: Likely similar to Boiler relay. The difference may be explained in the Programming reference, section 2.6.
- **Heat available** switch: A signal to the thermostat. Probably indicating if water is heated sufficuently. Default on.

&nbsp;

#### Adaptation run _(\*1)_

In order for the thermostat to run optimally it regularly performs an adaptation run to estimate the Valve characteristic.

- **Adaptation run status**: Indicates if it is currently performing an adaptation run.
- **Adaptation run valve characteristic found**: Indicates that adaptation run was successful, and it determined the valve characteristic.

&nbsp;

#### Heating Control Scaling _(\*1)_

With this control option you can set how aggressive the control algorithm controls the valve opening.
Possible values:

- Quick (5min)
- Moderate (30min)
- Slow (80min)

&nbsp;

_(\*1): Radiator only_
