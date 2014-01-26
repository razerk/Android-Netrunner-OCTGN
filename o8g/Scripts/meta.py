﻿    # Python Scripts for the Android:Netrunner LCG definition for OCTGN
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
# This file contains scripts which are not used to play the actual game, but is rather related to the rules of engine
# * [Generic Netrunner] functions are not doing something in the game by themselves but called often by the functions that do.
# * In the [Switches] section are the scripts which controls what automations are active.
# * [Help] functions spawn tokens on the table with succint information on how to play the game.
# * [Button] functions are trigered either from the menu or from the button cards on the table, and announce a specific message each.
# * [Debug] if for helping the developers fix bugs
# * [Online Functions] is everything which connects to online files for some purpose, such as checking the game version or displaying a message of the day
###=================================================================================================================###
import re, time
#import sys # Testing
#import dateutil # Testing
#import elementtree # Testing
#import decimal # Testing

try:
    import os
    if os.environ['RUNNING_TEST_SUITE'] == 'TRUE':
        me = object
        table = object
except ImportError:
    pass

Automations = {'Play, Score and Rez'    : True, # If True, game will automatically trigger card effects when playing or double-clicking on cards. Requires specific preparation in the sets.
               'Start/End-of-Turn'      : True, # If True, game will automatically trigger effects happening at the start of the player's turn, from cards they control.
               'Damage Prevention'      : True, # If True, game will automatically use damage prevention counters from card they control.
               'Triggers'               : True, # If True, game will search the table for triggers based on player's actions, such as installing a card, or trashing one.
               'WinForms'               : True, # If True, game will use the custom Windows Forms for displaying multiple-choice menus and information pop-ups
               'Quick Access'           : False,# If True, game will enable quick access
               'Damage'                 : True}

UniCode = True # If True, game will display credits, clicks, trash, memory as unicode characters

debugVerbosity = -1 # At -1, means no debugging messages display

startupMsg = False # Used to check if the player has checked for the latest version of the game.

gameGUID = None # A Unique Game ID that is fetched during game launch.
#totalInfluence = 0 # Used when reporting online
#gameEnded = False # A variable keeping track if the players have submitted the results of the current game already.
turn = 0 # used during game reporting to report how many turns the game lasted
AccessBtnNextChoice = 0
askedQA = False

CardsAA = {} # Dictionary holding all the AutoAction scripts for all cards
CardsAS = {} # Dictionary holding all the AutoScript scripts for all cards


#---------------------------------------------------------------------------
# Generic Netrunner functions
#---------------------------------------------------------------------------
def uniCredit(count):
   debugNotify(">>> uniCredit(){}".format(extraASDebug())) #Debug
   count = num(count)
   if UniCode: return "{} ¥".format(count)
   else: 
      if count == 1: grammar = 's'
      else: grammar =''
      return "{} Credit{}".format(count,grammar)
 
def uniRecurring(count):
   debugNotify(">>> uniRecurring(){}".format(extraASDebug())) #Debug
   count = num(count)
   if UniCode: return "{} £".format(count)
   else: 
      if count == 1: grammar = 's'
      else: grammar =''
      return "{} Recurring Credit{}".format(count,grammar)
 
def uniClick():
   debugNotify(">>> uniClick(){}".format(extraASDebug())) #Debug
   if UniCode: return ' ⌚'
   else: return '(/)'

def uniTrash():
   debugNotify(">>> uniTrash(){}".format(extraASDebug())) #Debug
   if UniCode: return '⏏'
   else: return 'Trash'

def uniMU(count = 1):
   debugNotify(">>> uniMU(){}".format(extraASDebug())) #Debug
   if UniCode: 
      if num(count) == 1: return '⎗'
      elif num(count) == 2:  return '⎘'
      else: return '{} MU'.format(count)
   else: return '{} MU'.format(count)
   
def uniLink():
   debugNotify(">>> uniLink(){}".format(extraASDebug())) #Debug
   if UniCode: return '⎙'
   else: return 'Base Link'

def uniSubroutine():
   debugNotify(">>> uniLink(){}".format(extraASDebug())) #Debug
   if UniCode: return '⏎'
   else: return '[Subroutine]'

def chooseWell(limit, choiceText, default = None):
   debugNotify(">>> chooseWell(){}".format(extraASDebug())) #Debug
   if default == None: default = 0# If the player has not provided a default value for askInteger, just assume it's the max.
   choice = limit # limit is the number of choices we have
   if limit > 1: # But since we use 0 as a valid choice, then we can't actually select the limit as a number
      while choice >= limit:
         choice = askInteger("{}".format(choiceText), default)
         if not choice: return False
         if choice > limit: whisper("You must choose between 0 and {}".format(limit - 1))
   else: choice = 0 # If our limit is 1, it means there's only one choice, 0.
   return choice

def findMarker(card, markerDesc): # Goes through the markers on the card and looks if one exist with a specific description
   debugNotify(">>> findMarker() on {} with markerDesc = {}".format(card,markerDesc)) #Debug
   foundKey = None
   if markerDesc in mdict: markerDesc = mdict[markerDesc][0] # If the marker description is the code of a known marker, then we need to grab the actual name of that.
   for key in card.markers:
      debugNotify("Key: {}\nmarkerDesc: {}".format(key[0],markerDesc), 3) # Debug
      if re.search(r'{}'.format(markerDesc),key[0]) or markerDesc == key[0]:
         foundKey = key
         debugNotify("Found {} on {}".format(key[0],card), 2)
         break
   debugNotify("<<< findMarker() by returning: {}".format(foundKey), 3)
   return foundKey
   
def getKeywords(card): # A function which combines the existing card keywords, with markers which give it extra ones.
   debugNotify(">>> getKeywords(){}".format(extraASDebug())) #Debug
   global Stored_Keywords
   #confirm("getKeywords") # Debug
   keywordsList = []
   cKeywords = card.Keywords # First we try a normal grab, if the card properties cannot be read, then we flip face up.
   if cKeywords == '?': cKeywords = fetchProperty(card, 'Keywords')
   strippedKeywordsList = cKeywords.split('-')
   for cardKW in strippedKeywordsList:
      strippedKW = cardKW.strip() # Remove any leading/trailing spaces between traits. We need to use a new variable, because we can't modify the loop iterator.
      if strippedKW: keywordsList.append(strippedKW) # If there's anything left after the stip (i.e. it's not an empty string anymrore) add it to the list.   
   if card.markers:
      for key in card.markers:
         markerKeyword = re.search('Keyword:([\w ]+)',key[0])
         if markerKeyword:
            #confirm("marker found: {}\n key: {}".format(markerKeyword.groups(),key[0])) # Debug
            #if markerKeyword.group(1) == 'Barrier' or markerKeyword.group(1) == 'Sentry' or markerKeyword.group(1) == 'Code Gate': #These keywords are mutually exclusive. An Ice can't be more than 1 of these
               #if 'Barrier' in keywordsList: keywordsList.remove('Barrier') # It seems in ANR, they are not so mutually exclusive. See: Tinkering
               #if 'Sentry' in keywordsList: keywordsList.remove('Sentry') 
               #if 'Code Gate' in keywordsList: keywordsList.remove('Code Gate')
            if re.search(r'Breaker',markerKeyword.group(1)):
               if 'Barrier Breaker' in keywordsList: keywordsList.remove('Barrier Breaker')
               if 'Sentry Breaker' in keywordsList: keywordsList.remove('Sentry Breaker')
               if 'Code Gate Breaker' in keywordsList: keywordsList.remove('Code Gate Breaker')
            keywordsList.append(markerKeyword.group(1))
   keywords = ''
   for KW in keywordsList:
      keywords += '{}-'.format(KW)
   Stored_Keywords[card._id] = keywords[:-1] # We also update the global variable for this card, which is used by many functions.
   debugNotify("<<< getKeywords() by returning: {}.".format(keywords[:-1]), 3)
   return keywords[:-1] # We need to remove the trailing dash '-'
   
