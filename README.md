# Probe Screen for LinuxCNC

 Installation.
-----------------------------------------------------------------------------
1. Add to your .ini these settings

```sh
[DISPLAY]

DISPLAY = axis

EMBED_TAB_NAME=Probe Screen 
EMBED_TAB_COMMAND=halcmd loadusr -Wn gladevcp gladevcp -c gladevcp -u python/probe_screen.py -x {XID} probe_icons/probe_screen.glade 

PREFERENCE_FILE_PATH = ./manualtoolchange.pref

......
[RS274NGC]

FEATURES=30
SUBROUTINE_PATH = your_subroutine_path
```
This application can be easily connected to Gmoccapy, differ only in lines for panel connection
```sh
EMBED_TAB_NAME=Probe Screen 
EMBED_TAB_LOCATION = ntb_user_tabs
EMBED_TAB_COMMAND = gladevcp  -x {XID} -u python/probe_screen.py probe_icons/probe_screen.glade 
```

2. The following files from the archive are placed in:

your-folder-configuration/pyton
probe_screen.py

your-folder-configuration/your_subroutine_path
all from folder "macros"

your-folder-configuration/probe_icons
all from folder "probe_icons"

your-folder-configuration
manualtoolchange.pref[/spoiler]

Use.
----------------------------------------------------------------------------------
Set the probe in the spindle.
Move manually probe for Z about 2-10 mm above the workpiece surface, 
and for XY about the position indicated by the colored dot on the appropriate button Probe Screen.
Fill parameters. Meaning of the parameters should be clear from the names and pictures (the name pop up when approaching the mouse). If you change the parameters are automatically saved in manualtoolchange.pref .

Hit only! the button that corresponds to the position of the probe above the workpiece. For the other buttons - another position above the workpiece.  

You do not need to expose offsets for tool "Probe", the program desired zero offsets for the current tool makes herself, and G-code works off all in relative coordinates. 
In fact, you can use the application immediately after the Home.


Any of the search ends at XY moving at the desired point (or edge, or corner, or center), Z remains in the original position.
