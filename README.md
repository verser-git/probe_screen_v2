# Probe Screen V2 for LinuxCNC

 Install.
-----------------------------------------------------------------------------
1. Delete (or comment out) from all .hal files lines of the form:
```sh
#loadusr -W hal_manualtoolchange
#net tool-change iocontrol.0.tool-change => hal_manualtoolchange.change
#net tool-changed iocontrol.0.tool-changed <= hal_manualtoolchange.changed
#net tool-number iocontrol.0.tool-prep-number => hal_manualtoolchange.number
```

2. Add to your .ini ...-postgui.hal settings from my-mill.ini and my-mill-postgui.hal, substitute your own constants.

3. The following folders from the archive are placed in configuration folder:
```sh
/python
/macros
/probe_icons
```

4. .axisrc is placed in home ~/ folder.
If you are already using .axisrc, then only add to your file contents of this .axisrc.


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

More info https://vers.by/en/blog/useful-articles/probe-screen
Discussion on the forum linuxcnc.org: https://forum.linuxcnc.org/49-basic-configuration/29187-work-with-probe

Changes in updates.
----------------------------------------------------------------------------------

v.2.0.8
```sh
-corrections in tool diameter button
-allow neg. angle value
-correction pref. and history for tool measurement
```
v.2.0.7
```sh
-correction my-mill-postgui.hal from installation instructions for tool change
-delete all "%" from macros
```
v.2.0.6
```sh
-fixed incorrect toolchange pin connection
-added FernV's corrections for inch
-added FernV's scrolling screen version
```

 License terms.
-----------------------------------------------------------------------------

   This is a plugin for LinuxCNC
   Copyright 2015 Serguei Glavatski <info@vers.by>

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


 Установка.
-----------------------------------------------------------------------------
1. Удалите (или закомментируйте) из всех  .hal файлов строки вида:
```sh
#loadusr -W hal_manualtoolchange
#net tool-change iocontrol.0.tool-change => hal_manualtoolchange.change
#net tool-changed iocontrol.0.tool-changed <= hal_manualtoolchange.changed
#net tool-number iocontrol.0.tool-prep-number => hal_manualtoolchange.number
```
2. Добавьте в конфигурационные файлы .ini ...-postgui.hal все настройки из my-mill.ini, my-mill-postgui.hal, примените свои собственные константы.

3. Следующие папки из архива перенесите в папку с конфигурацией станка:
```sh
/python
/macros
/probe_icons
```

4. Файл .axisrc разместите в папке home ~/.
Если у Вас уже есть .axisrc, то добавьте в него (в конце) содержимое прилагаемого .axisrc


Использование.
----------------------------------------------------------------------------------
Центроискатель устанавливаем в шпиндель. Подводим в ручном режиме центроискатель по Z приблизительно 2-4 мм над поверхностью заготовки, а по XY примерно в позицию, обозначенную цветной точкой на соответствующей кнопке Probe Screen. Заполняем параметры (названия всплывают при подводе мышки). Параметры при изменениии автоматически сохраняются в .pref
При изменении значений параметров с помощью клавиатуры (а не мышкой по стрелкам) обязательно нажать Enter для фиксации новых значений
Использовать только! ту кнопку, которая соответствует позиции центроискателя над заготовкой. Для другой кнопки - другая позиция над заготовкой.

Подробнее см. https://vers.by/ru/blog/useful-articles/probe-screen
Обсуждение на форуме cnc-club.ru: http://www.cnc-club.ru/forum/viewtopic.php?f=15&t=7981#p193295

 Условия лицензии.
-----------------------------------------------------------------------------

   Это плагин для LinuxCNC
   Copyright 2015 Serguei Glavatski <info@vers.by>

   Эта программа является свободным программным обеспечением; Вы можете распространять его и / или изменять
   в соответствии с условиями Стандартной Общественной Лицензии (General Public License) GNU, опубликованной
   Free Software Foundation; либо версия 2 Лицензии, либо
   (на ваше усмотрение) любая более поздняя версия.

   Эта программа распространяется как есть в надежде, что она будет полезна,
   но БЕЗ КАКИХ-ЛИБО ГАРАНТИЙ. Смотрите
   GNU General Public License для более подробной информации.

   Для получения копии Стандартной Общественной Лицензии (General Public License) GNU
   обратитесь в:  Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