def pileName(group):
   debugNotify(">>> pileName()") #Debug
   debugNotify("pile name {}".format(group.name), 2) #Debug   
   debugNotify("pile player: {}".format(group.player), 2) #Debug
   if group.name == 'Table': name = 'Table'
   elif group.name == 'Heap/Archives(Face-up)':
      if group.player.getGlobalVariable('ds') == 'corp': name = 'Face-up Archives'
      else: name = 'Heap'
   elif group.name == 'R&D/Stack':
      if group.player.getGlobalVariable('ds') == 'corp': name = 'R&D'
      else: name = 'Stack'
   elif group.name == 'Archives(Hidden)': name = 'Hidden Archives'
   else:
      if group.player.getGlobalVariable('ds') == 'corp': name = 'HQ'
      else: name = 'Grip'
   debugNotify("<<< pileName() by returning: {}".format(name), 3)
   return name

def clearNoise(): # Clears all player's noisy bits. I.e. nobody is considered to have been noisy this turn.
   debugNotify(">>> clearNoise()") #Debug
   for player in players: player.setGlobalVariable('wasNoisy', '0') 
   debugNotify("<<< clearNoise()", 3) #Debug

def storeSpecial(card): 
# Function stores into a shared variable some special cards that other players might look up.
   try:
      debugNotify(">>> storeSpecial(){}".format(extraASDebug())) #Debug
      storeProperties(card, True)
      specialCards = eval(me.getGlobalVariable('specialCards'))
      if card.name == 'HQ' or card.name == 'R&D' or card.name == 'Archives':
         specialCards[card.name] = card._id # The central servers we find via name
      else: specialCards[card.Type] = card._id
      me.setGlobalVariable('specialCards', str(specialCards))
   except: notify("!!!ERROR!!! In storeSpecial()")

def getSpecial(cardType,player = me):
# Functions takes as argument the name of a special card, and the player to whom it belongs, and returns the card object.
   debugNotify(">>> getSpecial() for player: {}".format(me.name)) #Debug
   specialCards = eval(player.getGlobalVariable('specialCards'))
   cardID = specialCards.get(cardType,None)
   if not cardID: 
      debugNotify("No special card of type {} found".format(cardType),2)
      card = None
   else:
      card = Card(specialCards[cardType])
      debugNotify("Stored_Type = {}".format(Stored_Type.get(card._id,'NULL')), 2)
      if Stored_Type.get(card._id,'NULL') == 'NULL':
         #if card.owner == me: delayed_whisper(":::DEBUG::: {} was NULL. Re-storing as an attempt to fix".format(cardType)) # Debug
         debugNotify("card ID = {}".format(card._id))
         debugNotify("Stored Type = {}".format(Stored_Type.get(card._id,'NULL')))
         storeProperties(card, True)
   debugNotify("<<< getSpecial() by returning: {}".format(card), 3)
   return card

def chkRAM(card, action = 'INSTALL', silent = False):
   debugNotify(">>> chkRAM(){}".format(extraASDebug())) #Debug
   MUreq = num(fetchProperty(card,'Requirement'))
   hostCards = eval(getGlobalVariable('Host Cards'))
   if hostCards.has_key(card._id): hostC = Card(hostCards[card._id])
   else: hostC = None
   if (MUreq > 0
         and not (card.markers[mdict['DaemonMU']] and not re.search(r'Daemon',getKeywords(card)))
         and not findMarker(card,'Daemon Hosted MU')
         and not (card.markers[mdict['Cloud']] and card.markers[mdict['Cloud']] >= 1) # If the card is already in the cloud, we do not want to modify the player's MUs
         and not (hostC and findMarker(card, '{} Hosted'.format(hostC.name)) and hostC.name != "Scheherazade") # No idea if this will work.
         and card.highlight != InactiveColor 
         and card.highlight != RevealedColor):
      if action == 'INSTALL':
         card.owner.MU -= MUreq
         chkCloud(card)
         update()
         if not card.markers[mdict['Cloud']]:
            MUtext = ", using up  {}".format(uniMU(MUreq))
         else: MUtext = ''
      elif action == 'UNINSTALL':
         card.owner.MU += MUreq
         MUtext = ", freeing up  {}".format(uniMU(MUreq))
   else: MUtext = ''
   if card.owner.MU < 0 and not silent: 
      notify(":::Warning:::{}'s programs require more memory than they have available. They must trash enough programs to bring their available Memory to at least 0".format(card.controller))
      information(":::ATTENTION:::\n\nYou are now using more MUs than you have available memory!\
                  \nYou need to trash enough programs to bring your Memory to 0 or higher")
   debugNotify("<<< chkRAM() by returning: {}".format(MUtext), 3)
   return MUtext

def chkCloud(cloudCard = None): # A function which checks the table for cards which can be put in the cloud and thus return their used MUs
   debugNotify(">>> chkCloud(){}".format(extraASDebug())) #Debug
   if not cloudCard: cards = [c for c in table if c.Type == 'Program']
   else: cards = [cloudCard] # If we passed a card as a variable, we just check the cloud status of that card
   for card in cards:
      debugNotify("Cloud Checking {} with AS = {}".format(card,fetchProperty(card, 'AutoScripts')), 2) #Debug
      cloudRegex = re.search(r'Cloud([0-9]+)Link',fetchProperty(card, 'AutoScripts'))
      if cloudRegex:
         linkRequired = num(cloudRegex.group(1))
         debugNotify("Found Cloud Regex. linkRequired = {}".format(linkRequired), 2) #Debug
         if linkRequired <= card.controller.counters['Base Link'].value and not card.markers[mdict['Cloud']]:
            card.markers[mdict['Cloud']] = 1
            card.controller.MU += num(card.Requirement)
            notify("-- {}'s {} has been enabled for cloud computing".format(me,card))            
         if linkRequired > card.controller.counters['Base Link'].value and card.markers[mdict['Cloud']] and card.markers[mdict['Cloud']] >= 1:
            card.markers[mdict['Cloud']] = 0
            card.controller.MU -= num(card.Requirement)
            notify("-- {}'s {} has lost connection to the cloud.".format(me,card))
            if card.controller.MU < 0: 
               notify(":::Warning:::{}'s loss of cloud connection means that their programs require more memory than they have available. They must trash enough programs to bring their available Memory to at least 0".format(card.controller))
   debugNotify("<<< chkCloud()", 3)
            
   
