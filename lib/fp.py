#!/usr/bin/env ccs-script
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState
from org.lsst.ccs.subsystem.ocsbridge.sim.MCM import StandbyState
from java.time import Duration
from ccs import proxies
import jarray
from java.lang import String
#import bot_bench
import time
import array
import os
import time
import bot

CLEARDELAY=0.07
#CLEARDELAY=2.35

mcm = CCS.attachProxy("mcm") # this will be override by CCS.aliases
agentName = mcm.getAgentProperty("agentName")
imageTimeout = Duration.ofSeconds(60)

def sanityCheck():
   state = mcm.getState()
   alert = state.getState(AlertState)
   if alert!=AlertState.NOMINAL:
      print "WARNING: %s subsystem is in alert state %s" % ( agentName, alert )
   standby = state.getState(StandbyState)
   if standby==StandbyState.STANDBY:
      print "WARNING: %s subsystem is in %s, attempting to switch to STARTED" % ( agentName, standby )
      mcm.start("Normal")

def clear(n=1):
   if n == 0:
      return
   print "Clearing CCDs (%d)" % n
   fp.clear(n)
   fp.waitForSequencer(Duration.ofSeconds(2))

def takeBias(fitsHeaderData, annotation=None, locations=None):
   # TODO: This may not be the best way to take bias images
   # It may be better to define a takeBias command at the subsystem layer, since
   # this could skip the startIntegration/endIntegration and got straigh to readout
   return takeExposure(fitsHeaderData=fitsHeaderData, annotation=annotation, locations=locations)

def takeExposure(exposeCommand=None, fitsHeaderData=None, annotation=None, locations=None, clears=1):
   sanityCheck()
   print "Setting FITS headers %s" % fitsHeaderData

   imageName = mcm.allocateImageName() 
   print "Image name: %s" % imageName

   mcm.clearAndStartNamedIntegration(imageName, False, clears, annotation, locations, fitsHeaderData)
   # Sleep for 70 ms to allow for clear which is part of integrate to complete
   time.sleep(CLEARDELAY)

   if exposeCommand:
      extraData = exposeCommand()
      if extraData:
          mcm.setHeaderKeywords(extraData)
   mcm.endIntegration()
   mcm.waitForImage()
   return (imageName, None)
