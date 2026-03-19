NOSY stands for Non-Executing Observer of Storage Yields. it's a simple-to-use USB forensics tool designed to allow you to view the contents of unknown USB devices, without causing harm to your device. It is intended to be used on Raspberry Pi systems through the terminal, through SSH to avoid causing any harm to your main machine. 

This tool allows for viewing of files on USB devices through terminal as plaintext for .txt files, but also allows you to view images on the USB device through the terminal using the timg tool. (sudo apt install timg)
It also allows you to view all the contents through a web server, if that's more of your thing. 

NOTE/WARNING: THIS DEVICE WILL NOT PROTECT AGAINST USBKILLER DEVICES. IF YOU PLUG IN AN UNKNOWN USB DRIVE TO YOUR RASPBERRY PI AND IT DIES, BE HAPPY THAT IT WASN'T YOUR MAIN MACHINE.

Steps to use:
-Clone into the repo 
-That's it. Python3 nosy.py and you're good to go. 