#!/usr/bin/env python
#
# Copyright (c) 2015 Serguei Glavatski ( verser  from cnc-club.ru )
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import hal                  # base hal class to react to hal signals
import os                   # needed to get the paths and directorys
import hal_glib             # needed to make our own hal pins
import gtk                  # base for pygtk widgets and constants
import gtk.glade
import sys                  # handle system calls
import linuxcnc             # to get our own error sytsem
import gobject              # needed to add the timer for periodic
import pygtk
import gladevcp
import pango
from linuxcnc import ini
import ConfigParser
from datetime import datetime

CONFIGPATH1 = os.environ['CONFIG_DIR']


cp1 = ConfigParser.RawConfigParser
class ps_preferences(cp1):
    types = {
        bool: cp1.getboolean,
        float: cp1.getfloat,
        int: cp1.getint,
        str: cp1.get,
        repr: lambda self, section, option: eval(cp1.get(self, section, option)),
    }

    def __init__(self, path = None):
        cp1.__init__(self)
        if not path:
            path = "~/.toolch_preferences"
        self.fn = os.path.expanduser(path)
        self.read(self.fn)

    def getpref(self, option, default = False, type = bool):
        m = self.types.get(type)
        try:
            o = m(self, "DEFAULT", option)
        except Exception, detail:
            print detail
            self.set("DEFAULT", option, default)
            self.write(open(self.fn, "w"))
            if type in(bool, float, int):
                o = type(default)
            else:
                o = default
        return o

    def putpref(self, option, value, type = bool):
        self.set("DEFAULT", option, type(value))
        self.write(open(self.fn, "w"))


class ProbeScreenClass:
    
    def error_poll(self):
        error = self.e.poll()
        if error:
            kind, text = error
            if kind in (linuxcnc.NML_ERROR, linuxcnc.OPERATOR_ERROR):
                typus = "error"
                print typus, text
                return -1
            else:
                typus = "info"
                print typus, text
                return -1


    def get_preference_file_path(self):
        # we get the preference file, if there is none given in the INI
        # we use toolchange2.pref in the config dir
        temp = self.inifile.find("DISPLAY", "PREFERENCE_FILE_PATH")
        if not temp:
            machinename = self.inifile.find("EMC", "MACHINE")
            if not machinename:
                temp = os.path.join(CONFIGPATH1, "probe_screen.pref")
            else:
                machinename = machinename.replace(" ", "_")
                temp = os.path.join(CONFIGPATH1, "%s.pref" % machinename)
        print("****  probe_screen GETINIINFO **** \n Preference file path: %s" % temp)
        return temp

    def add_history(self,tool_tip_text,s="",xm=0.,xc=0.,xp=0.,lx=0.,ym=0.,yc=0.,yp=0.,ly=0.,z=0.,d=0.):
#        c = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c = datetime.now().strftime('%H:%M:%S  ') + '{0: <10}'.format(tool_tip_text)  
        if "Xm" in s : 
            c += "X-=%.4f "%xm
        if "Xc" in s : 
            c += "Xc=%.4f "%xc
        if "Xp" in s : 
            c += "X+=%.4f "%xp
        if "Lx" in s : 
            c += "Lx=%.4f "%lx
        if "Ym" in s : 
            c += "Y-=%.4f "%ym
        if "Yc" in s : 
            c += "Yc=%.4f "%yc
        if "Yp" in s : 
            c += "Y+=%.4f "%yp
        if "Ly" in s : 
            c += "Ly=%.4f "%ly
        if "Z" in s : 
            c += "Z=%.4f "%z
        if "D" in s : 
            c += "D=%.4f"%d
        i=self.buffer.get_end_iter()
        i.set_line(0)
        self.buffer.insert(i, "%s \n" % c)


    # Set Zero check
    def on_chk_set_zero_toggled( self, gtkcheckbutton, data = None ):
        self.halcomp["set_zero"] = gtkcheckbutton.get_active()
        self.prefs.putpref( "chk_set_zero", gtkcheckbutton.get_active(), bool )