def chkHostType(card, seek = 'Targeted', caissa = False):
   debugNotify(">>> chkHostType(){}".format(extraASDebug())) #Debug
   # Checks if the card needs to have a special host targeted before it can come in play.
   if caissa: hostType = re.search(r'CaissaPlace:([A-Za-z1-9:_ -]+)', fetchProperty(card, 'AutoScripts'))
   else: hostType = re.search(r'Placement:([A-Za-z1-9:_ -]+)', fetchProperty(card, 'AutoScripts'))
   if hostType:
      debugNotify("hostType: {}.".format(hostType.group(1)), 2) #Debug
      if hostType.group(1) == 'ICE': host = findTarget('{}-isICE-choose1'.format(seek))
      else: host = findTarget('{}-at{}-choose1'.format(seek,hostType.group(1)),card = card)
      if len(host) == 0:
         delayed_whisper("ABORTING!")
         result = 'ABORT'
      else: result = host[0] # If a propert host is targeted, then we return it to the calling function. We always return just the first result.
   else: result = None
   debugNotify("<<< chkHostType() with result {}".format(result), 3)
   return result
   
def chkDoublePrevention():
   # This function checks for various cards which, if present prevent extra costs from double cards.
   debugNotify(">>> chkDoublePrevention(){}".format(extraASDebug())) #Debug
   fullCostPrev = False
   for c in table: 
      if fullCostPrev: break # If we already prevented the full cost, let's break out of the loop.
      if c.name == 'Starlight Crusade Funding' and c.controller == me: 
         notify("--> {} has allowed {} to ignore the additional costs".format(c,me))
         fullCostPrev = True
   debugNotify("<<< chkDoublePrevention() with fullCostPrev = {}".format(fullCostPrev)) #Debug
   return fullCostPrev
 
def checkUnique (card, manual = False):
   debugNotify(">>> checkUnique(){}".format(extraASDebug())) #Debug
   mute()
   if not re.search(r'Unique', getKeywords(card)): 
      debugNotify("<<< checkUnique() - Not a unique card", 3) #Debug
      return True #If the played card isn't unique do nothing.
   cName = fetchProperty(card, 'name')
   ExistingUniques = [ c for c in table
                       if c.owner == me 
                       and c.controller == me 
                       and c.isFaceUp 
                       and c.name == cName ]
   if ((not manual and len(ExistingUniques) != 0) or (manual and len(ExistingUniques) != 1)) and not confirm("This unique card is already in play. Are you sure you want to play {}?\n\n(If you do, your existing unique card will be Trashed at no cost)".format(fetchProperty(card, 'name'))) : return False
   else:
      count = len(ExistingUniques)
      for uniqueC in ExistingUniques: 
         if manual and count == 1: break # If it's a manual, the new unique card is already on the table, so we do not want to trash it as well.
         trashForFree(uniqueC)
         count -= 1
   debugNotify("<<< checkUnique() - Returning True", 3) #Debug
   return True   

def chkTargeting(card):
   debugNotify(">>> chkTargeting(){}".format(extraASDebug())) #Debug
   if (re.search(r'on(Rez|Play|Install)[^|]+(?<!Auto)Targeted', CardsAS.get(card.model,''))
         and len(findTarget(CardsAS.get(card.model,''))) == 0
         and not re.search(r'isOptional', CardsAS.get(card.model,''))
         and not confirm("This card requires a valid target for it to work correctly.\
                        \nIf you proceed without a target, strange things might happen.\
                      \n\nProceed anyway?")):
      return 'ABORT'
   if ds == 'corp': runnerPL = findOpponent()
   else: runnerPL = me
   if re.search(r'ifTagged', CardsAS.get(card.model,'')) and runnerPL.Tags == 0 and not re.search(r'isOptional', CardsAS.get(card.model,'')):
      whisper("{} must be tagged in order to use this card".format(runnerPL))
      return 'ABORT'
   if re.search(r'isExposeTarget', CardsAS.get(card.model,'')) and getSetting('ExposeTargetsWarn',True):
      if confirm("This card will automatically provide a bonus depending on how many non-exposed derezzed cards you've selected.\
                \nMake sure you've selected all the cards you wish to expose and have peeked at them before taking this action\
                \nSince this is the first time you take this action, you have the opportunity now to abort and select your targets before traying it again.\
              \n\nDo you want to abort this action?\
                \n(This message will not appear again)"):
         setSetting('ExposeTargetsWarn',False)
         return 'ABORT'
      else: setSetting('ExposeTargetsWarn',False) # Whatever happens, we don't show this message again.
   if re.search(r'Reveal&Shuffle', CardsAS.get(card.model,'')) and getSetting('RevealandShuffleWarn',True):
      if confirm("This card will automatically provide a bonus depending on how many cards you selected to reveal (i.e. place on the table) from your hand.\
                \nMake sure you've selected all the cards (of any specific type required) you wish to reveal to the other players\
                \nSince this is the first time you take this action, you have the opportunity now to abort and select your targets before trying it again.\
              \n\nDo you want to abort this action?\
                \n(This message will not appear again)"):
         setSetting('RevealandShuffleWarn',False)
         return 'ABORT'
      else: setSetting('RevealandShuffleWarn',False) # Whatever happens, we don't show this message again.
   if re.search(r'HandTarget', CardsAS.get(card.model,'')) or re.search(r'HandTarget', CardsAA.get(card.model,'')):
      hasTarget = False
      for c in me.hand:
         if c.targetedBy and c.targetedBy == me: hasTarget = True
      if not hasTarget:
         whisper(":::Warning::: This card effect requires that you have one of more cards targeted from your hand. Aborting!")
         return 'ABORT'

def checkNotHardwareConsole (card, manual = False):
   debugNotify(">>> checkNotHardwareConsole(){}".format(extraASDebug())) #Debug
   mute()
   if card.Type != "Hardware" or not re.search(r'Console', getKeywords(card)): return True
   ExistingConsoles = [ c for c in table
         if c.owner == me and c.isFaceUp and re.search(r'Console', getKeywords(c)) ]
   if ((not manual and len(ExistingConsoles) != 0) or (manual and len(ExistingConsoles) != 1)) and not confirm("You already have at least one console in play and you're not normally allowed to install a second. Are you sure you want to install {}?".format(fetchProperty(card, 'name'))): return False
   #else:
      #for HWDeck in ExistingConsoles: trashForFree(HWDeck)
   debugNotify(">>> checkNotHardwareConsole()") #Debug
   return True   
   
def chkTags():
# A function which checks if the runner has any tags and puts a tag marker on the runner ID in that case.
   if ds == 'runner': 
      ID = Identity
      player = me
   else: 
      player = findOpponent()
      ID = getSpecial('Identity',player)
   remoteCall(player,'syncTags',[]) # We send the tag update as a remote call, so as not to get complaints from OCTGN
   if player.Tags: return True      
   else: return False
      
