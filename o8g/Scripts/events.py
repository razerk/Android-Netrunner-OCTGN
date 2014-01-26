    # Python Scripts for the Android:Netrunner LCG definition for OCTGN
    # Copyright (C) 2012  Konstantine Thoukydides

    # This python script is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this script.  If not, see <http://www.gnu.org/licenses/>.

###==================================================File Contents==================================================###
# This file contains the basic table actions in ANR. They are the ones the player calls when they use an action in the menu.
# Many of them are also called from the autoscripts.
###=================================================================================================================###

import re
import collections
import time

flipBoard = 1 # If True, it signifies that the table board has been flipped because the runner is on the side A
ds = None # The side of the player. 'runner' or 'corp'
flipModX = 0
flipModY = 0

def parseNewCounters(player,counter,oldValue):
   mute()
   debugNotify(">>> parseNewCounters() for player {} with counter {}. Old Value = {}".format(player,counter.name,oldValue))
   if counter.name == 'Tags' and player == me: chkTags()
   if counter.name == 'Bad Publicity' and oldValue < counter.value:
      if player == me: playSound('Gain-Bad_Publicity')
      for c in table: # Looking for cards which trigger off the corp gaining Bad Publicity
         if c.name == "Raymond Flint" and c.controller == me:
            if confirm("Do you want to activate Raymont Flint's ability at this point?\n\n(Make sure your opponent does not have a way to cancel this effect before continuing)"):
               HQaccess(silent = True)
   debugNotify("<<< parseNewCounters()")

   