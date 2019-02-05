import fp
import bot_bench
import ccob
import bot
import os
import time
from pd import PhotodiodeReadout

def symlink(fileList, symdir, acqType, imageType, testSeqNumber):
   ''' Create symlinks for created FITS files, based on the specification here:

       https://confluence.slac.stanford.edu/x/B244Dg
   '''
   if not fileList: # Indicates --nofits option was used
      return
   print "Saved %d FITS files to %s" % (fileList.size(),fileList.getCommonParentDirectory())
   if symdir:
      symname = "%s/%s_%s-%03d" % (symdir, acqType, imageType, testSeqNumber)
      if not os.path.exists(symdir): 
         os.makedirs(symdir)
      os.symlink(fileList.getCommonParentDirectory().toString(), symname)
      print "Symlinked from %s" % symname; 
   
def computeExposureTime(ndFilter, wlFilter, e_per_pixel):
   # TODO: Use per-filter config file to compute exposure
   return float(e_per_pixel)/100.0

def do_bias(options):
   print "bias called %s" % options
   count = int(options.get('count','10'))
   biasSeqNumber = 0
   for i in range(count):
      fitsHeaderData = {'ExposureTime': 0, 'TestType': 'BIAS', 'ImageType': 'BIAS', 'TestSeqNum': biasSeqNumber}
      imageName,fileList = fp.takeBias(fitsHeaderData)
      symlink(fileList, options['symlink'], 'bias', 'bias', biasSeqNumber)
      biasSeqNumber += 1

# This is what Seth's document calls fe55+flat, but Aaron's config calls FE55
def do_fe55(options):
   print "fe55 called %s" % options
   # of biases per fe55 image
   bcount = int(options.get('bcount','1'))
   flats = options.get('flat').replace('\n','').split(',')
   (fe55exposure, fe55count) = options.get('count').split()
   fe55exposure = float(fe55exposure)
   fe55count = int(fe55count)
   fe55SeqNumber = 0
   
   for flat in flats:
       filter,e_per_pixel = flat.split()
       exposure = computeExposureTime(None, filter, e_per_pixel)	
       print "exp %s filter %s" % (exposure,filter)   
       def exposeCommand(): 
          bot_bench.openShutter(exposure) # Flat
          bot_bench.openFe55Shutter(fe55exposure) # Fe55

       bot_bench.setColorFilter(filter)

       for f in range(fe55count):  
          for b in range(bcount):
            fitsHeaderData = {'ExposureTime': 0, 'TestType': 'FE55_FLAT', 'ImageType': 'BIAS', 'TestSeqNum': fe55SeqNumber}
            imageName,fileList = fp.takeBias(fitsHeaderData)
            symlink(fileList, options['symlink'], 'fe55_flat', 'bias', fe55SeqNumber)
            fe55SeqNumber += 1
            
            fitsHeaderData = {'ExposureTime': exposure, 'ExposureTime2': fe55exposure, 'TestType': 'FE55_FLAT', 'ImageType': 'FE55', 'TestSeqNum': fe55SeqNumber}
            imageName,fileList = fp.takeExposure(exposeCommand, fitsHeaderData)
            symlink(fileList, options['symlink'], 'fe55_flat', '%s_flat_%s' % (filter,e_per_pixel) , fe55SeqNumber)
            fe55SeqNumber += 1


def do_dark(options):
   print "dark called %s" % options
   # of biases per dark image
   bcount = int(options.get('bcount','1'))
   darks = options.get('dark').replace('\n','').split(',')
   darkSeqNumber = 0

   for dark in darks:
      integration,count = dark.split()
      integration = float(integration)
      count = int(count)
      exposeCommand = lambda: time.sleep(integration)

      for d in range(count):
         for b in range(bcount):
            fitsHeaderData = {'ExposureTime': 0, 'TestType': 'DARK', 'ImageType': 'BIAS', 'TestSeqNum': darkSeqNumber}
            imageName,fileList = fp.takeBias(fitsHeaderData)
            symlink(fileList, options['symlink'], 'dark', 'bias', darkSeqNumber)
            darkSeqNumber += 1
            
         fitsHeaderData = {'ExposureTime': integration, 'TestType': 'DARK', 'ImageType': 'DARK', 'TestSeqNum': darkSeqNumber}
         imageName,fileList = fp.takeExposure(exposeCommand, fitsHeaderData)
         symlink(fileList, options['symlink'], 'dark', 'dark', darkSeqNumber)
         darkSeqNumber += 1


def do_persistence(options):
   print "persistence called %s" % options

def do_flat(options):
   optics = False
   print "flat called %s" % options
   bcount = int(options.get('bcount','1'))
   wl = options.get('wl')
   if optics :
       bot_bench.setColorFilter(wl)
   flats = options.get('flat').replace('\n','').split(',')
   flatSeqNumber = 0
   for flat in flats:
       e_per_pixel,filter = flat.split()
       exposure = computeExposureTime(filter, wl, e_per_pixel)	
       print "exp %s filter %s" % (exposure,filter)   
       if optics :
           bot_bench.setNDFilter(filter)
       
       for i in range(bcount):
          fitsHeaderData = {'ExposureTime': 0, 'TestType': 'FLAT', 'ImageType': 'BIAS', 'TestSeqNum': flatSeqNumber}
          imageName,fileList = fp.takeBias(fitsHeaderData)
          symlink(fileList, options['symlink'], 'flat', 'bias', flatSeqNumber)
          flatSeqNumber += 1
          
       if optics :
           exposeCommand = lambda: bot_bench.openShutter(exposure)
