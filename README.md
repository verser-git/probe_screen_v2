# Probe Screen for LinuxCNC

 Install.
-----------------------------------------------------------------------------
1. Add to your .ini ...-postgui.hal settings from my-mill.ini and my-mill-postgui.hal, substitute your own constants.

2. The following folders from the archive are placed in configuration folder:
/python,
/macros,
/probe_icons

3. .axisrc is placed in home ~/ folder.
If you are already using .axisrc, then only add to your file contents of this .axisrc.

4. Delete (or comment out) from all .hal files lines of the form:
```sh
#loadusr -W hal_manualtoolchange
#net tool-change iocontrol.0.tool-change => hal_manualtoolchange.change
#net tool-changed iocontrol.0.tool-changed <= hal_manualtoolchange.changed
#net tool-number iocontrol.0.tool-prep-number => hal_manualtoolchange.number
#net tool-prepare-loopback iocontrol.0.tool-prepare => iocontrol.0.tool-prepared
```

Use.
----------------------------------------------------------------------------------
Set the probe in the spindle.
Move manually probe for Z about 2-10 mm above the workpiece surface, 
and for XY about the position indicated by the colored dot on the appropriate button Probe Screen.
Fill parameters. Meaning of the parameters should be clear from the names and pictures (the name pop up when approaching the mouse). If you change the parameters are automatically saved in .pref .

Hit only! the button that corresponds to the position of the probe above the workpiece. For the other buttons - another position above the workpiece.  

You do not need to expose offsets for tool "Probe", the program desired zero offsets for the current tool makes herself, and G-code works off all in relative coordinates. 
In fact, you can use the application immediately after the Home.


Any of the search ends at XY moving at the desired point (or edge, or corner, or center), Z remains in the original position.
