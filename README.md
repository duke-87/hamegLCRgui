hamegLCRqui
=========
*Python serial driver for controlling Hameg (Rohde&Schwarz) LCR bridge and simple GUI for performing automated measurements*

More information on the communicatin protocol and commands can be found in [Programable LCR-Bridge HM8118 User Manual](http://www.hameg.com/manuals.0.html?&no_cache=1&tx_hmdownloads_pi1[mode]=download&tx_hmdownloads_pi1[uid]=959).

**NOTE**: This software is NOT a product of *HAMEG Instruments GmbH*.

# Main Features

* Setting up and performing automated measurements
* Exporting measurement data to Excel Spreadsheet 
* Saving measurement graphs in PNG format

# Requirements
The bare serial driver (hamegLCR.py) requires only the [pySerial](https://github.com/pyserial/pyserial) package.
To run the GUI (hamegLCRgui.py) the following packages are additionally required:

* PyQt4
* PyQwt5
* NumPy

On Windows machines it is requred to install Virtual COM Port (VCP) driver.
To do this, follow a simple instructions found in [Dual Interface H0820 Installation Guide](http://www.hameg.com/drivers.0.html?&no_cache=1&tx_hmdownloads_pi1[mode]=download&tx_hmdownloads_pi1[uid]=6147) or similar.

Exporting measurement into an Excel file is supported if the following packages are present (if these pacgages are not found, this functionality is disabled):

* pandas
* openpyxl

The `hamegLCRgui` software was tested on Linux and Windows platforms.

# Examples

## Open device

    from hamegLCR import HamegLCR

    # open the first connected USBTMC device (/dev/usbtmc0)
    hameg = HamegLCR()

or

    from hamegLCR import HamegLCR

    # open a specific device on Linux
    hameg = HamegLCR("/dev/ttyUSB0")

    # open a specific device on Windows
    hameg = HamegLCR("COM27")

## Read value

    hameg.getMainValue()

# Screenshot
![alt text][tab01]

[tab01]: screenshot_01.png "The main tab of the GUI."