# the following is just for testing
       else :
           exposeCommand = lambda: time.sleep(exposure)

       for pair in range(2):
          # Create photodiode readout handler.
          pd_readout = PhotodiodeReadout(exposure)

          pd_readout.start_accumulation()

          fitsHeaderData = {'ExposureTime': exposure, 'TestType': 'FLAT', 'ImageType': 'FLAT', 'TestSeqNum': flatSeqNumber}
          imageName,fileList = fp.takeExposure(exposeCommand, fitsHeaderData)

          pd_readout.write_readings(fileList.getCommonParentDirectory().toString(), flatSeqNumber, pair)

          symlink(fileList, options['symlink'], 'flat', '%s_%s_flat%d' % (wl,e_per_pixel,pair), flatSeqNumber)
          flatSeqNumber += 1

def takeFlat(bcount,ndFilter,wlFilter,e_per_pixel,testType,imgType, counter):
   for i in range(bcount):
      fitsHeaderData = {'ExposureTime': 0, 'TestType': testType, 'ImageType': 'BIAS', 'TestSeqNum': counter}
      imageName,fileList = fp.takeBias(fitsHeaderData)
      symlink(fileList, options['symlink'], testType.lower(), 'bias', counter)
      counter += 1
          
   exposeCommand = lambda: bot_bench.openShutter(exposure)
   fitsHeaderData = {'ExposureTime': exposure, 'TestType': testType, 'ImageType': 'FLAT', 'TestSeqNum': counter}
   imageName,fileList = fp.takeExposure(exposeCommand, fitsHeaderData)
   symlink(fileList, options['symlink'], testType.lower(), imgType, counter)
   counter += 1   

def do_sflat(options):
   print "superflat called %s" % options
   bcount = int(options.get('bcount','1'))
   sflats = options.get('sflat').replace('\n','').split(',')
   seqno = Counter()
   for sflat in sflats:
       wlFilter,e_per_pixel,count,ndFilter = sflat.split()     
       takeFlat(bcount,ndFilter,wlFilter,e_per_pixel,'SFLAT','flat_%s_%s' % (wlFilter,e_per_pixel), seqno)

def do_lambda(options):
   print "lambda called %s" % options
   bcount = int(options.get('bcount','1'))
   imcount = int(options.get('imcount', 1))
   lambdas = options.get('lambda').replace('\n','').split(',')
   lambdaSeqNumber = 0
   for lamb in lambdas:
       wlFilter,e_per_pixel,ndFilter = lamb.split()
       exposure = computeExposureTime(ndFilter, wlFilter, e_per_pixel)		
       print "exp %s wlFilter %s ndFilter %s" % (exposure,wlFilter,ndFilter)   
       
       for i in range(bcount):
          fitsHeaderData = {'ExposureTime': 0, 'TestType': 'LAMBDA', 'ImageType': 'BIAS', 'TestSeqNum': lambdaSeqNumber}
          imageName,fileList = fp.takeBias(fitsHeaderData)
          symlink(fileList, options['symlink'], 'lambda', 'bias', lambdaSeqNumber)
          lambdaSeqNumber += 1
          
       exposeCommand = lambda: bot_bench.openShutter(exposure)
       fitsHeaderData = {'ExposureTime': exposure, 'TestType': 'LAMBDA', 'ImageType': 'FLAT', 'TestSeqNum': lambdaSeqNumber}
       imageName,fileList = fp.takeExposure(exposeCommand, fitsHeaderData)
       symlink(fileList, options['symlink'], 'lambda', 'flat_%s_%s' % (wlFilter,e_per_pixel), lambdaSeqNumber)
       lambdaSeqNumber += 1

def do_ccob(options):
   print "ccob called %s" % options
   bcount = int(options.get('bcount','1'))
   imcount = int(options.get('imcount','1'))
   exposures = options.get('expose').replace('\n','').split(',')
   points = options.get('point').replace('\n','').split(',')
   for point in points:
      (x,y) = [float(x) for x in point.split()]
      print (x,y)
      for exposure in exposures:
         (led,current,duration) = exposure.split()
         current = float(current)
         duration = float(duration)
         exposeCommand = lambda: ccob.fireLED(led,current,duration)
         for i in range(imcount):
            for b in range(bcount):
               imageName,fileList = fp.takeBias()
               symlink(options,imageName,fileList,'BIAS')
            imageName,fileList = fp.takeExposure(exposeCommand)
            symlink(options,imageName,fileList,'CCOB')