def syncTags():
   mute()
   ID = getSpecial('Identity',me)
   if me.Tags: ID.markers[mdict['Tag']] = me.Tags
   else: ID.markers[mdict['Tag']] = 0
   

def fetchRunnerPL():
   if ds == 'runner': return me
   else: return findOpponent()
   
def clearAttachLinks(card):
# This function takes care to discard any attachments of a card that left play
# It also clear the card from the host dictionary, if it was itself attached to another card
# If the card was hosted by a Daemon, it also returns the free MU token to that daemon
   debugNotify(">>> clearAttachLinks()") #Debug
   hostCards = eval(getGlobalVariable('Host Cards'))
   cardAttachementsNR = len([att_id for att_id in hostCards if hostCards[att_id] == card._id])
   if cardAttachementsNR >= 1:
      hostCardSnapshot = dict(hostCards)
      for attachment in hostCardSnapshot:
         if hostCardSnapshot[attachment] == card._id:
            if Card(attachment) in table: intTrashCard(Card(attachment),0,cost = "host removed")
            del hostCards[attachment]
      setGlobalVariable('Host Cards',str(hostCards))
   unlinkHosts(card)
   debugNotify("<<< clearAttachLinks()", 3) #Debug   

def unlinkHosts(card): #Checking if the card is attached to unlink.
   debugNotify(">>> returnHostTokens()") #Debug
   hostCards = eval(getGlobalVariable('Host Cards'))
   if hostCards.has_key(card._id):
      hostCard = Card(hostCards[card._id])
      if (re.search(r'Daemon',getKeywords(hostCard)) or re.search(r'CountsAsDaemon', CardsAS.get(hostCard.model,''))) and hostCard.group == table: 
         if card.markers[mdict['DaemonMU']] and not re.search(r'Daemon',getKeywords(card)):
            hostCard.markers[mdict['DaemonMU']] += card.markers[mdict['DaemonMU']] # If the card was hosted by a Daemon, we return any Daemon MU's used.
         DaemonHosted = findMarker(card,'Daemon Hosted MU')
         if DaemonHosted: # if the card just removed was a daemon hosted by a daemon, then it's going to have a different kind of token.
            hostCard.markers[mdict['DaemonMU']] += card.markers[DaemonHosted] # If the card was hosted by a Daemon, we return any Daemon MU's used.
      customMU = findMarker(card, '{} Hosted'.format(hostCard.name)) 
      debugNotify("customMU = {}".format(customMU))
      if customMU and hostCard.group == table: # If the card has a custom hosting marker (e.g. Dinosaurus)
         hostCard.markers[customMU] += 1 # Then we return the custom hosting marker to its original card to signifiy it's free to host another program.
         card.markers[customMU] -= 1
      del hostCards[card._id] # If the card was an attachment, delete the link
      setGlobalVariable('Host Cards',str(hostCards)) # We need to store again before orgAttachments takes over
      if not re.search(r'Daemon',getKeywords(hostCard)) and not customMU: 
         orgAttachments(hostCard) # Reorganize the attachments if the parent is not a daemon-type card.
   debugNotify("<<< returnHostTokens()", 3) #Debug   
   
def sendToTrash(card, pile = None): # A function which takes care of sending a card to the right trash pile and running the appropriate scripts. Doesn't handle costs.
   debugNotify(">>> sendToTrash()") #Debug   
   if pile == None: pile = card.owner.piles['Heap/Archives(Face-up)'] # I can't pass it as a function variable. OCTGN doesn't like it.
   debugNotify("Target Pile: {}'s {}".format(pile.player,pile.name))
   debugNotify("sendToTrash says previous group = {} and highlight = {}".format(card.group.name,card.highlight))
   if pile.controller != me:
      debugNotify("We don't control the discard pile. Taking it over.")
      grabPileControl(pile)
   if card.controller != me and card.group == table: grabCardControl(card) # We take control of the card in order to avoid errors
   if card.group == table: 
      playTrashSound(card)
      autoscriptOtherPlayers('CardTrashed',card)
   if card.group == table or chkModulator(card, 'runTrashScriptWhileInactive', 'onTrash'): 
      executePlayScripts(card,'TRASH') # We don't want to run automations on simply revealed cards, but some of them will like Director Haas.
   clearAttachLinks(card)
   if chkModulator(card, 'preventTrash', 'onTrash'): # IF the card has the preventTrash modulator, it's not supposed to be trashed.
      if chkModulator(card, 'ifAccessed', 'onTrash') and ds != 'runner': card.moveTo(pile) # Unless it only has that modulator active during runner access. Then when the corp trashes it, it should trash normally.
   else: card.moveTo(pile)
   if pile.player != pile.controller: remoteCall(pile.controller,'passPileControl',[pile,pile.player])
   update()
   debugNotify("<<< sendToTrash()", 3) #Debug   
   
def findAgendaRequirement(card):
   mute()
   debugNotify(">>> findAgendaRequirement() for card: {}".format(card)) #Debug
   AdvanceReq = num(fetchProperty(card, 'Cost'))
   for c in table:
      for autoS in CardsAS.get(c.model,'').split('||'):
         if re.search(r'whileInPlay', autoS):
            advanceModRegex = re.search(r'(Increase|Decrease)([0-9])Advancement', autoS)
            if advanceModRegex:
               debugNotify("advanceModRegex = {} ".format(advanceModRegex.groups()))
               if re.search(r'onlyOnce',autoS) and c.orientation == Rot90: continue # If the card has a once per-turn ability which has been used, ignore it
               if (re.search(r'excludeDummy',autoS) or re.search(r'CreateDummy',autoS)) and c.highlight == DummyColor: continue
               advanceMod = num(advanceModRegex.group(2)) * {'Decrease': -1}.get(advanceModRegex.group(1),1) * per(autoS, c, 0, findTarget(autoS, card = card))
               debugNotify("advanceMod = {}".format(advanceMod))
               AdvanceReq += advanceMod
               if advanceMod: delayed_whisper("-- {} {}s advance requirement by {}".format(c,advanceModRegex.group(1),advanceMod))
   debugNotify("<<< findAgendaRequirement() with return {}".format(AdvanceReq)) #Debug
   return AdvanceReq
   
def resetAll(): # Clears all the global variables in order to start a new game.
   global Stored_Name, Stored_Type, Stored_Cost, Stored_Keywords, Stored_AutoActions, Stored_AutoScripts
   global installedCount, debugVerbosity, newturn,endofturn, currClicks, turn, autoRezFlags
   debugNotify(">>> resetAll(){}".format(extraASDebug())) #Debug
   mute()
   if len(table) > 0: return # This function should only ever run after game start or reset. We abort in case it's a reconnect.
   me.counters['Credits'].value = 5
   me.counters['Hand Size'].value = 5
   me.counters['Tags'].value = 0
   me.counters['Agenda Points'].value = 0
   me.counters['Bad Publicity'].value = 0
   Stored_Name.clear()
   Stored_Type.clear()
   Stored_Cost.clear()
   Stored_Keywords.clear()
   Stored_AutoActions.clear()
   Stored_AutoScripts.clear()
   installedCount.clear()
   setGlobalVariable('CurrentTraceEffect','None')
   setGlobalVariable('CorpTraceValue','None')
   setGlobalVariable('League','')
   setGlobalVariable('Access','DENIED')
   setGlobalVariable('accessAttempts','0')
   newturn = False 
   endofturn = False
   currClicks = 0
   turn = 0
   del autoRezFlags[:]
   ShowDicts()
   if len(players) > 1: debugVerbosity = -1 # Reset means normal game.
   elif debugVerbosity != -1 and confirm("Reset Debug Verbosity?"): debugVerbosity = -1    
   debugNotify("<<< resetAll()") #Debug   
   
