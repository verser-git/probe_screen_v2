#!/usr/bin/env python
#
# Copyright (c) 2015 Serguei Glavatski ( verser  from cnc-club.ru )
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any laforter version.
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
import time
import math
from linuxcnc import ini
import ConfigParser
from datetime import datetime
from subprocess import Popen, PIPE

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

    def get_display(self):
        # gmoccapy or axis ?
        temp = self.inifile.find("DISPLAY", "DISPLAY")
        if not temp:
            print("****  PROBE SCREEN GET INI INFO **** \n Error recognition of display type : %s" % temp)
        return temp

    def add_history(self,tool_tip_text,s="",xm=0.,xc=0.,xp=0.,lx=0.,ym=0.,yc=0.,yp=0.,ly=0.,z=0.,d=0.,a=0.):
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
        if "A" in s :
            c += "Angle=%.3f"%a
        i=self.buffer.get_end_iter()
        if i.get_line() > 1000 :
            i.backward_line()
            self.buffer.delete(i,self.buffer.get_end_iter())
        i.set_line(0)
        self.buffer.insert(i, "%s \n" % c)

    def error_poll(self):
        error = self.e.poll()
        if "axis" in self.display:
            error_pin= Popen('halcmd getp probe.user.error ', shell=True, stdout=PIPE).stdout.read()
        else:
            error_pin= Popen('halcmd getp gmoccapy.error ', shell=True, stdout=PIPE).stdout.read()
        if error:
            self.command.mode( linuxcnc.MODE_MANUAL )
            self.command.wait_complete()
            kind, text = error
            self.add_history("Error: %s" % text, "", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            if kind in (linuxcnc.NML_ERROR, linuxcnc.OPERATOR_ERROR):

                typus = "error"
                print typus, text
                return -1
            else:
                typus = "info"
                print typus, text
                return -1
        else:
            if "TRUE" in error_pin:
                text = "User probe error"
                self.add_history("Error: %s" % text, "", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                typus = "error"
                print typus, text
                self.command.mode( linuxcnc.MODE_MANUAL )
                self.command.wait_complete()
                return -1

        return 0



    # calculate corner coordinates in rotated coord. system
    def calc_cross_rott(self,x1=0.,y1=0.,x2=0.,y2=0.,a1=0.,a2=90.) :
        coord = [0,0]
        k1=math.tan(math.radians(a1))
        k2=math.tan(math.radians(a2))
        coord[0]=(k1*x1-k2*x2+y2-y1)/(k1-k2)
        coord[1]=k1*(coord[0]-x1)+y1
        return coord

    # rotate point coordinates
    def rott_point(self,x1=0.,y1=0.,a1=0.) :
        coord = [x1,y1]
        if a1 != 0:
            if self.chk_set_zero.get_active() :
                xc = self.spbtn_offs_x.get_value()
                yc = self.spbtn_offs_y.get_value()
            else :
                self.stat.poll()
                xc=self.stat.position[0]-self.stat.g5x_offset[0] - self.stat.g92_offset[0] - self.stat.tool_offset[0]
                yc=self.stat.position[1]-self.stat.g5x_offset[1] - self.stat.g92_offset[1] - self.stat.tool_offset[1]
            t = math.radians(a1)
            coord[0] = (x1-xc) * math.cos(t) - (y1-yc) * math.sin(t) + xc
            coord[1] = (x1-xc) * math.sin(t) + (y1-yc) * math.cos(t) + yc
        return coord

    # rotate around 0,0 point coordinates
    def rott00_point(self,x1=0.,y1=0.,a1=0.) :
        coord = [x1,y1]
        if a1 != 0:
            t = math.radians(a1)
            coord[0] = x1 * math.cos(t) - y1 * math.sin(t)
            coord[1] = x1 * math.sin(t) + y1 * math.cos(t)
        return coord

    def probed_position_with_offsets(self) :
        self.stat.poll()
        probed_position=list(self.stat.probed_position)
        coord=list(self.stat.probed_position)
        g5x_offset=list(self.stat.g5x_offset)
        g92_offset=list(self.stat.g92_offset)
        tool_offset=list(self.stat.tool_offset)
#        print "g5x_offset=",g5x_offset
#        print "g92_offset=",g92_offset
#        print "tool_offset=",tool_offset
#        print "actual position=",self.stat.actual_position
#        print "position=",self.stat.position
#        print "joint_actual position=",self.stat.joint_actual_position
#        print "joint_position=",self.stat.joint_position
#        print "probed position=",self.stat.probed_position
        for i in range(0, len(probed_position)-1):
             coord[i] = probed_position[i] - g5x_offset[i] - g92_offset[i] - tool_offset[i]
        angl=self.stat.rotation_xy
        res=self.rott00_point(coord[0],coord[1],-angl)
        coord[0]=res[0]
        coord[1]=res[1]
        return coord

    # Set Zero check
    def on_chk_set_zero_toggled( self, gtkcheckbutton, data = None ):
        self.halcomp["set_zero"] = gtkcheckbutton.get_active()
        self.hal_led_set_zero.hal_pin.set(gtkcheckbutton.get_active())
        self.prefs.putpref( "chk_set_zero", gtkcheckbutton.get_active(), bool )

    # Auto Rot check
    def on_chk_auto_rott_toggled( self, gtkcheckbutton, data = None ):
        self.halcomp["auto_rott"] = gtkcheckbutton.get_active()
        self.hal_led_auto_rott.hal_pin.set(gtkcheckbutton.get_active())
        self.prefs.putpref( "chk_auto_rott", gtkcheckbutton.get_active(), bool )


    def set_zerro(self,s="XYZ",x=0.,y=0.,z=0.):
        if self.chk_set_zero.get_active() :
            #  Z current position
            self.stat.poll()
            tmpz=self.stat.position[2]-self.stat.g5x_offset[2] - self.stat.g92_offset[2] - self.stat.tool_offset[2]
            c = "G10 L20 P0"
            s=s.upper()
            if "X" in s :
                x += self.spbtn_offs_x.get_value()
                c += " X%s"%x
            if "Y" in s :
                y += self.spbtn_offs_y.get_value()
                c += " Y%s"%y
            if "Z" in s :
                tmpz = tmpz - z + self.spbtn_offs_z.get_value()
                c += " Z%s"%tmpz
            self.gcode(c)
            time.sleep(1)

    def rotate_coord_system(self,a=0.):
        self.spbtn_offs_angle.set_value(a)
        self.lb_probe_a.set_text( "%.3f" % a)
        if self.chk_auto_rott.get_active() :
            s="G10 L2 P0"
            if self.chk_set_zero.get_active() :
                s += " X%s" % self.spbtn_offs_x.get_value()
                s += " Y%s" % self.spbtn_offs_y.get_value()
            else :
                self.stat.poll()
                x=self.stat.position[0]
                y=self.stat.position[1]
                s += " X%s" % x
                s += " Y%s" % y
            s += " R%s" % a
            self.gcode(s)
            time.sleep(1)



    # -----------
    # JOG BUTTONS
    # -----------
    def _init_jog_increments( self ):
        # Get the increments from INI File
        jog_increments = []
        increments = self.inifile.find("DISPLAY", "INCREMENTS")
        if increments:
            if "," in increments:
                for i in increments.split(","):
                    jog_increments.append(i.strip())
            else:
                jog_increments = increments.split()
            jog_increments.insert(0, 0)
        else:
            jog_increments = [0, "1,000", "0,100", "0,010", "0,001"]
            print("**** PROBE SCREEN INFO **** \n No default jog increments entry found in [DISPLAY] of INI file")

        self.jog_increments = jog_increments
        if len( self.jog_increments ) > 5:
            print( _( "**** PROBE SCREEN INFO ****" ) )
            print( _( "**** To many increments given in INI File for this screen ****" ) )
            print( _( "**** Only the first 5 will be reachable through this screen ****" ) )
            # we shorten the incrementlist to 5 (first is default = 0)
            self.jog_increments = self.jog_increments[0:5]

        # The first radio button is created to get a radio button group
        # The group is called according the name off  the first button
        # We use the pressed signal, not the toggled, otherwise two signals will be emitted
        # One from the released button and one from the pressed button
        # we make a list of the buttons to later add the hardware pins to them
        label = "Cont"
        rbt0 = gtk.RadioButton( None, label )
        rbt0.connect( "pressed", self.on_increment_changed, 0 )
        self.steps.pack_start( rbt0, True, True, 0 )
        rbt0.set_property( "draw_indicator", False )
        rbt0.show()
        rbt0.modify_bg( gtk.STATE_ACTIVE, gtk.gdk.color_parse( "#FFFF00" ) )
        rbt0.__name__ = "rbt0"
        self.incr_rbt_list.append( rbt0 )
        # the rest of the buttons are now added to the group
        # self.no_increments is set while setting the hal pins with self._check_len_increments
        for item in range( 1, len( self.jog_increments ) ):
            rbt = "rbt%d" % ( item )
            rbt = gtk.RadioButton( rbt0, self.jog_increments[item] )
            rbt.connect( "pressed", self.on_increment_changed, self.jog_increments[item] )
            self.steps.pack_start( rbt, True, True, 0 )
            rbt.set_property( "draw_indicator", False )
            rbt.show()
            rbt.modify_bg( gtk.STATE_ACTIVE, gtk.gdk.color_parse( "#FFFF00" ) )
            rbt.__name__ = "rbt%d" % ( item )
            self.incr_rbt_list.append( rbt )
        self.active_increment = "rbt0"

    # This is the jogging part
    def on_increment_changed( self, widget = None, data = None ):
        if data == 0:
            self.distance = 0
        else:
            self.distance = self._parse_increment( data )
        self.halcomp["jog-increment"] = self.distance
        self.active_increment = widget.__name__

    def _from_internal_linear_unit( self, v, unit = None ):
        if unit is None:
            unit = self.stat.linear_units
        lu = ( unit or 1 ) * 25.4
        return v * lu

    def _parse_increment( self, jogincr ):
        if jogincr.endswith( "mm" ):
            scale = self._from_internal_linear_unit( 1 / 25.4 )
        elif jogincr.endswith( "cm" ):
            scale = self._from_internal_linear_unit( 10 / 25.4 )
        elif jogincr.endswith( "um" ):
            scale = self._from_internal_linear_unit( .001 / 25.4 )
        elif jogincr.endswith( "in" ) or jogincr.endswith( "inch" ):
            scale = self._from_internal_linear_unit( 1. )
        elif jogincr.endswith( "mil" ):
            scale = self._from_internal_linear_unit( .001 )
        else:
            scale = 1
        jogincr = jogincr.rstrip( " inchmuil" )
        if "/" in jogincr:
            p, q = jogincr.split( "/" )
            jogincr = float( p ) / float( q )
        else:
            jogincr = float( jogincr )
        return jogincr * scale

    def on_btn_jog_pressed( self, widget, data = None ):
        # only in manual mode we will allow jogging the axis at this development state
        self.command.mode( linuxcnc.MODE_MANUAL )
        self.command.wait_complete()
        self.stat.poll()
        if not self.stat.task_mode == linuxcnc.MODE_MANUAL:
            return

        axisletter = widget.get_label()[0]
        if not axisletter.lower() in "xyzabcuvw":
            print ( "unknown axis %s" % axisletter )
            return

        # get the axisnumber
        axisnumber = "xyzabcuvws".index( axisletter.lower() )

        # if data = True, then the user pressed SHIFT for Jogging and
        # want's to jog at 0.2 speed
        if data:
            value = 0.2
        else:
            value = 1

        velocity = float(self.inifile.find("TRAJ", "DEFAULT_VELOCITY"))

        dir = widget.get_label()[1]
        if dir == "+":
            direction = 1
        else:
            direction = -1

        if self.distance <> 0:  # incremental jogging
            self.command.jog( linuxcnc.JOG_INCREMENT, axisnumber, direction * velocity, self.distance )
        else:  # continuous jogging
            self.command.jog( linuxcnc.JOG_CONTINUOUS, axisnumber, direction * velocity )

    def on_btn_jog_released( self, widget, data = None ):
        axisletter = widget.get_label()[0]
        if not axisletter.lower() in "xyzabcuvw":
            print ( "unknown axis %s" % axisletter )
            return

        axis = "xyzabcuvw".index( axisletter.lower() )

        if self.distance <> 0:
            pass
        else:
            self.command.jog( linuxcnc.JOG_STOP, axis )


    # Spin  buttons

    def on_spbtn1_search_vel_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
#        print "Key %s (%d) was pressed" % (keyname, data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn1_probe_vel_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn1_probe_max_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))


    def on_spbtn1_probe_latch_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn1_probe_diam_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn1_xy_clearance_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn1_edge_lenght_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn1_z_clearance_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn_offs_x_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn_offs_y_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn_offs_z_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn_offs_angle_key_press_event( self, gtkspinbutton, data = None ):
        keyname = gtk.gdk.keyval_name(data.keyval)
        if keyname == "Return" :
            gtkspinbutton.modify_font(pango.FontDescription('normal'))
        else :
            gtkspinbutton.modify_font(pango.FontDescription('italic'))

    def on_spbtn1_search_vel_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal '))
        self.halcomp["ps_searchvel"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_searchvel", gtkspinbutton.get_value(), float )

    def on_spbtn1_probe_vel_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_probevel"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_probevel", gtkspinbutton.get_value(), float )

    def on_spbtn1_probe_max_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_probe_max"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_probe_max", gtkspinbutton.get_value(), float )

    def on_spbtn1_probe_latch_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_probe_latch"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_probe_latch", gtkspinbutton.get_value(), float )

    def on_spbtn1_probe_diam_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_probe_diam"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_probe_diam", gtkspinbutton.get_value(), float )

    def on_spbtn1_xy_clearance_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_xy_clearance"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_xy_clearance", gtkspinbutton.get_value(), float )

    def on_spbtn1_edge_lenght_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_edge_lenght"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_edge_lenght", gtkspinbutton.get_value(), float )

    def on_spbtn1_z_clearance_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_z_clearance"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_z_clearance", gtkspinbutton.get_value(), float )

    def on_spbtn_offs_x_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_offs_x"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_offs_x", gtkspinbutton.get_value(), float )

    def on_spbtn_offs_y_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_offs_y"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_offs_y", gtkspinbutton.get_value(), float )

    def on_spbtn_offs_z_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_offs_z"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_offs_z", gtkspinbutton.get_value(), float )

    def on_spbtn_offs_angle_value_changed( self, gtkspinbutton, data = None ):
        gtkspinbutton.modify_font(pango.FontDescription('normal'))
        self.halcomp["ps_offs_angle"] = gtkspinbutton.get_value()
        self.prefs.putpref( "ps_offs_angle", gtkspinbutton.get_value(), float )

    def gcode(self, s, data = None):
        for l in s.split("\n"):
            if "G1" in l :
                l+= " F#<_ini[TOOLSENSOR]RAPID_SPEED>"
            self.command.mdi( l )
            self.command.wait_complete()
            if self.error_poll() == -1:
                return -1
        return 0

    def ocode(self, s, data = None):
        self.command.mdi(s)
        self.stat.poll()
        while self.stat.interp_state != linuxcnc.INTERP_IDLE :
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
        G90""" % (self.spbtn1_z_clearance.get_value())
        if self.gcode(s) == -1:
            return -1
        return 0

    def z_clearance_up(self, data = None):
        # move Z + z_clearance
        s="""G91
        G1 Z%f
        G90""" % (self.spbtn1_z_clearance.get_value())
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

    # --------------  Touch off buttons -----------------
    def on_btn_set_x_released(self, gtkbutton, data = None):
        self.prefs.putpref( "ps_offs_x", self.spbtn_offs_x.get_value(), float )
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        self.command.mdi( "G10 L20 P0 X%f" % self.spbtn_offs_x.get_value() )
        self.vcp_action_reload.emit( "activate" )
        time.sleep(1)


    def on_btn_set_y_released(self, gtkbutton, data = None):
        self.prefs.putpref( "ps_offs_y", self.spbtn_offs_y.get_value(), float )
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        self.command.mdi( "G10 L20 P0 Y%f" % self.spbtn_offs_y.get_value() )
        self.vcp_action_reload.emit( "activate" )
        time.sleep(1)

    def on_btn_set_z_released(self, gtkbutton, data = None):
        self.prefs.putpref( "ps_offs_z", self.spbtn_offs_z.get_value(), float )
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        self.command.mdi( "G10 L20 P0 Z%f" % self.spbtn_offs_z.get_value() )
        self.vcp_action_reload.emit( "activate" )
        time.sleep(1)

    def on_btn_set_angle_released(self, gtkbutton, data = None):
        self.prefs.putpref( "ps_offs_angle", self.spbtn_offs_angle.get_value(), float )
        self.lb_probe_a.set_text( "%.3f" % self.spbtn_offs_angle.get_value())
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        s="G10 L2 P0"
        if self.chk_set_zero.get_active() :
            s += " X%.4f" % self.spbtn_offs_x.get_value()
            s += " Y%.4f" % self.spbtn_offs_y.get_value()
        else :
            self.stat.poll()
            x=self.stat.position[0]
            y=self.stat.position[1]
            s += " X%.4f" % x
            s += " Y%.4f" % y
        s +=  " R%.4f"%self.spbtn_offs_angle.get_value()
        print "s=", s
        self.gcode(s)
        time.sleep(1)



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
        a=self.probed_position_with_offsets()
        self.lb_probe_z.set_text( "%.4f" % float(a[2]) )
        self.add_history(gtkbutton.get_tooltip_text(),"Z",0,0,0,0,0,0,0,0,a[2],0,0)
        self.set_zerro("Z",0,0,a[2])
    # X+
    def on_xp_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
         # move X - xy_clearance
        s="""G91
        G1 X-%f
        G90""" % (self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
       # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        a=self.probed_position_with_offsets()
        xres=float(a[0]+0.5*self.spbtn1_probe_diam.get_value())
        self.lb_probe_xp.set_text( "%.4f" % xres )
        self.lenght_x()
        self.add_history(gtkbutton.get_tooltip_text(),"XpLx",0,0,xres,self.lenght_x(),0,0,0,0,0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f" % xres
        if self.gcode(s) == -1:
            return
        self.set_zerro("X")

    # Y+
    def on_yp_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
         # move Y - xy_clearance
        s="""G91
        G1 Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        a=self.probed_position_with_offsets()
        yres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"YpLy",0,0,0,0,0,0,yres,self.lenght_y(),0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 Y%f" % yres
        if self.gcode(s) == -1:
            return
        self.set_zerro("Y")

    # X-
    def on_xm_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
         # move X + xy_clearance
        s="""G91
        G1 X%f
        G90""" % (self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        a=self.probed_position_with_offsets()
        xres=float(a[0]-0.5*self.spbtn1_probe_diam.get_value())
        self.lb_probe_xm.set_text( "%.4f" % xres )
        self.lenght_x()
        self.add_history(gtkbutton.get_tooltip_text(),"XmLx",xres,0,0,self.lenght_x(),0,0,0,0,0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f" % xres
        if self.gcode(s) == -1:
            return
        self.set_zerro("X")

    # Y-
    def on_ym_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
         # move Y + xy_clearance
        s="""G91
        G1 Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        a=self.probed_position_with_offsets()
        yres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % yres )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"YmLy",0,0,0,0,yres,0,0,self.lenght_y(),0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 Y%f" % yres
        if self.gcode(s) == -1:
            return
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
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xres=float(a[0]+0.5*self.spbtn1_probe_diam.get_value())
        self.lb_probe_xp.set_text( "%.4f" % xres )
        self.lenght_x()
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move X + edge_lenght +xy_clearance,  Y - edge_lenght - xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X%f Y-%f
        G90""" % (a, a)
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        yres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"XpLxYpLy",0,0,xres,self.lenght_x(),0,0,yres,self.lenght_y(),0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f Y%f" % (xres,yres)
        if self.gcode(s) == -1:
            return
        self.set_zerro("XY")

    # X+Y-
    def on_xpym_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X - xy_clearance Y + edge_lenght
        s="""G91
        G1 X-%f Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xres=float(a[0]+0.5*self.spbtn1_probe_diam.get_value())
        self.lb_probe_xp.set_text( "%.4f" % xres )
        self.lenght_x()
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move X + edge_lenght +xy_clearance,  Y + edge_lenght + xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X%f Y%f
        G90""" % (a, a)
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        yres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % yres )
        self.add_history(gtkbutton.get_tooltip_text(),"XpLxYmLy",0,0,xres,self.lenght_x(),yres,0,0,self.lenght_y(),0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f Y%f" % (xres,yres)
        if self.gcode(s) == -1:
            return
        self.set_zerro("XY")

    # X-Y+
    def on_xmyp_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X + xy_clearance Y + edge_lenght
        s="""G91
        G1 X%f Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xres=float(a[0]-0.5*self.spbtn1_probe_diam.get_value())
        self.lb_probe_xm.set_text( "%.4f" % xres )
        self.lenght_x()
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move X - edge_lenght - xy_clearance,  Y - edge_lenght - xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f Y-%f
        G90""" % (a, a)
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        yres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"XmLxYpLy",xres,0,0,self.lenght_x(),0,0,yres,self.lenght_y(),0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f Y%f" % (xres,yres)
        if self.gcode(s) == -1:
            return
        self.set_zerro("XY")

    # X-Y-
    def on_xmym_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X + xy_clearance Y - edge_lenght
        s="""G91
        G1 X%f Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xres=float(a[0]-0.5*self.spbtn1_probe_diam.get_value())
        self.lb_probe_xm.set_text( "%.4f" % xres )
        self.lenght_x()
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return

        # move X - edge_lenght - xy_clearance,  Y + edge_lenght + xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f Y%f
        G90""" % (a, a)
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        yres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % yres )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"XmLxYmLy",xres,0,0,self.lenght_x(),yres,0,0,self.lenght_y(),0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f Y%f" % (xres,yres)
        if self.gcode(s) == -1:
            return
        self.set_zerro("XY")

    # Center X+ X- Y+ Y-
    def on_xy_center_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X - edge_lenght- xy_clearance
        s="""G91
        G1 X-%f
        G90""" % (self.spbtn1_edge_lenght.get_value() + self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
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
        a=self.probed_position_with_offsets()
        xmres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xmres )
        self.lenght_x()
        xcres=0.5*(xpres+xmres)
        self.lb_probe_xc.set_text( "%.4f" % xcres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # distance to the new center of X from current position
#        self.stat.poll()
#        to_new_xc=self.stat.position[0]-self.stat.g5x_offset[0] - self.stat.g92_offset[0] - self.stat.tool_offset[0] - xcres
        s = "G1 X%f" % xcres
        if self.gcode(s) == -1:
            return


        # move Y - edge_lenght- xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 Y-%f
        G90""" % a
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
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
        a=self.probed_position_with_offsets()
        ymres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % ymres )
        self.lenght_y()
        # find, show and move to finded  point
        ycres=0.5*(ypres+ymres)
        self.lb_probe_yc.set_text( "%.4f" % ycres )
        diam=ymres-ypres
        self.lb_probe_d.set_text( "%.4f" % diam )
        self.add_history(gtkbutton.get_tooltip_text(),"XmXcXpLxYmYcYpLyD",xmres,xcres,xpres,self.lenght_x(),ymres,ycres,ypres,self.lenght_y(),0,diam,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 Y%f" % ycres
        if self.gcode(s) == -1:
            return
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
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xres )
        self.lenght_x()

        # move X - edge_lenght Y - xy_clearance
        tmpxy=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f Y%f
        G90""" % (tmpxy, tmpxy)
        if self.gcode(s) == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        yres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"XpLxYpLy",0,0,xres,self.lenght_x(),0,0,yres,self.lenght_y(),0,0,0)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f Y%f" % (xres,yres)
        if self.gcode(s) == -1:
            return
        self.set_zerro("XY")

    # X+Y-
    def on_xpym1_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y + edge_lenght X - xy_clearance
        s="""G91
        G1 X-%f Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xres )
        self.lenght_x()

        # move X - edge_lenght Y + xy_clearance
        tmpxy=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X-%f Y-%f
        G90""" % (tmpxy, tmpxy)
        if self.gcode(s) == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        yres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % yres )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"XpLxYmLy",0,0,xres,self.lenght_x(),yres,0,0,self.lenght_y(),0,0,0)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f Y%f" % (xres,yres)
        if self.gcode(s) == -1:
            return
        self.set_zerro("XY")

    # X-Y+
    def on_xmyp1_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y - edge_lenght X + xy_clearance
        s="""G91
        G1 X%f Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xres )
        self.lenght_x()

        # move X + edge_lenght Y - xy_clearance
        tmpxy=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X%f Y%f
        G90""" % (tmpxy, tmpxy)
        if self.gcode(s) == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return

        # show Y result
        a=self.probed_position_with_offsets()
        yres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % yres )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"XmLxYpLy",xres,0,0,self.lenght_x(),0,0,yres,self.lenght_y(),0,0,0)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f Y%f" % (xres,yres)
        if self.gcode(s) == -1:
            return
        self.set_zerro("XY")

    # X-Y-
    def on_xmym1_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y + edge_lenght X + xy_clearance
        s="""G91
        G1 X%f Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value(), self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xres )
        self.lenght_x()

        # move X + edge_lenght Y - xy_clearance
        tmpxy=self.spbtn1_edge_lenght.get_value()-self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 X%f Y-%f
        G90""" % (tmpxy, tmpxy)
        if self.gcode(s) == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        yres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % yres )
        self.lenght_y()
        self.add_history(gtkbutton.get_tooltip_text(),"XmLxYmLy",xres,0,0,self.lenght_x(),yres,0,0,self.lenght_y(),0,0,0)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 X%f Y%f" % (xres,yres)
        if self.gcode(s) == -1:
            return
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
        a=self.probed_position_with_offsets()
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
        a=self.probed_position_with_offsets()
        xpres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xpres )
        self.lenght_x()
        xcres=0.5*(xmres+xpres)
        self.lb_probe_xc.set_text( "%.4f" % xcres )

        # move X to new center
        s = """G1 X%f""" % (xcres)
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
        a=self.probed_position_with_offsets()
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
        a=self.probed_position_with_offsets()
        ypres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % ypres )
        self.lenght_y()
        # find, show and move to finded  point
        ycres=0.5*(ymres+ypres)
        self.lb_probe_yc.set_text( "%.4f" % ycres )
        diam=0.5*((xpres-xmres)+(ypres-ymres))
        self.lb_probe_d.set_text( "%.4f" % diam )
        self.add_history(gtkbutton.get_tooltip_text(),"XmXcXpLxYmYcYpLyD",xmres,xcres,xpres,self.lenght_x(),ymres,ycres,ypres,self.lenght_y(),0,diam,0)
        # move to center
        s = "G1 Y%f" % ycres
        if self.gcode(s) == -1:
            return
        # move Z to start point
        self.z_clearance_up()
        self.set_zerro("XY")

    # --------------  Command buttons -----------------
    #               Measurement angle
    # -------------------------------------------------

    # Angle
    # Move Probe manual under corner 2-3 mm
    # Y+Y+
    def on_angle_yp_released(self, gtkbutton, data = None):
        self.stat.poll()
        xstart=self.stat.position[0]-self.stat.g5x_offset[0] - self.stat.g92_offset[0] - self.stat.tool_offset[0]
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y - xy_clearance
        s="""G91
        G1 Y-%f
        G90""" % (self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        ycres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yc.set_text( "%.4f" % ycres )
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move X + edge_lenght
        s="""G91
        G1 X%f
        G90""" % (self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        ypres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % ypres )
        alfa=math.degrees(math.atan2(ypres-ycres,self.spbtn1_edge_lenght.get_value()))
        self.add_history(gtkbutton.get_tooltip_text(),"YcYpA",0,0,0,0,0,ycres,ypres,0,0,0,alfa)

        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move XY to adj start point
        s="G1 X%f Y%f" % (xstart,ycres)
        if self.gcode(s) == -1:
            return
        self.rotate_coord_system(alfa)

    # Y-Y-
    def on_angle_ym_released(self, gtkbutton, data = None):
        self.stat.poll()
        xstart=self.stat.position[0]-self.stat.g5x_offset[0] - self.stat.g92_offset[0] - self.stat.tool_offset[0]
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y + xy_clearance
        s="""G91
        G1 Y%f
        G90""" % (self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        ycres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yc.set_text( "%.4f" % ycres )
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move X - edge_lenght
        s="""G91
        G1 X-%f
        G90""" % (self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yminus.ngc
        if self.ocode ("O<yminus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        ymres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % ymres )
        alfa=math.degrees(math.atan2(ycres-ymres,self.spbtn1_edge_lenght.get_value()))
        self.add_history(gtkbutton.get_tooltip_text(),"YmYcA",0,0,0,0,ymres,ycres,0,0,0,0,alfa)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move XY to adj start point
        s="G1 X%f Y%f" % (xstart,ycres)
        if self.gcode(s) == -1:
            return
        self.rotate_coord_system(alfa)

    # X+X+
    def on_angle_xp_released(self, gtkbutton, data = None):
        self.stat.poll()
        ystart=self.stat.position[1]-self.stat.g5x_offset[1] - self.stat.g92_offset[1] - self.stat.tool_offset[1]
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X - xy_clearance
        s="""G91
        G1 X-%f
        G90""" % (self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xcres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xc.set_text( "%.4f" % xcres )
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move Y - edge_lenght
        s="""G91
        G1 Y-%f
        G90""" % (self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xpres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xpres )
        alfa=math.degrees(math.atan2(xcres-xpres,self.spbtn1_edge_lenght.get_value()))
        self.add_history(gtkbutton.get_tooltip_text(),"XcXpA",0,xcres,xpres,0,0,0,0,0,0,0,alfa)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move XY to adj start point
        s="G1 X%f Y%f" % (xcres,ystart)
        if self.gcode(s) == -1:
            return
        self.rotate_coord_system(alfa)

    # X-X-
    def on_angle_xm_released(self, gtkbutton, data = None):
        self.stat.poll()
        ystart=self.stat.position[1]-self.stat.g5x_offset[1] - self.stat.g92_offset[1] - self.stat.tool_offset[1]
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X + xy_clearance
        s="""G91
        G1 X%f
        G90""" % (self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xcres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xc.set_text( "%.4f" % xcres )
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move Y + edge_lenght
        s="""G91
        G1 Y%f
        G90""" % (self.spbtn1_edge_lenght.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xminus.ngc
        if self.ocode ("O<xminus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xmres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xmres )
        alfa=math.degrees(math.atan2(xcres-xmres,self.spbtn1_edge_lenght.get_value()))
        self.add_history(gtkbutton.get_tooltip_text(),"XmXcA",xmres,xcres,0,0,0,0,0,0,0,0,alfa)
        # move Z to start point
        if self.z_clearance_up() == -1:
            return
        # move XY to adj start point
        s="G1 X%f Y%f" % (xcres,ystart)
        if self.gcode(s) == -1:
            return
        self.rotate_coord_system(alfa)

    # Lx OUT
    def on_lx_out_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move X - edge_lenght- xy_clearance
        s="""G91
        G1 X-%f
        G90""" % (self.spbtn1_edge_lenght.get_value() + self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xpres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xpres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point X
        s = "G1 X%f" % xpres
        if self.gcode(s) == -1:
            return

        # move X + 2 edge_lenght +  xy_clearance
        aa=2*self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
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
        a=self.probed_position_with_offsets()
        xmres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xm.set_text( "%.4f" % xmres )
        self.lenght_x()
        xcres=0.5*(xpres+xmres)
        self.lb_probe_xc.set_text( "%.4f" % xcres )
        self.add_history(gtkbutton.get_tooltip_text(),"XmXcXpLx",xmres,xcres,xpres,self.lenght_x(),0,0,0,0,0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # go to the new center of X
        s = "G1 X%f" % xcres
        if self.gcode(s) == -1:
            return
        self.set_zerro("XY")


    # Ly OUT
    def on_ly_out_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move Y - edge_lenght- xy_clearance
        a=self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 Y-%f
        G90""" % a
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        ypres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % ypres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point Y
        s = "G1 Y%f" % ypres
        if self.gcode(s) == -1:
            return

        # move Y + 2 edge_lenght +  xy_clearance
        aa=2*self.spbtn1_edge_lenght.get_value()+self.spbtn1_xy_clearance.get_value()
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
        a=self.probed_position_with_offsets()
        ymres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_ym.set_text( "%.4f" % ymres )
        self.lenght_y()
        # find, show and move to finded  point
        ycres=0.5*(ypres+ymres)
        self.lb_probe_yc.set_text( "%.4f" % ycres )
        self.add_history(gtkbutton.get_tooltip_text(),"YmYcYpLy",0,0,0,0,ymres,ycres,ypres,self.lenght_y(),0,0,0)
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point
        s = "G1 Y%f" % ycres
        if self.gcode(s) == -1:
            return
        self.set_zerro("XY")


    # Lx IN
    def on_lx_in_released(self, gtkbutton, data = None):
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
        a=self.probed_position_with_offsets()
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
        a=self.probed_position_with_offsets()
        xpres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_xp.set_text( "%.4f" % xpres )
        self.lenght_x()
        xcres=0.5*(xmres+xpres)
        self.lb_probe_xc.set_text( "%.4f" % xcres )
        self.add_history(gtkbutton.get_tooltip_text(),"XmXcXpLx",xmres,xcres,xpres,self.lenght_x(),0,0,0,0,0,0,0)
        # move X to new center
        s = """G1 X%f""" % (xcres)
        if self.gcode(s) == -1:
            return
        # move Z to start point
        self.z_clearance_up()
        self.set_zerro("XY")


    # Ly IN
    def on_ly_in_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        if self.z_clearance_down() == -1:
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
        a=self.probed_position_with_offsets()
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
        a=self.probed_position_with_offsets()
        ypres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
        self.lb_probe_yp.set_text( "%.4f" % ypres )
        self.lenght_y()
        # find, show and move to finded  point
        ycres=0.5*(ymres+ypres)
        self.lb_probe_yc.set_text( "%.4f" % ycres )
        self.add_history(gtkbutton.get_tooltip_text(),"YmYcYpLy",0,0,0,0,ymres,ycres,ypres,self.lenght_y(),0,0,0)
        # move to center
        s = "G1 Y%f" % ycres
        if self.gcode(s) == -1:
            return
        # move Z to start point
        self.z_clearance_up()
        self.set_zerro("XY")


    # TOOL DIA
    def on_tool_dia_released(self, gtkbutton, data = None):
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        # move XY to Tool Setter point
        # Start gotots.ngc
        if self.ocode ("O<gotots> call") == -1:
            return
        # move X - edge_lenght- xy_clearance
        s="""G91
        G1 X-%f
        G90""" % (0.5 * self.tsdiam + self.spbtn1_xy_clearance.get_value())
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start xplus.ngc
        if self.ocode ("O<xplus> call") == -1:
            return
        # show X result
        a=self.probed_position_with_offsets()
        xpres=float(a[0])+0.5*self.spbtn1_probe_diam.get_value()
#        self.lb_probe_xp.set_text( "%.4f" % xpres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point X
        s = "G1 X%f" % xpres
        if self.gcode(s) == -1:
            return

        # move X + tsdiam +  xy_clearance
        aa=self.tsdiam+self.spbtn1_xy_clearance.get_value()
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
        a=self.probed_position_with_offsets()
        xmres=float(a[0])-0.5*self.spbtn1_probe_diam.get_value()
#        self.lb_probe_xm.set_text( "%.4f" % xmres )
        self.lenght_x()
        xcres=0.5*(xpres+xmres)
        self.lb_probe_xc.set_text( "%.4f" % xcres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # go to the new center of X
        s = "G1 X%f" % xcres
        if self.gcode(s) == -1:
            return


        # move Y - tsdiam/2 - xy_clearance
        a=0.5*self.tsdiam+self.spbtn1_xy_clearance.get_value()
        s="""G91
        G1 Y-%f
        G90""" % a
        if self.gcode(s) == -1:
            return
        if self.z_clearance_down() == -1:
            return
        # Start yplus.ngc
        if self.ocode ("O<yplus> call") == -1:
            return
        # show Y result
        a=self.probed_position_with_offsets()
        ypres=float(a[1])+0.5*self.spbtn1_probe_diam.get_value()
#        self.lb_probe_yp.set_text( "%.4f" % ypres )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        # move to finded  point Y
        s = "G1 Y%f" % ypres
        if self.gcode(s) == -1:
            return

        # move Y + tsdiam +  xy_clearance
        aa=self.tsdiam+self.spbtn1_xy_clearance.get_value()
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
        a=self.probed_position_with_offsets()
        ymres=float(a[1])-0.5*self.spbtn1_probe_diam.get_value()
#        self.lb_probe_ym.set_text( "%.4f" % ymres )
        self.lenght_y()
        # find, show and move to finded  point
        ycres=0.5*(ypres+ymres)
        self.lb_probe_yc.set_text( "%.4f" % ycres )
        diam=self.spbtn1_probe_diam.get_value() + (ymres-ypres-self.tsdiam)

        self.lb_probe_d.set_text( "%.4f" % diam )
        # move Z to start point up
        if self.z_clearance_up() == -1:
            return
        self.stat.poll()
        tmpz=self.stat.position[2] - 4
        self.add_history(gtkbutton.get_tooltip_text(),"XcYcZD",0,xcres,0,0,0,ycres,0,0,tmpz,diam,0)
        # move to finded  point
        s = "G1 Y%f" % ycres
        if self.gcode(s) == -1:
            return

#---------------------------------------
#
#    AUTO TOOL MEASUREMENT
#
#---------------------------------------
    # display warning dialog
    def warning_dialog(self, message, secondary = None, title = _("Operator Message")):
        dialog = gtk.MessageDialog(self.window1,
            gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_INFO, gtk.BUTTONS_OK, message)
        # if there is a secondary message then the first message text is bold
        if secondary:
            dialog.format_secondary_text(secondary)
        dialog.show_all()
        dialog.set_title(title)
        responce = dialog.run()
        dialog.destroy()
        return responce == gtk.RESPONSE_OK

        # Here we create a manual tool change dialog
    def on_tool_change( self, gtkbutton, data = None):
        change = self.halcomp['toolchange-change']
        toolnumber = self.halcomp['toolchange-number']
        print "toolnumber =",toolnumber,change
        if change:
            # if toolnumber = 0 we will get an error because we will not be able to get
            # any tooldescription, so we avoid that case
            if toolnumber == 0:
                message = _( "Please remove the mounted tool and press OK when done" )
            else:
                tooltable = self.inifile.find("EMCIO", "TOOL_TABLE")
                if not tooltable:
                    print( _( "**** auto_tool_measurement ERROR ****" ) )
                    print( _( "**** Did not find a toolfile file in [EMCIO] TOOL_TABLE ****" ) )
                    sys.exit()
                CONFIGPATH = os.environ['CONFIG_DIR']
                toolfile = os.path.join( CONFIGPATH, tooltable )
                self.tooledit1.set_filename( toolfile )
                tooldescr = self.tooledit1.get_toolinfo( toolnumber )[16]
                message = _( "Please change to tool\n\n# {0:d}     {1}\n\n then click OK." ).format( toolnumber, tooldescr )
            result = self.warning_dialog( message, title = _( "Manual Toolchange" ) )
            if result:
                self.halcomp["toolchange-changed"] = True
            else:
                print"toolchange abort", self.stat.tool_in_spindle, self.halcomp['toolchange-number']
                self.command.abort()
                self.halcomp['toolchange-number'] = self.stat.tool_in_spindle
                self.halcomp['toolchange-change'] = False
                self.halcomp['toolchange-changed'] = True
                self.messg = _( "Tool Change has been aborted!\n" )
                self.messg += _( "The old tool will remain set!" )
                self.warning_dialog( message)
        else:
            self.halcomp['toolchange-changed'] = False

    def get_tool_sensor_data(self):
        xpos = float(self.inifile.find("TOOLSENSOR", "X"))
        ypos = float(self.inifile.find("TOOLSENSOR", "Y"))
        zpos = float(self.inifile.find("TOOLSENSOR", "Z"))
        maxprobe = float(self.inifile.find("TOOLSENSOR", "MAXPROBE"))
        tsdiam = float(self.inifile.find("TOOLSENSOR", "TS_DIAMETER"))
        revrott = float(self.inifile.find("TOOLSENSOR", "REV_ROTATION_SPEED"))
        return xpos, ypos, zpos, maxprobe, tsdiam, revrott

    def on_spbtn_probe_height_value_changed( self, gtkspinbutton, data = None ):
        self.halcomp["probeheight"] = gtkspinbutton.get_value()
        self.prefs.putpref( "probeheight", gtkspinbutton.get_value(), float )
        c="TS Height = " + "%.4f" % gtkspinbutton.get_value()
        i=self.buffer.get_end_iter()
        if i.get_line() > 1000 :
            i.backward_line()
            self.buffer.delete(i,self.buffer.get_end_iter())
        i.set_line(0)
        self.buffer.insert(i, "%s \n" % c)
    def on_spbtn_block_height_value_changed( self, gtkspinbutton, data = None ):
        blockheight = gtkspinbutton.get_value()
        if blockheight != False:
            self.halcomp["blockheight"] = blockheight
            self.halcomp["probeheight"] = self.spbtn_probe_height.get_value()
        else:
            self.prefs.putpref( "blockheight", 0.0, float )
            print( _( "Conversion error in btn_block_height" ) )
            self._add_alarm_entry( _( "Offset conversion error because off wrong entry" ) )
            self.warning_dialog( self, _( "Conversion error in btn_block_height!" ),
                                   _( "Please enter only numerical values\nValues have not been applied" ) )
        # set koordinate system to new origin
        origin = float(self.inifile.find("AXIS_2", "MIN_LIMIT")) + blockheight
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        self.command.mdi( "G10 L2 P0 Z%s" % origin )
        self.vcp_action_reload.emit( "activate" )
        c="Workpiece Height = " + "%.4f" % gtkspinbutton.get_value()
        i=self.buffer.get_end_iter()
        if i.get_line() > 1000 :
            i.backward_line()
            self.buffer.delete(i,self.buffer.get_end_iter())
        i.set_line(0)
        self.buffer.insert(i, "%s \n" % c)
    def clicked_btn_probe_tool_setter(self, data = None):
        # Start probe_down.ngc
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        self.command.mdi( "O<probe_down> call" )
        self.stat.poll()
        while self.stat.interp_state != linuxcnc.INTERP_IDLE :
            self.command.wait_complete()
            self.stat.poll()
        self.command.wait_complete()
        a=self.stat.probed_position
        self.spbtn_probe_height.set_value( float(a[2]) )
        self.add_history(gtkbutton.get_tooltip_text(),"Z",0,0,0,0,0,0,0,0,a[2],0,0)

    def clicked_btn_probe_workpiece(self, data = None):
        # Start probe_down.ngc
        self.command.mode( linuxcnc.MODE_MDI )
        self.command.wait_complete()
        self.command.mdi( "O<block_down> call" )
        self.stat.poll()
        while self.stat.interp_state != linuxcnc.INTERP_IDLE :
            self.command.wait_complete()
            self.stat.poll()
        self.command.wait_complete()
        a=self.stat.probed_position
        self.spbtn_block_height.set_value( float(a[2]) )
        self.add_history(gtkbutton.get_tooltip_text(),"Z",0,0,0,0,0,0,0,0,a[2],0,0)

    def on_chk_use_tool_measurement_toggled( self, gtkcheckbutton, data = None ):
        if gtkcheckbutton.get_active():
            self.frm_probe_pos.set_sensitive( True )
            self.halcomp["use_toolmeasurement"] = True
            self.halcomp["probeheight"] = self.spbtn_probe_height.get_value()
            self.halcomp["blockheight"] = self.spbtn_block_height.get_value()
        else:
            self.frm_probe_pos.set_sensitive( False )
            self.halcomp["use_toolmeasurement"] = False
            self.halcomp["probeheight"] = 0.0
            self.halcomp["blockheight"] = 0.0
        self.prefs.putpref( "use_toolmeasurement", gtkcheckbutton.get_active(), bool )
        self.hal_led_set_m6.hal_pin.set(gtkcheckbutton.get_active())

#--------------------------
#
#  INIT
#
#--------------------------
    def __init__(self, halcomp,builder,useropts):
        inipath = os.environ["INI_FILE_NAME"]
        self.inifile = ini(inipath)
        if not self.inifile:
            print("**** PROBE SCREEN GET INI INFO **** \n Error, no INI File given !!")
            sys.exit()
        self.display = self.get_display() or "unknown"
        self.command = linuxcnc.command()
        self.stat = linuxcnc.stat()
        self.builder = builder
        self.prefs = ps_preferences( self.get_preference_file_path() )
        self.window1 = builder.get_object("window1")
        self.textarea = builder.get_object("textview1")
        self.e = linuxcnc.error_channel()
        self.stat.poll()
        self.e.poll()

        self.buffer = self.textarea.get_property('buffer')
        self.chk_use_tool_measurement = self.builder.get_object("chk_use_tool_measurement")
        self.chk_use_tool_measurement.set_active( self.prefs.getpref( "use_toolmeasurement", False, bool ) )
        self.chk_set_zero = self.builder.get_object("chk_set_zero")
        self.chk_set_zero.set_active( self.prefs.getpref( "chk_set_zero", False, bool ) )
        self.chk_auto_rott = self.builder.get_object("chk_auto_rott")
        self.chk_auto_rott.set_active( self.prefs.getpref( "chk_auto_rott", False, bool ) )
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

        self.hal_led_set_m6 = self.builder.get_object("hal_led_set_m6")
        self.hal_led_set_zero = self.builder.get_object("hal_led_set_zero")
        self.hal_led_auto_rott = self.builder.get_object("hal_led_auto_rott")

        self.spbtn_offs_x = self.builder.get_object("spbtn_offs_x")
        self.spbtn_offs_y = self.builder.get_object("spbtn_offs_y")
        self.spbtn_offs_z = self.builder.get_object("spbtn_offs_z")
        self.spbtn_offs_angle = self.builder.get_object("spbtn_offs_angle")

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

        self.lx_out = self.builder.get_object("lx_out")
        self.lx_in = self.builder.get_object("lx_in")
        self.ly_out = self.builder.get_object("ly_out")
        self.ly_in = self.builder.get_object("ly_in")
        self.tool_dia = self.builder.get_object("tool_dia")

        self.vcp_action_reload = self.builder.get_object("vcp_action_reload")

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
        self.halcomp.newpin( "ps_offs_angle", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "use_toolmeasurement", hal.HAL_BIT, hal.HAL_OUT )
        if self.chk_use_tool_measurement.get_active():
            self.halcomp["use_toolmeasurement"] = True
            self.hal_led_set_m6.hal_pin.set(1)
        self.halcomp.newpin( "set_zero", hal.HAL_BIT, hal.HAL_OUT )
        if self.chk_set_zero.get_active():
            self.halcomp["set_zero"] = True
            self.hal_led_set_zero.hal_pin.set(1)
        self.halcomp.newpin( "auto_rott", hal.HAL_BIT, hal.HAL_OUT )
        if self.chk_auto_rott.get_active():
            self.halcomp["auto_rott"] = True
            self.hal_led_auto_rott.hal_pin.set(1)
        self.halcomp.newpin( "ps_error", hal.HAL_FLOAT, hal.HAL_OUT )

        if self.inifile.find("TRAJ", "LINEAR_UNITS") not in ['metric', 'mm'] :
            # default values for inches
            tup = (20.0, 2.0, 0.5, 1.0, 0.1, 0.125, 1.0, 1.25)
        else :
            tup = (300.0, 10.0, 3.0, 1.0, 0.5, 2.0, 5.0, 5.0)

        self.spbtn1_search_vel.set_value(self.prefs.getpref("ps_searchvel", tup[0], float))
        self.spbtn1_probe_vel.set_value(self.prefs.getpref("ps_probevel", tup[1], float))
        self.spbtn1_z_clearance.set_value(self.prefs.getpref("ps_z_clearance", tup[2], float))
        self.spbtn1_probe_max.set_value(self.prefs.getpref("ps_probe_max", tup[3], float))
        self.spbtn1_probe_latch.set_value(self.prefs.getpref("ps_probe_latch", tup[4], float))
        self.spbtn1_probe_diam.set_value(self.prefs.getpref("ps_probe_diam", tup[5], float))
        self.spbtn1_xy_clearance.set_value(self.prefs.getpref("ps_xy_clearance", tup[6], float))
        self.spbtn1_edge_lenght.set_value(self.prefs.getpref("ps_edge_lenght", tup[7], float))

        self.spbtn_offs_x.set_value( self.prefs.getpref( "ps_offs_x", 0.0, float ) )
        self.spbtn_offs_y.set_value( self.prefs.getpref( "ps_offs_y", 0.0, float ) )
        self.spbtn_offs_z.set_value( self.prefs.getpref( "ps_offs_z", 0.0, float ) )
        self.spbtn_offs_angle.set_value( self.prefs.getpref( "ps_offs_angle", 0.0, float ) )

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
        self.halcomp["ps_offs_angle"] = self.spbtn_offs_angle.get_value()
        self.halcomp["ps_error"] = 0.

        # For JOG
        self.steps = self.builder.get_object("steps")
        self.incr_rbt_list = []    # we use this list to add hal pin to the button later
        self.jog_increments = []   # This holds the increment values
        self.distance = 0          # This global will hold the jog distance
        self.halcomp.newpin( "jog-increment", hal.HAL_FLOAT, hal.HAL_OUT )
        self._init_jog_increments()

        # For Auto Tool Measurement
        # set the title of the window
        self.frm_probe_pos = self.builder.get_object("frm_probe_pos")
        self.spbtn_probe_height = self.builder.get_object("spbtn_probe_height")
        self.spbtn_block_height = self.builder.get_object("spbtn_block_height")
        self.btn_probe_tool_setter = self.builder.get_object("btn_probe_tool_setter")
        self.btn_probe_workpiece = self.builder.get_object("btn_probe_workpiece")
        self.tooledit1 = self.builder.get_object("tooledit1")
        self.messg = " "

        self.change_text = builder.get_object("change-text")
        self.halcomp.newpin("number", hal.HAL_FLOAT, hal.HAL_IN)
        # make the pins for tool measurement
        self.halcomp.newpin( "probeheight", hal.HAL_FLOAT, hal.HAL_OUT )
        self.halcomp.newpin( "blockheight", hal.HAL_FLOAT, hal.HAL_OUT )
        # for manual tool change dialog
        self.halcomp.newpin( "toolchange-number", hal.HAL_S32, hal.HAL_IN )
        self.halcomp.newpin( "toolchange-changed", hal.HAL_BIT, hal.HAL_OUT )
        pin = self.halcomp.newpin( 'toolchange-change', hal.HAL_BIT, hal.HAL_IN )
        hal_glib.GPin( pin ).connect( 'value_changed', self.on_tool_change )
        self.halcomp['toolchange-number'] = self.stat.tool_in_spindle
        # tool measurement probe settings
        self.xpos, self.ypos, self.zpos, self.maxprobe, self.tsdiam, self.revrott = self.get_tool_sensor_data()
        if not self.xpos or not self.ypos or not self.zpos or not self.maxprobe or not self.tsdiam or not self.revrott :
            self.chk_use_tool_measurement.set_active( False )
            self.tool_dia.set_sensitive( False )
            print( _( "**** PROBE SCREEN INFO ****" ) )
            print( _( "**** no valid probe config in INI File ****" ) )
            print( _( "**** disabled auto tool measurement ****" ) )
        else:
            self.spbtn_probe_height.set_value( self.prefs.getpref( "probeheight", 0.0, float ) )
            self.spbtn_block_height.set_value( self.prefs.getpref( "blockheight", 0.0, float ) )
            # to set the hal pin with correct values we emit a toogled
            if self.chk_use_tool_measurement.get_active():
                self.frm_probe_pos.set_sensitive( True )
                self.halcomp["use_toolmeasurement"] = True
                self.halcomp["probeheight"] = self.spbtn_probe_height.get_value()
                self.halcomp["blockheight"] = self.spbtn_block_height.get_value()
            else:
                self.frm_probe_pos.set_sensitive( False )
                self.chk_use_tool_measurement.set_sensitive( True )

#        gobject.timeout_add( 500, self._periodic )  # time between calls to the function, in milliseconds


def get_handlers(halcomp,builder,useropts):
    return [ProbeScreenClass(halcomp,builder,useropts)]
