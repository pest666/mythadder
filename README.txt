This document assumes you are running default Ubuntu 9.10 and MythTV .23 fixes.
This version was created from my original code by wagnerrp from the MythTV wiki.

Your mileage may vary with other distros or MythTV version.

****************************************************************

Do the following on every frontend you want to have mythadder on:

*** PYTHON AND PYTHON MYSQLDB

sudo apt-get install python python-mysqldb

*** MYTHADDER.PY:

sudo cp mythadder.py /usr/bin
sudo chmod +x /usr/bin/mythadder.py

*** UDEV RULE:

sudo cp 99-mythadder.rules /etc/udev/rules.d
sudo /etc/init.d/udev restart

****************************************************************

If Ubuntu is automounting your usb drives correctly, and before the mount delay runs out, 
you should now see video files from your removable media in mythvideo when you attach them.

The default delay is 10 seconds, and you may need to go out to the main menu
and then back into media center/videos for Myth to re-read the database.

Enjoy and if i've done something dumb, it's because this is the first python script I've ever
written.

Hello to the guys at at abhdtv.net.