def clearLeftoverEvents():
   debugNotify(">>> clearLeftoverEvents()") #Debug   
   debugNotify("About to clear all events from table")
   hostCards = eval(getGlobalVariable('Host Cards'))
   for card in table: # We discard all events on the table when the player tries to use another click.
      debugNotify("Processing {}".format(card))
      debugNotify("hostCards eval = {}".format(hostCards))
      if card.isFaceUp and (card.Type == 'Operation' or card.Type == 'Event') and card.highlight != DummyColor and card.highlight != RevealedColor and card.highlight != InactiveColor and not card.markers[mdict['Scored']] and not hostCards.has_key(card._id): # We do not trash "scored" events (e.g. see Notoriety) or cards hosted on others card (e.g. see Oversight AI)
         intTrashCard(card,0,"free") # Clearing all Events and operations for players who keep forgeting to clear them.   
   debugNotify("<<< clearLeftoverEvents()") #Debug   
      
#---------------------------------------------------------------------------
# Card Placement
#---------------------------------------------------------------------------

def placeCard(card, action = 'INSTALL', hostCard = None, type = None, retainPos = False):
   debugNotify(">>> placeCard() with action: {}".format(action)) #Debug
   if not hostCard:
      hostCard = chkHostType(card, seek = 'DemiAutoTargeted')
      if hostCard:
         try:
            if hostCard == 'ABORT': 
               delayed_whisper(":::ERROR::: No Valid Host Targeted! Aborting Placement.") # We can pass a host from a previous function (e.g. see Personal Workshop)
               return 'ABORT'
         except: pass
   if hostCard: hostMe(card,hostCard)
   else:
      global installedCount
      if not type: 
         type = fetchProperty(card, 'Type') # We can pass the type of card as a varialbe. This way we can pass one card as another.
         if action != 'INSTALL' and type == 'Agenda':
            if ds == 'corp': type = 'scoredAgenda'
            else: type = 'liberatedAgenda'
         if action == 'INSTALL' and re.search(r'Console',card.Keywords): type = 'Console'
      if action == 'INSTALL' and type in CorporationCardTypes: CfaceDown = True
      else: CfaceDown = False
      debugNotify("Setting installedCount. Type is: {}, CfaceDown: {}".format(type, str(CfaceDown)), 3) #Debug
      if installedCount.get(type,None) == None: installedCount[type] = 0
      else: installedCount[type] += 1
      debugNotify("installedCount is: {}. Setting loops...".format(installedCount[type]), 2) #Debug
      loopsNR = installedCount[type] / (place[type][3]) 
      loopback = place[type][3] * loopsNR 
      if loopsNR and place[type][3] != 1: offset = 15 * (loopsNR % 3) # This means that in one loop the offset is going to be 0 and in another 15.
      else: offset = 0
      debugNotify("installedCount[type] is: {}.\nLoopsNR is: {}.\nLoopback is: {}\nOffset is: {}".format(installedCount[type],offset, loopback, offset), 3) #Debug
      #if not retainPos: card.moveToTable(((place[type][0] + (((cwidth(card,0) + place[type][2]) * (installedCount[type] - loopback)) + offset) * place[type][4]) * flipBoard) + flipModX,(place[type][1] * flipBoard) + flipModY,CfaceDown) 
      if not retainPos: placeOnTable(card,((place[type][0] + (((cwidth(card,0) + place[type][2]) * (installedCount[type] - loopback)) + offset) * place[type][4]) * flipBoard) + flipModX,(place[type][1] * flipBoard) + flipModY,CfaceDown) 
      # To explain the above, we place the card at: Its original location
      #                                             + the width of the card
      #                                             + a predefined distance from each other times the number of other cards of the same type
      #                                             + the special offset in case we've done one or more loops
      #                                             And all of the above, multiplied by +1/-1 (place[type][4]) in order to direct the cards towards the left or the right
      #                                             And finally, the Y axis is always the same in ANR.
      if type == 'Agenda' or type == 'Upgrade' or type == 'Asset': # camouflage until I create function to install them on specific Server, via targeting.
         installedCount['Agenda'] = installedCount[type]
         installedCount['Asset'] = installedCount[type]
         installedCount['Upgrade'] = installedCount[type]
      if not card.isFaceUp: 
         debugNotify("Peeking() at placeCard()")
         card.peek() # Added in octgn 3.0.5.47
   debugNotify("<<< placeCard()", 3) #Debug

def hostMe(card,hostCard):
   debugNotify(">>> hostMe()") #Debug
   unlinkHosts(card) # First we make sure we clear any previous hosting and return any markers to their right place.
   hostCards = eval(getGlobalVariable('Host Cards'))
   hostCards[card._id] = hostCard._id
   setGlobalVariable('Host Cards',str(hostCards))
   orgAttachments(hostCard)
   debugNotify("<<< hostMe()") #Debug

def orgAttachments(card):
# This function takes all the cards attached to the current card and re-places them so that they are all visible
# xAlg, yAlg are the algorithsm which decide how the card is placed relative to its host and the other hosted cards. They are always multiplied by attNR
   debugNotify(">>> orgAttachments()") #Debug
   attNR = 1
   debugNotify(" Card Name : {}".format(card.name), 4)
   if specialHostPlacementAlgs.has_key(card.name):
      debugNotify("Found specialHostPlacementAlgs", 3)
      xAlg = specialHostPlacementAlgs[card.name][0]
      yAlg = specialHostPlacementAlgs[card.name][1]
      debugNotify("Found Special Placement Algs. xAlg = {}, yAlg = {}".format(xAlg,yAlg), 2)
   else: 
      debugNotify("No specialHostPlacementAlgs", 3)
      xAlg = 0 # The Default placement on the X axis, is to place the attachments at the same X as their parent
      if card.controller == me: sideOffset = playerside # If it's our card, we need to assign it towards our side
      else: sideOffset = playerside * -1 # Otherwise we assign it towards the opponent's side
      yAlg =  -(cwidth(card) / 4 * sideOffset) # Defaults
   hostCards = eval(getGlobalVariable('Host Cards'))
   cardAttachements = [Card(att_id) for att_id in hostCards if hostCards[att_id] == card._id]
   x,y = card.position
   for attachment in cardAttachements:
      debugNotify("Checking group of {}".format(attachment))
      debugNotify("group name = {}".format(attachment.group.name))
      if attachment.owner.getGlobalVariable('ds') == 'corp' and pileName(attachment.group) in ['R&D','Face-up Archives','HQ'] and attachment.Type != 'Operation':
         debugNotify("card is faceDown")
         cFaceDown = True
      else: 
         debugNotify("attachment.isFaceUp = {}".format(attachment.isFaceUp))
         cFaceDown = False # If we're moving corp cards to the table, we generally move them face down
      placeOnTable(attachment,x + ((xAlg * attNR) * flipBoard), y + ((yAlg * attNR) * flipBoard),cFaceDown)
      if cFaceDown and attachment.owner == me: 
         debugNotify("Peeking() at orgAttachments()")
         attachment.peek() # If we moved our own card facedown to the table, we peek at it.
      if fetchProperty(attachment, 'Type') == 'ICE': attachment.orientation = Rot90 # If we just moved an ICE to the table, we make sure it's turned sideways.
      indexSet(attachment,len(cardAttachements) - attNR) # This whole thing has become unnecessary complicated because sendToBack() does not work reliably
      debugNotify("{} index = {}".format(attachment,attachment.getIndex), 4) # Debug
      attNR += 1
      debugNotify("Moving {}, Iter = {}".format(attachment,attNR), 4)
   indexSet(card,'front') # Because things don't work as they should :(
   if debugVerbosity >= 4: # Checking Final Indices
      for attachment in cardAttachements: notify("{} index = {}".format(attachment,attachment.getIndex)) # Debug
   debugNotify("<<< orgAttachments()", 3) #Debug      