def do_xtalk(options):
   print "xtalk called %s" % options
   bcount = int(options.get('bcount', '1'))
   imcount = int(options.get('imcount', '1'))
   xoffset = float(options.get('xoffset'))
   yoffset = float(options.get('yoffset'))
   exposures = options.get('expose').replace('\n','').split(',')
   points = options.get('point').replace('\n', '').split(',')
   bot.setLampOffset(xoffset, yoffset)
   xtalkSeqNumber = 0
   for point in points:
      (x,y) = [float(x) for x in point.split()]
      bot.moveTo(x,y)
      for exposure in exposures:
         exposure = float(exposure)

         for b in range(bcount):
            fitsHeaderData = {'ExposureTime': 0, 'TestType': 'XTALK', 'ImageType': 'BIAS', 'TestSeqNum': xtalkSeqNumber}
            imageName, fileList = fp.takeBias(fitsHeaderData)
            symlink(fileList,options['symlink'], 'XTALK', 'BIAS',xtalkSeqNumber)

         exposeCommand = lambda: bot_bench.openShutter(exposure)
         for i in range(imcount):
            fitsHeaderData = {'ExposureTime': exposure, 'TestType': 'XTALK', 'ImageType': "%03.1f_%03.1f_%03.1f" % (x,y,exposure), 'TestSeqNum': xtalkSeqNumber}
            imageName,fileList = fp.takeExposure(exposeCommand,fitsHeaderData)
            symlink(fileList, options['symlink'], 'XTALK', "%03.1f_%03.1f_%03.1f" % (x,y,exposure), xtalkSeqNumber)
      xtalkSeqNumber += 1

def do_spot(options):
   print "spot called %s" % options
   bcount = int(options.get('bcount', '1'))
   imcount = int(options.get('imcount', '1'))
   xoffset = float(options.get('xoffset'))
   yoffset = float(options.get('yoffset'))
   mask = options.get('mask')
   bot_bench.setSpotFilter(mask)
   exposures = options.get('expose').replace('\n','').split(',')
   points = options.get('point').replace('\n', '').split(',')
   bot.setLampOffset(xoffset, yoffset)
   spotSeqNumber = 0 
   for point in points:
      (x,y) = [float(x) for x in point.split()]
      bot.moveTo(x,y)
      for exposure in exposures:
         exposure = float(exposure)

         for b in range(bcount):
            fitsHeaderData = {'ExposureTime': 0, 'TestType': 'SPOT', 'ImageType': 'BIAS', 'TestSeqNum': spotSeqNumber}
            imageName, fileList = fp.takeBias(fitsHeaderData)
            symlink(fileList,options['symlink'], 'SPOT', 'BIAS',spotSeqNumber)

         exposeCommand = lambda: bot_bench.openShutter(exposure)
         for i in range(imcount):
            fitsHeaderData = {'ExposureTime': exposure, 'TestType': 'SPOT', 'ImageType': "%03.1f_%03.1f_%s_%03.1f" % (x,y,mask,exposure), 'TestSeqNum': spotSeqNumber}
            imageName,fileList = fp.takeExposure(exposeCommand,fitsHeaderData)
            symlink(fileList, options['symlink'], 'SPOT', "%03.1f_%03.1f_%s_%03.1f" % (x,y,mask,exposure), spotSeqNumber)
         spotSeqNumber += 1

def do_spot_flat(options):
   print "spot called %s" % options
   bcount = int(options.get('bcount', '1'))
   imcount = int(options.get('imcount', '1'))
   xoffset = float(options.get('xoffset'))
   yoffset = float(options.get('yoffset'))
   mask = options.get('mask')
   exposures = options.get('expose').replace('\n','').split(',')
   points = options.get('point').replace('\n', '').split(',')
   bot.setLampOffset(xoffset, yoffset)
   seqNumber = 0 
   for point in points:
      (x,y) = [float(x) for x in point.split()]
      bot.moveTo(x,y)
      for exposure in exposures:
         (exposure_1, exposure_2) = exposure.split()
         exposure_1 = float(exposure_1)
         exposure_2 = float(exposure_2)

         for b in range(bcount):
            fitsHeaderData = {'ExposureTime': 0, 'TestType': 'SPOT_FLAT', 'ImageType': 'BIAS', 'TestSeqNum': seqNumber}
            imageName, fileList = fp.takeBias(fitsHeaderData)
            symlink(fileList,options['symlink'], 'SPOT', 'BIAS',seqNumber)

         bot_bench.setSpotFilter(mask)
         exposeCommand = lambda: bot_bench.openShutter(exposure_1)
         secondExposeCommand = lambda: bot_bench.openShutter(exposure_2)
         for i in range(imcount):
            fitsHeaderData = {'ExposureTime': exposure_1, 'TestType': 'SPOT_FLAT', 
                              'ImageType': "%03.1f_%03.1f_FLAT_%s_%03.1f_%03.1f" % (x,y,mask,exposure_1, exposure_2), 'TestSeqNum': seqNumber}
            imageName,fileList = fp.takeMixedExposure(exposeCommand,fitsHeaderData, secondExposeCommand)
            symlink(fileList, options['symlink'], 'SPOT_FLAT', "%03.1f_%03.1f_FLAT_%s_%03.1f_%03.1f" % (x,y,mask,exposure_1, exposure_2), seqNumber)
         seqNumber += 1