#        i=self.buffer.get_end_iter()
#        i.set_line(0)
#        self.buffer.insert(i, "Set Zero = %s\n" % gtkcheckbutton.get_active())

    def set_zerro(self,s="XYZ",x=0.,y=0.,z=0.):
        if self.chk_set_zero.get_active() :
            #  Z current position
            self.stat.poll()
            tmpz=self.stat.position[2]
            c = "G10 L20 P0"
            s=s.upper()
            if "X" in s :
                x+=self.spbtn_offs_x.get_value() 
                c += " X%s"%x
            if "Y" in s : 
                y+=self.spbtn_offs_y.get_value() 
                c += " Y%s"%y
            if "Z" in s :
                tmpz=tmpz-z+self.spbtn_offs_z.get_value() 
                c += " Z%s"%tmpz
            self.gcode(c)

    # Spin buttons

    def on_spbtn1_search_vel_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_searchvel"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_searchvel", gtkspinbutton.get_value(), float )

    def on_spbtn1_probe_vel_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_probevel"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_probevel", gtkspinbutton.get_value(), float )

    def on_spbtn1_probe_max_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_probe_max"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_probe_max", gtkspinbutton.get_value(), float )

    def on_spbtn1_probe_latch_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_probe_latch"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_probe_latch", gtkspinbutton.get_value(), float )

    def on_spbtn1_probe_diam_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_probe_diam"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_probe_diam", gtkspinbutton.get_value(), float )

    def on_spbtn1_xy_clearance_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_xy_clearance"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_xy_clearance", gtkspinbutton.get_value(), float )

    def on_spbtn1_edge_lenght_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_edge_lenght"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_edge_lenght", gtkspinbutton.get_value(), float )

    def on_spbtn1_z_clearance_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_z_clearance"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_z_clearance", gtkspinbutton.get_value(), float )

    def on_spbtn_offs_x_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_offs_x"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_offs_x", gtkspinbutton.get_value(), float )

    def on_spbtn_offs_y_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_offs_y"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_offs_y", gtkspinbutton.get_value(), float )

    def on_spbtn_offs_z_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["ps_offs_z"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_offs_z", gtkspinbutton.get_value(), float )

    def gcode(self,s, data = None): 
        for l in s.split("\n"):
            if "G1" in l :
                l+= " F#<_ini[TOOLSENSOR]RAPID_SPEED>"
            self.command.mdi( l )
            self.command.wait_complete()
            if self.error_poll() == -1:
                return -1
        return 0

    def ocode(self,s, data = None):	
        self.command.mdi(s)
        self.stat.poll()
        while self.stat.exec_state == 7 or self.stat.exec_state == 3 :
            if self.error_poll() == -1:
                return -1
            self.command.wait_complete()
            self.stat.poll()
        self.command.wait_complete()
        if self.error_poll() == -1:
            return -1
        return 0

    def z_clearance_down(self, data = None):
        # move Z - z_clearance
        s="""G91
        G1 Z-%f
        G90""" % (self.spbtn1_z_clearance.get_value() )        
        if self.gcode(s) == -1:
            return -1
        return 0

    def z_clearance_up(self, data = None):
        # move Z + z_clearance
        s="""G91
        G1 Z%f
        G90""" % (self.spbtn1_z_clearance.get_value() )        
        if self.gcode(s) == -1:
            return -1
        return 0

    def lenght_x(self, data = None):
        res=0
        if self.lb_probe_xm.get_text() == "" or self.lb_probe_xp.get_text() == "" :
            return res
        xm = float(self.lb_probe_xm.get_text())
        xp = float(self.lb_probe_xp.get_text())
        if xm < xp :
            res=xp-xm
        else:
            res=xm-xp
        self.lb_probe_lx.set_text("%.4f" % res)
        return res

    def lenght_y(self, data = None):
        res=0
        if self.lb_probe_ym.get_text() == "" or self.lb_probe_yp.get_text() == "" :
            return res
        ym = float(self.lb_probe_ym.get_text())
        yp = float(self.lb_probe_yp.get_text())
        if ym < yp :
            res=yp-ym
        else:
            res=ym-yp
        self.lb_probe_ly.set_text("%.4f" % res)
        return res

    # Simulate
#    def on_simulate_pressed(self, data = None):
#        self.halcomp["ps_simulate"] = 0
#    def on_simulate_released(self, data = None):
#        self.halcomp["ps_simulate"] = 1

    # --------------  Touch off buttons -----------------
    def on_btn1_set_x_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        self.command.mdi( "G10 L20 P0 X%f" % self.spbtn_offs_x.get_value() )
        self.command.wait_complete()
        self.prefs.putpref( "ps_offs_x", self.spbtn_offs_x.get_value(), float )

    def on_btn1_set_y_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        self.command.mdi( "G10 L20 P0 Y%f" % self.spbtn_offs_y.get_value() )
        self.command.wait_complete()
        self.prefs.putpref( "ps_offs_y", self.spbtn_offs_y.get_value(), float )

    def on_btn1_set_z_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        self.command.mdi( "G10 L20 P0 Z%f" % self.spbtn_offs_z.get_value() )
        self.command.wait_complete()
        self.prefs.putpref( "ps_offs_z", self.spbtn_offs_z.get_value(), float )


       
    # --------------  Command buttons -----------------
    #               Measurement outside
    # -------------------------------------------------
    # Down
    def on_down_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # Start down.ngc
        if self.ocode ("O<down> call") == -1:
            return
        a=self.stat.probed_position
        self.lb_probe_z.set_text( "%.4f" % float(a[2]) )
        self.add_history(gtkbutton.get_tooltip_text(),"Z",0,0,0,0,0,0,0,0,a[2],0)
        self.set_zerro("Z",0,0,a[2])
    # X+
    def on_xp_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
         # move X - xy_clearance
        s="""G91
        G1 X-%f
        G90""" % (self.spbtn1_xy_clearance.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
       # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        a=self.stat.probed_position
        res=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % res )
        self.add_history(gtkbutton.get_tooltip_text(),"XpLx",0,0,res,self.lenght_x(),0,0,0,0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f" % res)
        self.command.wait_complete()
        self.set_zerro("X")

    # Y+
    def on_yp_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
         # move Y - xy_clearance
        s="""G91
        G1 Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        a=self.stat.probed_position
        res=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % res )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"YpLy",0,0,0,0,0,0,res,self.lenght_y(),0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 Y%f" % res)
        self.command.wait_complete()
        self.set_zerro("Y")

    # X-
    def on_xm_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
         # move X + xy_clearance
        s="""G91
        G1 X%f
        G90""" % (self.spbtn1_xy_clearance.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        a=self.stat.probed_position
        res=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % res )
        self.add_history(gtkbutton.get_tooltip_text(),"XmLx",res,0,0,self.lenght_x(),0,0,0,0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f" % res)
        self.command.wait_complete()
        self.set_zerro("X")

    # Y-
    def on_ym_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
         # move Y + xy_clearance
        s="""G91
        G1 Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        a=self.stat.probed_position
        res=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % res )
        self.add_history(gtkbutton.get_tooltip_text(),"YmLy",0,0,0,0,res,0,0,self.lenght_y(),0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 Y%f" % res)
        self.command.wait_complete()
        self.set_zerro("Y")

    # Corners
    # Move Probe manual under corner 2-3 mm
    # X+Y+ 
    def on_xpyp_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X - xy_clearance Y + edge_lenght
        s="""G91
        G1 X-%f Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move X + edge_lenght +xy_clearance,  Y - edge_lenght - xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X%f Y-%f
        G90""" % (a,a)        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        yres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.add_history(gtkbutton.get_tooltip_text(),"XpLxYpLy",0,0,xres,self.lenght_x(),0,0,yres,self.lenght_y(),0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f Y%f" % (xres,yres))
        self.command.wait_complete()
        self.set_zerro("XY")

    # X+Y-
    def on_xpym_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X - xy_clearance Y + edge_lenght
        s="""G91
        G1 X-%f Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value(),self.spbtn1_edge_lenght.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move X + edge_lenght +xy_clearance,  Y + edge_lenght + xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X%f Y%f
        G90""" % (a,a)        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        yres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % yres )
        self.add_history(gtkbutton.get_tooltip_text(),"XpLxYmLy",0,0,xres,self.lenght_x(),yres,0,0,self.lenght_y(),0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f Y%f" % (xres,yres))
        self.command.wait_complete()
        self.set_zerro("XY")

    # X-Y+
    def on_xmyp_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X + xy_clearance Y + edge_lenght
        s="""G91
        G1 X%f Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value(),self.spbtn1_edge_lenght.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move X - edge_lenght - xy_clearance,  Y - edge_lenght - xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f Y-%f
        G90""" % (a,a)        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        yres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.add_history(gtkbutton.get_tooltip_text(),"XmLxYpLy",xres,0,0,self.lenght_x(),0,0,yres,self.lenght_y(),0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f Y%f" % (xres,yres))
        self.command.wait_complete()
        self.set_zerro("XY")

    # X-Y-
    def on_xmym_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X + xy_clearance Y - edge_lenght
        s="""G91
        G1 X%f Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move X - edge_lenght - xy_clearance,  Y + edge_lenght + xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f Y%f
        G90""" % (a,a)        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        yres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % yres )
        self.add_history(gtkbutton.get_tooltip_text(),"XmLxYmLy",xres,0,0,self.lenght_x(),yres,0,0,self.lenght_y(),0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f Y%f" % (xres,yres))
        self.command.wait_complete()
        self.set_zerro("XY")

    # Center X+ X- Y+ Y-
    def on_xy_center_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X - edge_lenght- xy_clearance
        s="""G91
        G1 X-%f
        G90""" % (self.spbtn1_edge_lenght.get_value() + self.spbtn1_xy_clearance.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xpres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xpres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move X + 2 edge_lenght + 2 xy_clearance
        aa=2*(self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value())
        s="""G91
        G1 X%f
        G90""" % (aa)        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xmres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xmres )
        xcres=0.5*(xpres+xmres)
        self.lb_probe_xc.set_text( "%.4f" % xcres )
        # distance to the new center of X from current position
        self.stat.poll()
        to_new_xc=self.stat.position[0]-xcres
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return


        # move Y - edge_lenght- xy_clearance  X - to_new_xc
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f Y-%f
        G90""" % (to_new_xc,a)
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        ypres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % ypres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move Y + 2 edge_lenght + 2 xy_clearance
        aa=2*(self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value())
        s="""G91
        G1 Y%f
        G90""" % (aa)        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        ymres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % ymres )
        self.lenght_y()
        # find, show and move to finded  point
        ycres=0.5*(ypres+ymres)
        self.lb_probe_yc.set_text( "%.4f" % ycres )
        diam=0.5*((xmres-xpres)+(ymres-ypres))
        self.lb_probe_d.set_text( "%.4f" % diam )
        self.add_history(gtkbutton.get_tooltip_text(),"XmXcXpLxYmYcYpLyD",xmres,xcres,xpres,self.lenght_x(),ymres,ycres,ypres,self.lenght_y(),0,diam)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f Y%f" % (xcres,ycres))
        self.command.wait_complete()
        self.set_zerro("XY")

    # --------------  Command buttons -----------------
    #               Measurement inside
    # -------------------------------------------------

    # Corners
    # Move Probe manual under corner 2-3 mm
    # X+Y+ 
    def on_xpyp1_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y - edge_lenght X - xy_clearance
        s="""G91
        G1 X-%f Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value(),self.spbtn1_edge_lenght.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xres )

        # move X - edge_lenght Y - xy_clearance
        tmpxy=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f Y%f
        G90""" % (tmpxy,tmpxy)        
        if self.gcode(s) == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        yres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.add_history(gtkbutton.get_tooltip_text(),"XpLxYpLy",0,0,xres,self.lenght_x(),0,0,yres,self.lenght_y(),0,0)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f Y%f" % (xres,yres))
        self.command.wait_complete()
        self.set_zerro("XY")

    # X+Y-
    def on_xpym1_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y + edge_lenght X - xy_clearance
        s="""G91
        G1 X-%f Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value(),self.spbtn1_edge_lenght.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xres )

        # move X - edge_lenght Y + xy_clearance
        tmpxy=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f Y-%f
        G90""" % (tmpxy,tmpxy)        
        if self.gcode(s) == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        yres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.add_history(gtkbutton.get_tooltip_text(),"XpLxYmLy",0,0,xres,self.lenght_x(),yres,0,0,self.lenght_y(),0,0)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f Y%f" % (xres,yres))
        self.command.wait_complete()
        self.set_zerro("XY")

    # X-Y+
    def on_xmyp1_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y - edge_lenght X + xy_clearance
        s="""G91
        G1 X%f Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value(),self.spbtn1_edge_lenght.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xres )

        # move X + edge_lenght Y - xy_clearance
        tmpxy=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X%f Y%f
        G90""" % (tmpxy,tmpxy)        
        if self.gcode(s) == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return

        # show Y result
        a=self.stat.probed_position
        yres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.add_history(gtkbutton.get_tooltip_text(),"XmLxYpLy",xres,0,0,self.lenght_x(),0,0,yres,self.lenght_y(),0,0)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f Y%f" % (xres,yres))
        self.command.wait_complete()
        self.set_zerro("XY")

    # X-Y-
    def on_xmym1_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y + edge_lenght X + xy_clearance
        s="""G91
        G1 X%f Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value(),self.spbtn1_edge_lenght.get_value() )        
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xres )

        # move X + edge_lenght Y - xy_clearance
        tmpxy=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X%f Y-%f
        G90""" % (tmpxy,tmpxy)        
        if self.gcode(s) == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        yres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.add_history(gtkbutton.get_tooltip_text(),"XmLxYmLy",xres,0,0,self.lenght_x(),yres,0,0,self.lenght_y(),0,0)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        self.command.mdi( "G1 X%f Y%f" % (xres,yres))
        self.command.wait_complete()
        self.set_zerro("XY")

    # Hole Xin- Xin+ Yin- Yin+
    def on_xy_hole_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        if self.z_clearance_down() == -1:
            return
        # move X - edge_lenght Y + xy_clearance
        tmpx=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f
        G90""" % (tmpx)        
        if self.gcode(s) == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xmres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xmres )

        # move X +2 edge_lenght - 2 xy_clearance
        tmpx=2*(self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value())
        s="""G91
        G1 X%f
        G90""" % (tmpx)        
        if self.gcode(s) == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.stat.probed_position
        xpres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xpres )
        xcres=0.5*(xmres+xpres)
        self.lb_probe_xc.set_text( "%.4f" % xcres )

        # move X to new center
        s="""G1 X%f""" % (xcres)        
        if self.gcode(s) == -1:
            return

        # move Y - edge_lenght + xy_clearance
        tmpy=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 Y-%f
        G90""" % (tmpy)        
        if self.gcode(s) == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        ymres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % ymres )

        # move Y +2 edge_lenght - 2 xy_clearance
        tmpy=2*(self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value())
        s="""G91
        G1 Y%f
        G90""" % (tmpy)        
        if self.gcode(s) == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.stat.probed_position
        ypres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % ypres )
        # find, show and move to finded  point
        ycres=0.5*(ymres+ypres)
        self.lb_probe_yc.set_text( "%.4f" % ycres )
        diam=0.5*((xpres-xmres)+(ypres-ymres))
        self.lb_probe_d.set_text( "%.4f" % diam )
        self.add_history(gtkbutton.get_tooltip_text(),"XmXcXpLxYmYcYpLyD",xmres,xcres,xpres,self.lenght_x(),ymres,ycres,ypres,self.lenght_y(),0,diam)
        # move to center
        self.command.mdi( "G1 Y%f" % ycres)
        self.command.wait_complete()
        # move Z to start point
        self.z_clearance_up()
        self.set_zerro("XY")


    def __init__(self, halcomp,builder,useropts):
        inipath = os.environ["INI_FILE_NAME"]
        self.inifile = ini(inipath)
        if not self.inifile:
            print("**** probe_screen GETINIINFO **** \n Error, no INI File given !!")
            sys.exit()
        self.command = linuxcnc.command()
        self.stat = linuxcnc.stat()
        self.builder = builder
        self.prefs = ps_preferences( self.get_preference_file_path() )
        self.e = linuxcnc.error_channel()
        self.textarea = builder.get_object("textview1")

        self.buffer = self.textarea.get_property('buffer')
        self.chk_set_zero = self.builder.get_object("chk_set_zero")
        self.chk_set_zero.set_active( self.prefs.getpref( "chk_set_zero", False, bool ) )
        self.xpym = self.builder.get_object("xpym")
        self.ym = self.builder.get_object("ym")
        self.xmym = self.builder.get_object("xmym")
        self.xp = self.builder.get_object("xp")
        self.center = self.builder.get_object("center")
        self.xm = self.builder.get_object("xm")
        self.xpyp = self.builder.get_object("xpyp")
        self.yp = self.builder.get_object("yp")
        self.xmyp = self.builder.get_object("xmyp")
        self.down = self.builder.get_object("down")
        self.hole = self.builder.get_object("hole")
        self.angle = self.builder.get_object("angle")

        self.spbtn1_search_vel = self.builder.get_object("spbtn1_search_vel")
        self.spbtn1_probe_vel = self.builder.get_object("spbtn1_probe_vel")
        self.spbtn1_z_clearance = self.builder.get_object("spbtn1_z_clearance")
        self.spbtn1_probe_max = self.builder.get_object("spbtn1_probe_max")
        self.spbtn1_probe_latch = self.builder.get_object("spbtn1_probe_latch")
        self.spbtn1_probe_diam = self.builder.get_object("spbtn1_probe_diam")
        self.spbtn1_xy_clearance = self.builder.get_object("spbtn1_xy_clearance")
        self.spbtn1_edge_lenght = self.builder.get_object("spbtn1_edge_lenght")

        self.spbtn_offs_x = self.builder.get_object("spbtn_offs_x")
        self.spbtn_offs_y = self.builder.get_object("spbtn_offs_y")
        self.spbtn_offs_z = self.builder.get_object("spbtn_offs_z")

        self.lb_probe_xp = self.builder.get_object("lb_probe_xp")
        self.lb_probe_yp = self.builder.get_object("lb_probe_yp")
        self.lb_probe_xm = self.builder.get_object("lb_probe_xm")
        self.lb_probe_ym = self.builder.get_object("lb_probe_ym")
        self.lb_probe_lx = self.builder.get_object("lb_probe_lx")
        self.lb_probe_ly = self.builder.get_object("lb_probe_ly")
        self.lb_probe_z = self.builder.get_object("lb_probe_z")
        self.lb_probe_d = self.builder.get_object("lb_probe_d")
        self.lb_probe_xc = self.builder.get_object("lb_probe_xc")
        self.lb_probe_yc = self.builder.get_object("lb_probe_yc")
        self.lb_probe_a = self.builder.get_object("lb_probe_a")


        self.halcomp = hal.component("probe")
        self.halcomp.newpin( "ps_searchvel", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_probevel", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_z_clearance", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_probe_max", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_probe_latch", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_probe_diam", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_xy_clearance", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_edge_lenght", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_offs_x", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_offs_y", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "ps_offs_z", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "set_zero", hal.HAL_BIT, hal.HAL_OUT )
        if self.chk_set_zero.get_active():
            self.halcomp["set_zero"] = True
#        self.halcomp.newpin( "ps_simulate", hal.HAL_BIT, hal.HAL_OUT )
        self.spbtn1_search_vel.set_value( self.prefs.getpref( "ps_searchvel", 300.0, float ) )
        self.spbtn1_probe_vel.set_value( self.prefs.getpref( "ps_probevel", 10.0, float ) )
        self.spbtn1_z_clearance.set_value( self.prefs.getpref( "ps_z_clearance", 3.0, float ) )
        self.spbtn1_probe_max.set_value( self.prefs.getpref( "ps_probe_max", 1.0, float ) )
        self.spbtn1_probe_latch.set_value( self.prefs.getpref( "ps_probe_latch", 0.5, float ) )
        self.spbtn1_probe_diam.set_value( self.prefs.getpref( "ps_probe_diam", 2.0, float ) )
        self.spbtn1_xy_clearance.set_value( self.prefs.getpref( "ps_xy_clearance", 5.0, float ) )
        self.spbtn1_edge_lenght.set_value( self.prefs.getpref( "ps_edge_lenght", 5.0, float ) )

        self.spbtn_offs_x.set_value( self.prefs.getpref( "ps_offs_x", 0.0, float ) )
        self.spbtn_offs_y.set_value( self.prefs.getpref( "ps_offs_x", 0.0, float ) )
        self.spbtn_offs_z.set_value( self.prefs.getpref( "ps_offs_x", 0.0, float ) )

        self.halcomp["ps_searchvel"] = self.spbtn1_search_vel.get_value()
        self.halcomp["ps_probevel"] = self.spbtn1_probe_vel.get_value()
        self.halcomp["ps_z_clearance"] = self.spbtn1_z_clearance.get_value()
        self.halcomp["ps_probe_max"] = self.spbtn1_probe_max.get_value()
        self.halcomp["ps_probe_latch"] = self.spbtn1_probe_latch.get_value()
        self.halcomp["ps_probe_diam"] = self.spbtn1_probe_diam.get_value()
        self.halcomp["ps_xy_clearance"] = self.spbtn1_xy_clearance.get_value()
        self.halcomp["ps_edge_lenght"] = self.spbtn1_edge_lenght.get_value()
        self.halcomp["ps_offs_x"] = self.spbtn_offs_x.get_value()
        self.halcomp["ps_offs_y"] = self.spbtn_offs_y.get_value()
        self.halcomp["ps_offs_z"] = self.spbtn_offs_z.get_value()
#        self.halcomp["ps_simulate"] = 1



def get_handlers(halcomp,builder,useropts):
    return [ProbeScreenClass(halcomp,builder,useropts)]