def possess(daemonCard, programCard, silent = False, force = False):
   debugNotify(">>> possess(){}".format(extraASDebug())) #Debug
   #This function takes as arguments 2 cards. A Daemon and a program requiring MUs, then assigns the program to the Daemon, restoring the used MUs to the player.
   hostType = re.search(r'Placement:([A-Za-z1-9:_ -]+)', fetchProperty(programCard, 'AutoScripts'))
   if hostType and not re.search(r'Daemon',hostType.group(1)):
      delayed_whisper("This card cannot be hosted on a Daemon as it needs a special host type")
      return 'ABORT'
   count = num(programCard.properties["Requirement"])
   debugNotify("Looking for custom hosting marker", 2)
   customHostMarker = findMarker(daemonCard, '{} Hosted'.format(daemonCard.name)) # We check if the card has a custom hosting marker which we use when the hosting is forced
   debugNotify("Custom hosting marker: {}".format(customHostMarker), 2)
   hostCards = eval(getGlobalVariable('Host Cards'))   
   if not force and (count > daemonCard.markers[mdict['DaemonMU']] and not customHostMarker):
      delayed_whisper(":::ERROR::: {} has already hosted the maximum amount of programs it can hold.".format(daemonCard))
      return 'ABORT'
   elif force and not customHostMarker: # .get didn't work on card.markers[] :-(
      delayed_whisper(":::ERROR::: {} has already hosted the maximum amount of programs it can hold.".format(daemonCard))
      return 'ABORT'
   elif hostCards.has_key(programCard._id):
      delayed_whisper(":::ERROR::: {} is already hosted in {}.".format(programCard,Card(hostCards[programCard._id])))
      return 'ABORT'
   else:
      debugNotify("We have a valid daemon host", 2) #Debug
      hostCards[programCard._id] = daemonCard._id
      setGlobalVariable('Host Cards',str(hostCards))
      if not customHostMarker:
         daemonCard.markers[mdict['DaemonMU']] -= count
         if re.search(r'Daemon',fetchProperty(programCard, 'Keywords')): # If it's a daemon, we do not want to give it the same daemon token, as that's going to be reused for other programs and we do not want that.
            TokensX('Put{}Daemon Hosted MU-isSilent'.format(count), '', programCard)
         else: programCard.markers[mdict['DaemonMU']] += count
      else:
         daemonCard.markers[customHostMarker] -= 1 # If this a forced host, the host should have a special counter on top of it...
         programCard.markers[customHostMarker] += 1 # ...that we move to the hosted program to signify it's hosted
         Autoscripts = CardsAS.get(daemonCard.model,'').split('||')
         debugNotify("Daemon Autoscripts found = {}".format(Autoscripts))
         for autoS in Autoscripts:
            markersRegex = re.search(r'onHost:(.*)',autoS)            
            if markersRegex:
               debugNotify("markersRegex groups = {}".format(markersRegex.groups()))
               for autoS in markersRegex.group(1).split('$$'):
                  redirect(autoS, programCard, announceText = None, notificationType = 'Quick', X = 0)
                  #TokensX(markersRegex.group(1),'',programCard)
            else: debugNotify("No onHost scripts found in {}".format(autoS))
      if customHostMarker and customHostMarker[0] == 'Scheherazade Hosted': pass
      else: programCard.owner.MU += count # We return the MUs the card would be otherwise using.
      if not silent: notify("{} installs {} into {}".format(me,programCard,daemonCard))
   debugNotify("<<< possess(){}", 3) #Debug   
#------------------------------------------------------------------------------
# Switches
#------------------------------------------------------------------------------

def switchAutomation(type,command = 'Off'):
   debugNotify(">>> switchAutomation(){}".format(extraASDebug())) #Debug
   global Automations
   if (Automations[type] and command == 'Off') or (not Automations[type] and command == 'Announce'):
      notify ("--> {}'s {} automations are OFF.".format(me,type))
      if command != 'Announce': Automations[type] = False
   else:
      notify ("--> {}'s {} automations are ON.".format(me,type))
      if command != 'Announce': Automations[type] = True
   
