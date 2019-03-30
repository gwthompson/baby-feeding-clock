# Baby Feeding Clock

## Introduction 

Recently, we had a baby and my girlfriend started breast feeding. Monitoring the duration of the feeding, how much time since the last one and how many during the day was a pain. So, I decided to build an easy to use clock that would display all the relevant info. 

Adafruit's PyPortal ([more info](https://learn.adafruit.com/adafruit-pyportal)) was used for this project. It integrates all the needed components in a nice package: 

- ATMEL (Microchip) ATSAMD51J20
- 3.2″ 320 x 240 color TFT with resistive touch screen.
- Espressif ESP32 Wi-Fi coprocessor

## Details

The main parts of the feeding clock are:

- An information screen that displays the time since the last feeding and the number of feeding during the day.


![logo](/doc/screen_info.jpg)

- A timer screen that displays the time since the beginning of the feeding.

## Setup 

To install all the needed librairies follow the steps [here](https://learn.adafruit.com/adafruit-pyportal/circuitpython-libraries). Background & fonts used are included in this repository but can easily be modified.