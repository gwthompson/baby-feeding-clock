# Baby Feeding Clock

## Introduction 

Recently, we had a baby and my girlfriend started breast feeding. Monitoring the duration of the feeding, how much time since the last one and how many during the day was a pain. So, I decided to build an easy to use clock that would display all the relevant info. 

Adafruit's PyPortal ([more info](https://learn.adafruit.com/adafruit-pyportal)) was used for this project. It integrates all the needed components in a compact package: 

- ATMEL (Microchip) ATSAMD51J20
- 3.2″ 320 x 240 color TFT with resistive touch screen.
- Espressif ESP32 Wi-Fi coprocessor

## Details

The main characteristics of the feeding clock are:

- An information screen that displays the time since the last feeding and the number of feeding during the day.

![info](/doc/screen_info.jpg)

- A timer screen that displays the time since the beginning of the feeding.

![timer](/doc/screen_timer.jpg)

- Simple touch interface. One touch to display the information screen for 30 sec and a second one to start the timer screen. Finally, a third touch to end the timer and go back to the information screen with the updated info.

- Start, end feeding time as well as the cumulative number of feedings are sent to [Adafruit IO ](https://io.adafruit.com) automatically for further analysis and history saving.

## Setup 

To install all the needed librairies follow the steps [here](https://learn.adafruit.com/adafruit-pyportal/circuitpython-libraries). Background & fonts used are included in this repository but can easily be modified. Finally, add a file named ```secrets.py``` at the root of the Circuit Python drive with the following information:


```Python
secrets = {
    'ssid' : 'your_ssid',
    'password' : 'your_ssid_password',
    'timezone' : "your_timezone_to_set_the_time",
    'aio_username' : 'your_adafruit_io_username',
    'aio_key' : 'your_adafruit_io_key',
    }
```