def switchPlayAutomation(group,x=0,y=0):
   debugNotify(">>> switchPlayAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Play, Score and Rez')
   
def switchStartEndAutomation(group,x=0,y=0):
   debugNotify(">>> switchStartEndAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Start/End-of-Turn')

def switchDMGAutomation(group,x=0,y=0):
   debugNotify(">>> switchDMGAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Damage')

def switchPreventDMGAutomation(group,x=0,y=0):
   debugNotify(">>> switchDMGAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Damage Prevention')

def switchTriggersAutomation(group,x=0,y=0):
   debugNotify(">>> switchTriggersAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Triggers')
   
def switchWinForms(group,x=0,y=0):
   debugNotify(">>> switchWinForms(){}".format(extraASDebug())) #Debug
   switchAutomation('WinForms')
   
def switchUniCode(group,x=0,y=0,command = 'Off'):
   debugNotify(">>> switchUniCode(){}".format(extraASDebug())) #Debug
   global UniCode
   if UniCode and command != 'On':
      whisper("Credits and Clicks will now be displayed as normal ASCII.".format(me))
      UniCode = False
   else:
      whisper("Credits and Clicks will now be displayed as Unicode.".format(me))
      UniCode = True

def switchSounds(group,x=0,y=0):
   debugNotify(">>> switchSounds(){}".format(extraASDebug())) #Debug
   if getSetting('Sounds', True):
      setSetting('Sounds', False)
      whisper("Sound effects have been switched off")
   else:
      setSetting('Sounds', True)
      whisper("Sound effects have been switched on")
        

def remoteAskQA():
   mute()
   switchQuickAccess(remoted = True)
#------------------------------------------------------------------------------
# Help functions
#------------------------------------------------------------------------------

def HELP_TurnStructure(group,x=0,y=0):
   table.create('8b4f0c4d-4e4a-4d7f-890d-936ef37c8600', x, y, 1)
def HELP_CorpActions(group,x=0,y=0):
   table.create('881ccfad-0da9-4ca8-82e6-29c524f15a7c', x, y, 1)
def HELP_RunnerActions(group,x=0,y=0):
   table.create('6b3c394a-411f-4a1c-b529-9a8772a96db9', x, y, 1)
def HELP_RunAnatomy(group,x=0,y=0):
   table.create('db60308d-0d0e-4891-9954-7c600a7389e1', x, y, 1)
def HELP_RunStructure(group,x=0,y=0):
   table.create('51c3a293-3923-49ee-8c6f-b8c41aaba5f3', x, y, 1)


#------------------------------------------------------------------------------
# Button functions
#------------------------------------------------------------------------------

def BUTTON_Access(group = None,x=0,y=0):
   global AccessBtnNextChoice # Using a global var to avoid running the slow random function
   mute()
   AccessMsgs = ["--- Alert: Unauthorized Access Imminent!", 
                 "--- Alert: Runner entry detected!",
                 "--- Alert: Firewalls breached!",
                 "--- Alert: Intrusion in progress!"]
   #AccessTXT = AccessMsgs[rnd(0,len(AccessMsgs) - 1)]
   AccessTXT = AccessMsgs[AccessBtnNextChoice]
   AccessBtnNextChoice += 1
   if AccessBtnNextChoice >= len(AccessMsgs): AccessBtnNextChoice = 0
   notify(AccessTXT + "\n-- {} is about to gain access. Corporate React?".format(me))
   setGlobalVariable('accessAttempts',str(num(getGlobalVariable('accessAttempts')) + 1))  # The runner using the Button counts for an access Attempt. After 3 of them, the runner can bypass an unresponsive corp.
   playButtonSound('Access')

def BUTTON_NoRez(group = None,x=0,y=0):  
   notify("--- {} does not rez approached ICE".format(me))
   playButtonSound('NoRez')

def BUTTON_OK(group = None,x=0,y=0):
   notify("--- {} has no further reactions.".format(me))
   if re.search(r'running',getGlobalVariable('status')) and ds == 'corp': setGlobalVariable('Access','GRANTED')
   playButtonSound('OK')

def BUTTON_Wait(group = None,x=0,y=0):  
   notify("--- Wait! {} wants to react.".format(me))
   playButtonSound('Wait')
#------------------------------------------------------------------------------
#  Online Functions
#------------------------------------------------------------------------------

def versionCheck():
   debugNotify(">>> versionCheck()") #Debug
   global startupMsg
   me.setGlobalVariable('gameVersion',gameVersion)
   debugNotify("<<< versionCheck()", 3) #Debug

def initGame(): # A function which prepares the game for online submition
   debugNotify(">>> initGame()") #Debug
   if getGlobalVariable('gameGUID') != 'None': return #If we've already grabbed a GUID, then just use that.
   (gameInit, initCode) = webRead('http://84.205.248.92/slaghund/init.slag',3000)
   if initCode != 200:
      #whisper("Cannot grab GameGUID at the moment!") # Maybe no need to inform players yet.
      return
   debugNotify("{}".format(gameInit), 2) #Debug
   GUIDregex = re.search(r'([0-9a-f-]{36}).*?',gameInit)
   if GUIDregex: setGlobalVariable('gameGUID',GUIDregex.group(1))
   else: setGlobalVariable('gameGUID','None') #If for some reason the page does not return a propert GUID, we won't record this game.
   setGlobalVariable('gameEnded','False')
   debugNotify("<<< initGame()", 3) #Debug
   
def reportGame(result = 'AgendaVictory'): # This submits the game results online.
   delayed_whisper("Please wait. Submitting Game Stats...")     
   debugNotify(">>> reportGame()") #Debug
   GUID = getGlobalVariable('gameGUID')
   if GUID == 'None' and debugVerbosity < 0: return # If we don't have a GUID, we can't submit. But if we're debugging, we go through.
   gameEnded = getGlobalVariable('gameEnded')
   if gameEnded == 'True':
     if not confirm("Your game already seems to have finished once before. Do you want to change the results to '{}' for {}?".format(result,me.name)): return
   playGameEndSound(result)
   PLAYER = me.name # Seeting some variables for readability in the URL
   id = getSpecial('Identity',me)
   IDENTITY = id.Subtitle.replace(',','').replace('.','').replace('#','').replace('@','').replace('#','')
   RESULT = result
   GNAME = currentGameName()
   LEAGUE = getGlobalVariable('League')
   if result == 'Flatlined' or result == 'Conceded' or result == 'DeckDefeat' or result == 'AgendaDefeat': WIN = 0
   else: WIN = 1
   SCORE = me.counters['Agenda Points'].value
   deckStats = eval(me.getGlobalVariable('Deck Stats'))
   debugNotify("Retrieved deckStats ", 2) #Debug
   debugNotify("deckStats = {}".format(deckStats), 2) #Debug
   INFLUENCE = deckStats[0]
   CARDSNR = deckStats[1]
   AGENDASNR = deckStats[2]
   TURNS = turn
   VERSION = gameVersion
   debugNotify("About to report player results online.", 2) #Debug
   if (turn < 1 or len(players) == 1) and debugVerbosity < 1:
      notify(":::ATTENTION:::Game stats submit aborted due to number of players ( less than 2 ) or turns played (less than 1)")
      return # You can never win before the first turn is finished and we don't want to submit stats when there's only one player.
   if debugVerbosity < 1: # We only submit stats if we're not in debug mode
      (reportTXT, reportCode) = webRead('http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}'.format(GUID,PLAYER,IDENTITY,RESULT,SCORE,INFLUENCE,TURNS,CARDSNR,AGENDASNR,VERSION,WIN,LEAGUE,GNAME),10000)
   else: 
      if confirm('Report URL: http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}\n\nSubmit?'.format(GUID,PLAYER,IDENTITY,RESULT,SCORE,INFLUENCE,TURNS,CARDSNR,AGENDASNR,VERSION,WIN,LEAGUE,GNAME)):
         (reportTXT, reportCode) = webRead('http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}'.format(GUID,PLAYER,IDENTITY,RESULT,SCORE,INFLUENCE,TURNS,CARDSNR,AGENDASNR,VERSION,WIN,LEAGUE,GNAME),10000)
         notify('Report URL: http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}\n\nSubmit?'.format(GUID,PLAYER,IDENTITY,RESULT,SCORE,INFLUENCE,TURNS,CARDSNR,AGENDASNR,VERSION,WIN,LEAGUE,GNAME))
   try:
      if reportTXT != "Updating result...Ok!" and debugVerbosity >=0: whisper("Failed to submit match results") 
   except: pass
   # The victorious player also reports for their enemy
   enemyPL = ofwhom('-ofOpponent')
   ENEMY = enemyPL.name
   enemyIdent = getSpecial('Identity',enemyPL)
   E_IDENTITY = enemyIdent.Subtitle.replace(',','').replace('.','').replace('#','').replace('@','').replace('#','')
   debugNotify("Enemy Identity Name: {}".format(E_IDENTITY), 2) #Debug
   if result == 'FlatlineVictory': 
      E_RESULT = 'Flatlined'
      E_WIN = 0
   elif result == 'Flatlined': 
      E_RESULT = 'FlatlineVictory'
      E_WIN = 1
   elif result == 'Conceded': 
      E_RESULT = 'ConcedeVictory'
      E_WIN = 1  
   elif result == 'DeckDefeat': 
      E_RESULT = 'DeckVictory'
      E_WIN = 1  
   elif result == 'AgendaVictory': 
      E_RESULT = 'AgendaDefeat'
      E_WIN = 0
   elif result == 'AgendaDefeat': 
      E_RESULT = 'AgendaVictory'
      E_WIN = 1
   else: 
      E_RESULT = 'Unknown'
      E_WIN = 0
   E_SCORE = enemyPL.counters['Agenda Points'].value
   debugNotify("About to retrieve E_deckStats", 2) #Debug
   E_deckStats = eval(enemyPL.getGlobalVariable('Deck Stats'))
   debugNotify("E_deckStats = {}".format(E_deckStats), 2) #Debug
   E_INFLUENCE = E_deckStats[0]
   E_CARDSNR = E_deckStats[1]
   E_AGENDASNR = E_deckStats[2]
   if ds == 'corp': E_TURNS = turn - 1 # If we're a corp, the opponent has played one less turn than we have.
   else: E_TURNS = turn # If we're the runner, the opponent has played one more turn than we have.
   debugNotify("About to report enemy results online.", 2) #Debug
   if debugVerbosity < 1: # We only submit stats if we're not debugging
      (EreportTXT, EreportCode) = webRead('http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}'.format(GUID,ENEMY,E_IDENTITY,E_RESULT,E_SCORE,E_INFLUENCE,E_TURNS,E_CARDSNR,E_AGENDASNR,VERSION,E_WIN,LEAGUE,GNAME),10000)
   setGlobalVariable('gameEnded','True')
   notify("Thanks for playing. Please submit any bugs or feature requests on github.\n-- https://github.com/db0/Android-Netrunner-OCTGN/issues")
   notify("   \n =+= Please consider supporting the development of this plugin\n =+= http://www.patreon.com/db0\n")
   debugNotify("<<< reportGame()", 3) #Debug

def setleague(group = table, x=0,y=0, manual = True):
   debugNotify(">>> setleague()") #Debug
   mute()
   league = getGlobalVariable('League')
   origLeague = league
   debugNotify("global var = {}".format(league))
   if league == '': # If there is no league set, we attempt to find out the league name from the game name
      for leagueTag in knownLeagues:
         if re.search(r'{}'.format(leagueTag),currentGameName()): league = leagueTag
   debugNotify("League after automatic check: {}".format(league))
   if manual:
      if not confirm("Do you want to set this match to count for an active league\n(Pressing 'No' will unset this match from all leagues)"): league = ''
      else:
         choice = SingleChoice('Please Select One the Active Leagues', [knownLeagues[leagueTag] for leagueTag in knownLeagues])
         if choice != None: league = [leagueTag for leagueTag in knownLeagues][choice]
   debugNotify("League after manual check: {}".format(league))
   debugNotify("Comparing with origLeague: {}".format(origLeague))
   if origLeague != league:
      if manual: 
         if league ==  '': notify("{} sets this match as casual".format(me))
         else: notify("{} sets this match to count for the {}".format(me,knownLeagues[league]))
      elif league != '': notify(":::LEAGUE::: This match will be recorded for the the {}. (press Ctrl+Alt+L to unset)".format(knownLeagues[league]))
   elif manual: 
         if league == '': delayed_whisper("Game is already casual.")
         else: delayed_whisper("Game already counts for the {}".format(me,knownLeagues[league]))
   setGlobalVariable('League',league)
   debugNotify(">>> setleague() with league: {}".format(league)) #Debug

def concede(group=table,x=0,y=0):
   mute()
   if confirm("Are you sure you want to concede this game?"): 
      reportGame('Conceded')
      notify("{} has conceded the game".format(me))
   else: 
      notify("{} was about to concede the game, but thought better of it...".format(me))
#------------------------------------------------------------------------------
# Debugging
#------------------------------------------------------------------------------
   

def ShowDicts():
   if debugVerbosity < 0: return
   notify("Stored_Names:\n {}".format(str(Stored_Name)))
   notify("Stored_Types:\n {}".format(str(Stored_Type)))
   notify("Stored_Costs:\n {}".format(str(Stored_Cost)))
   notify("Stored_Keywords: {}".format(str(Stored_Keywords)))
   debugNotify("Stored_AA: {}".format(str(Stored_AutoActions)), 4)
   debugNotify("Stored_AS: {}".format(str(Stored_AutoScripts)), 4)
   notify("installedCounts: {}".format(str(installedCount)))

def DebugCard(card, x=0, y=0):
   whisper("Stored Card Properties\
          \n----------------------\
          \nStored Name: {}\
          \nPrinted Name: {}\
          \nStored Type: {}\
          \nPrinted Type: {}\
          \nStored Keywords: {}\
          \nPrinted Keywords: {}\
          \nCost: {}\
          \nCard ID: {}\
          \n----------------------\
          ".format(Stored_Name.get(card._id,'NULL'), card.Name, Stored_Type.get(card._id,'NULL'), card.Type, Stored_Keywords.get(card._id,'NULL'), card.Keywords, Stored_Cost.get(card._id,'NULL'),card._id))
   if debugVerbosity >= 4: 
      #notify("Stored_AS: {}".format(str(Stored_AutoScripts)))
      notify("Downloaded AA: {}".format(str(CardsAA)))
      notify("Card's AA: {}".format(CardsAA.get(card.model,'???')))
   storeProperties(card, True)
   if Stored_Type.get(card._id,'?') != 'ICE': card.orientation = Rot0
   
def extraASDebug(Autoscript = None):
   if Autoscript and debugVerbosity >= 3: return ". Autoscript:{}".format(Autoscript)
   else: return ''

def ShowPos(group, x=0,y=0):
   if debugVerbosity >= 1: 
      notify('x={}, y={}'.format(x,y))
      
def ShowPosC(card, x=0,y=0):
   if debugVerbosity >= 1: 
      notify(">>> ShowPosC(){}".format(extraASDebug())) #Debug
      x,y = card.position
      notify('card x={}, y={}'.format(x,y))      
        
def testHandRandom():
   if confirm("Run Hand random alg?"):
      randomsList = []
      notify("About to fill list")
      for iter in range(len(me.hand)): randomsList.append(0)
      notify("about to iter 100")
      for i in range(500):
         c = me.hand.random()
         for iter in range(len(me.hand)):            
            if c == me.hand[iter]: 
               randomsList[iter] += 1
               break
      notify("randomsList: {}".format(randomsList))
