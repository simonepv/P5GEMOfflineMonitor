#!/usr/bin/env python

import cx_Oracle
import ROOT
import os
import time
from datetime import datetime
from operator import itemgetter
from array import array
import argparse
from argparse import RawTextHelpFormatter
from sys import exit

#argparse
parser = argparse.ArgumentParser(description='''Retrieve from the database the vmon, imon and status informations \nfor qc8 and create a root file for the asked chambers. \nTo execute the code just type \n\npython StatusGEMP5HV.py \n\nand then insert the Start date and the End date of the monitor scan. \nPut the positions of chambers in the stand in the file P5GEMChosenChambers_HV.txt, made with aliases''', formatter_class=RawTextHelpFormatter)

args = parser.parse_args()

#import DB credentials
from gempython.utils.wrappers import envCheck
envCheck("GEM_P5_DB_NAME")
envCheck("GEM_P5_DB_ACCOUNT")

dbName = os.getenv("GEM_P5_DB_NAME")
dbAccount = os.getenv("GEM_P5_DB_ACCOUNT")

def main():
   #Reminder: in the DB the DeltaV between pins are saved, not the V from ground
   #-------------KIND OF MONITOR FLAG----------------------------------------
   monitorFlag = "HV"
   #monitorFlag = "LV"
   #-------------FILE WITH CHOSEN CHAMBERS------------------------------------
   chambersFileName = "P5GEMChosenChambers_sliceTest_HV.txt"

   #-------------FILE WITH EXISTING CHAMBERS-----------------------------------
   existingChambersFileName = "P5GEMExistingChambers_sliceTest.txt"

   #-------------FILE WITH MAPPING---------------------------------------------
   mappingFileName = "GEMP5MappingHV_sliceTest.txt"

   #-------------DEVELOPER SLICE TEST FLAG------------------------------------
   sliceTestFlag = 1 #1 uses the slice test mapping properties
                     #0 for real P5 conditions
   
   #-------------PREPARE START AND END DATE------------------------------------
   sta_period = raw_input("Insert UTC start time in format YYYY-MM-DD HH:mm:ss\n")
   type(sta_period)
   end_period = raw_input("Insert UTC end time in format YYYY-MM-DD HH:mm:ss\n")
   type(end_period)
   
   start=sta_period.replace(" ", "_")
   end=end_period.replace(" ", "_")
   start=start.replace(":", "-")
   end=end.replace(":", "-")

   #add ' at beginning and end to have the date in the format for the query
   sta_period = "'" + sta_period + "'"
   end_period = "'" + end_period + "'"
  
   startDate = datetime(int(start[:4]), int(start[5:7]), int(start[8:10]), int(start[11:13]), int(start[14:16]), int(start[17:]) )
   endDate   = datetime(int(end[:4]), int(end[5:7]), int(end[8:10]), int(end[11:13]), int(end[14:16]), int(end[17:]) )
 
   #-------------OUTPUT ROOT FILE------------------------------------------------
   fileName = "P5_GEM_HV_monitor_UTC_start_"+start+"_end_"+end+".root" 
   f1=ROOT.TFile( fileName,"RECREATE")

   #-------------DATES OF MAPPING CHANGE-----------------------------------------
   mappingChangeDate = []
   if sliceTestFlag == 1:
      firstMappingChange = datetime( 2017, 03, 18, 11, 54, 01 ) #trial date for SliceTestMapping
      secondMappingChange = datetime( 2018, 03, 05, 04, 07, 16 ) #trial date for SliceTestMapping

      mappingChangeDate.append( firstMappingChange )
      mappingChangeDate.append( secondMappingChange )

   if sliceTestFlag == 0:
      firstMappingChange = datetime( 2019, 10, 01, 00, 00, 01 )
      
      mappingChangeDate.append(firstMappingChange)

   lastDate = datetime( 2050, 01, 01, 00, 00, 01)
   mappingChangeDate.append( lastDate )
  
   #divide the monitor period in a number of periods equal to the number of mappings used
   periodBool = []
   numberOfMaps = len(mappingChangeDate)-1
  
   #fill periodBool with 0 to say that the map is not used, chnage than to one if used
   for mapIdx in range(numberOfMaps):
      periodBool.append(0)
   
   startIdx = -1
   endIdx   = -1
   
   #errors declaration
   if (startDate < mappingChangeDate[0] or endDate < mappingChangeDate[0]) :
      LowDateError = "ERROR: Date too early!! Dates must be greater than"+ str(mappingChangeDate[0]) 
      exit( LowDateError )
   if (startDate > endDate):
      SwapDateError = "ERROR: Start date greater than end date!!"
      exit( SwapDateError )

   #find the index for mapping start and end
   startIdx = -1
   endIdx = -1
   for dateIdx in range(len(mappingChangeDate)-1):
      if ( startDate > mappingChangeDate[dateIdx] and startDate <= mappingChangeDate[dateIdx+1] ):
         periodBool[dateIdx] = 1
         startIdx = dateIdx
      if ( endDate > mappingChangeDate[dateIdx] and endDate <= mappingChangeDate[dateIdx+1] ):
         periodBool[dateIdx] = 1
         endIdx = dateIdx

   #fill with one all the periods between start and end date
   if ( startIdx != endIdx and (endIdx-startIdx)>1 ):
      for fillPeriodIdx in range(endIdx-startIdx-1):
         periodBool[startIdx+1+fillPeriodIdx] = 1

   print ( periodBool ) 

   #----------MAPPING LENGHT---------------------------------------------------
   #if mapping is HV is 504 lies long, if LV is 144 lines long
   findMap = 0
   if (mappingFileName.find("HV") != -1):
      print("You are using a HV map")
      findMap=1
      mappingLength = 504
      if sliceTestFlag == 1:
         mappingLength = 14 
   if (mappingFileName.find("LV") != -1):
      print("You are using a LV map")
      findMap=-1
      mappingLength = 144 

   #-----------READ THE FILE WITH EXISTING CHAMBERS NAMES-----------------------
   ExistingChambers = []
   nExistingChambers = sum(1 for line in open(existingChambersFileName))
   print ("In "+ existingChambersFileName + " you have "+str(nExistingChambers)+" chambers")
   
   fileExChambers = open(existingChambersFileName, "r")
   fileExChambersLine = fileExChambers.readlines()

   for exChamber in range(int(nExistingChambers)):
      exChamberName = str(fileExChambersLine[exChamber])[:-1]
      ExistingChambers.append( exChamberName )      

   print( "ExistingChambers:", ExistingChambers ) 
   
   #------------READ THE FILE WITH CHOSEN CHAMBERS-------------------------------
   #name of chambers are take in input from the chambersFileName
   #count the number of chambers in the chambersFileName
   howManyChambers = sum(1 for line in open(chambersFileName)) 
   print ("In "+ chambersFileName + " you have "+str(howManyChambers)+" chambers")

   fileChambers = open(chambersFileName, "r")
   fileChambersLine = fileChambers.readlines()

   chamberList = []
   
   for chIdx in range(int(howManyChambers)):
      chamberName = str(fileChambersLine[chIdx])[:-1]
      #print chamberName
      #check that the name of the chamber is one of the existing
      ExistBool = False
      for existIdx in range(len(ExistingChambers)):
         if chamberName == ExistingChambers[ existIdx ]:
            ExistBool = True
      if ExistBool == False:
         print ("ERROR: WRONG NAME OF THE CHAMBER: the accepted names are in File: " + existingChambersFileName)
         return 1
      chamberList.append( chamberName )

   print ( chamberList )


   #------------READ THE MAPPING FILE--------------------------------------------
   fileMapping = open(mappingFileName, "r")
   fileMappingLine = fileMapping.readlines()

   #lines with start of mapping   
   startMappingLines=[]

   #mapping booleans with same lenght as periodBool
   boolMapping = []
   
   for i in range(len(periodBool)):
     boolMapping.append(False)

   lineCounter = 0
   for x in fileMappingLine:
      #find the : index
      columnIdx = x.index(":")
      #make a loop on every mapping
      for mapIdx in range(len(boolMapping)):
         if str(x)[:columnIdx] == ("Mapping"+str(mapIdx+1)): #the first map is Mapping1, notMapping0
            boolMapping[mapIdx] = True
            startMappingLines.append( int(fileMappingLine.index(x)) )
      lineCounter = lineCounter + 1

   #if the boolMapping is full of True means that all the maps have been inserted in the map file
   allCorrectMapFlag = True
   for mapIdx in range(len(boolMapping)):
      if boolMapping[mapIdx] == False:
         allCorrectMapFlag = False
         print( "ERROR: Map "+str(mapIdx+1)+" not charged correctely" )
         return 1
   
   if allCorrectMapFlag == True:
      for mapIdx in range(len(boolMapping)):
         boolMapping[mapIdx] = bool(periodBool[mapIdx])
         #print (boolMapping[mapIdx], periodBool[mapIdx])


   #print ( "MappingStartLines:", startMappingLines )
   #print ( "boolMapping:", boolMapping )

   #check that the periodBool is the same of boolMapping
   if boolMapping != periodBool:
      print("ERROR: boolMapping != periodBool") 
      return 1
   
   #----------FRONT MAPPING STRING----------------------------------------------
   column1 = fileMappingLine[0].index(":")
   subString1 = fileMappingLine[0][column1+1:]
   column2 = subString1.index(":")
   stringFrontDP = subString1[column2+2:-2]
   #print(stringFrontDP)  
 
   #------------CHARGE THE MAPPING-----------------------------------------------
   #store the mapping each in a dedicated vector
   allMappingList=[]
   for idxMap in range(len(boolMapping)):
      #recognise where a map starts
      oneMap = []
      for lineIdx in range(startMappingLines[idxMap]+1, startMappingLines[idxMap]+1+mappingLength):
         oneMap.append( stringFrontDP + fileMappingLine[lineIdx][:-1] )
      allMappingList.append(oneMap)

   #print ( allMappingList )

   #-------------CHOOSE THE NEEDED MAPPING LINES FOR EACH REQUESTED CHAMBER----
   allChosenChamberDPs = []
   
   #charge a DP only if the mapBoolean corresponding is True
   for chIdx in range(len(chamberList)): #loop on chosen chambers
      oneChamberDPs = []
      for allMapIdx in range(len(allMappingList)): #loop on all maps
         if boolMapping[allMapIdx]==0: #if the map is not used don't charge it
            continue
         for oneMapIdx in range(len(allMappingList[allMapIdx])): #loop on oneMap
            oneMapLine = allMappingList[allMapIdx][oneMapIdx]
            #print( "boolMapping:", boolMapping[allMapIdx], "chIdx:", chIdx, " chamber:" , chamberList[chIdx], " oneMapIdx:", oneMapLine )
            if (oneMapLine.find(chamberList[chIdx]) != -1):
               #print( "boolMapping:", boolMapping[allMapIdx], "chIdx:", chIdx, " chamber:" , chamberList[chIdx], " oneMapIdx:", oneMapLine, "FOUND" )
               column2Idx = oneMapLine.index(":",15)
               oneChamberDPs.append(oneMapLine[:column2Idx])
      allChosenChamberDPs.append(oneChamberDPs)
  
   #print("----------------------------------------------------------------------")
   #print("                            CALLED DPs                                ")
   #print("\n")
   #for chIdx in range(len(chamberList)):
   #   print ( chamberList[chIdx] ) 
   #   print ( allChosenChamberDPs[chIdx] )

   #------------DATABASE CONNECT------------------------------------------------
   db = cx_Oracle.connect( dbAccount+"@"+dbName )
   cur = db.cursor()
  
   #-----------FIND THE DP FROM THE ALIAS--------------------------------------
   #check that in the called period is used the same alias used in the file of chosen chambers to select the chamber (the alias to call a chmaber is a part of the alias string)
   for chIdx in range(len(chamberList)):
      for mapIdx in range(len(allMappingList)):#loop on maps
         if boolMapping[mapIdx]==False:
            continue
         matchAliasMap_AliasCalled = 0
         for lineIdx in range(len(allMappingList[mapIdx])):#loop inside a map
            oneLineMap = allMappingList[mapIdx][lineIdx]
            if (oneLineMap.find(chamberList[chIdx]) != -1):
               matchAliasMap_AliasCalled += 1
         if matchAliasMap_AliasCalled != 7: #in a map I have to have 7 matches, one for each HV channel of the chamber
            periodBoolInString = ""
            for perIdx in range(len(periodBool)):
               periodBoolInString = periodBoolInString + str(periodBool[perIdx]) + " "
               print("ERROR: In the asked period there is an incorrect number of matches\nbetween the ALIAS called in the file "+ chambersFileName + "and the ALIAS in file\n"+ mappingFileName+" in the maps used (look to vector periodBool:["+ periodBoolInString + "] to know\nwhich ones are used ). Match obtained: "+ str(matchAliasMap_AliasCalled) + "/7")
               return 1          
 
   #------------FIND IDs for each chamber---------------------------------------
   #table CMS_GEM_PVSS_COND.ALIASES contains SINCE, DPE_NAME, ALIAS
   #table CMS_GEM_PVSS_COND.DP_NAME2ID contains DPNAME and ID
   #for a data point there could be different IDs associated, depending on their
   #validity period

   #DPE_NAME has a dot at the end of channellXXX, DPNAME has not a dot

   allChosenChamberIDs=[]
  
   print("-------------------------------------------------------------------------") 
   print("                      CALLED DPs AND THEIR IDs                           ")
   for chIdx in range(len(chamberList)):
      oneChosenChamberIDs=[]
      for dpIdx in range(len(allChosenChamberDPs[chIdx])):
         query = "select ID, DPNAME from CMS_GEM_PVSS_COND.DP_NAME2ID where DPNAME='"+allChosenChamberDPs[chIdx][dpIdx]+"'"
         cur.execute(query)
         curID = cur
         for result in curID:
            dpID   = result[0]
            dpNAME = result[1]
            
            print( "chamber:", chamberList[chIdx], "ID", dpID, "DPNAME", dpNAME )
            #it seems there is only one ID(if more than one care about the time order of calls)         
            oneChosenChamberIDs.append(dpID)
      allChosenChamberIDs.append(oneChosenChamberIDs)
  
   print("ChosenIDs")
   for chIdx in range(len(chamberList)):
      print(chamberList[chIdx], allChosenChamberIDs[chIdx])

   #--------------RETRIEVE DATA FOR HV--------------------------------------------
   #table CMS_GEM_PVSS_COND.FWCAENCHANNELA1515 for HV
   #table CMS_GEM_PVSS_COND.FWCAENCHANNEL for LV

   #for each chamber I retrive data and then if one is NULL I don't save it
   #HV TABLE
   #describe CMS_GEM_PVSS_COND.FWCAENCHANNELA1515;
   # Name					   Null?    Type
   # ----------------------------------------- -------- ----------------------------
   #UPDATEID				   NOT NULL NUMBER(38)
   #DPID					    NUMBER
   #CHANGE_DATE					    TIMESTAMP(9)
   #DPE_STATUS					    NUMBER
   #DPE_POSITION				    NUMBER
   #ACTUAL_IMONREAL				    NUMBER
   #ACTUAL_IMON					    NUMBER
   #ACTUAL_VMON					    NUMBER
   #ACTUAL_STATUS				    NUMBER
   #ACTUAL_ISON					    NUMBER
   #ACTUAL_TEMP					    NUMBER
   #ACTUAL_IMONDET 				    NUMBER
   #SETTINGS_OFFORDER				    NUMBER
   #SETTINGS_ONORDER				    NUMBER

   #LV TABLE
   #SQL> describe CMS_GEM_PVSS_COND.FWCAENCHANNEL;
   #Name					   Null?    Type
   #----------------------------------------- -------- ----------------------------
   #UPDATEID				   NOT NULL NUMBER(38)
   #DPID					    NUMBER
   #CHANGE_DATE					    TIMESTAMP(9)
   #DPE_STATUS					    NUMBER
   #DPE_POSITION				    NUMBER
   #ACTUAL_VMON					    NUMBER
   #ACTUAL_ISON					    NUMBER
   #ACTUAL_IMON					    NUMBER
   #ACTUAL_OVC					    NUMBER
   #ACTUAL_TRIP					    NUMBER
   #ACTUAL_STATUS				    NUMBER
   #ACTUAL_TEMP					    NUMBER
   #ACTUAL_VCON					    NUMBER
   #ACTUAL_TEMPERATUREERROR			    NUMBER
   #ACTUAL_POWERFAIL				    NUMBER

   if monitorFlag == "HV": 
      tableData = "CMS_GEM_PVSS_COND.FWCAENCHANNELA1515"
   if monitorFlag == "LV":
      tableData = "CMS_GEM_PVSS_COND.FWCAENCHANNEL"

   stringWhatRetriveList     = ["imon", "vmon", "smon", "ison", "temp"]
   for chIdx in range(len(chamberList)):
      #create the first level of directories: one for each chamber
      chamberNameRootFile = chamberList[chIdx].replace("-", "_")
      firstDir = f1.mkdir(chamberNameRootFile)
      firstDir.cd()

      #put a counter to identify which channel I am looking to 
      #IF I CALL A CHAMBER I AM OBLIGED TO LOOK ALL THE SEVEN CHANNELS
      channelName = ["G3Bot", "G3Top", "G2Bot", "G2Top", "G1Bot", "G1Top", "Drift"]

      #for each chnnel of a chamber ther eis only one ID
      for channelIDIdx in range(len(allChosenChamberIDs[chIdx])):
         imonData = [] #store two Dates and Imon in pair (0th Date in millisecond from the first element stored, 1st Date as wanted by root, 2nd Imon)
         vmonData = [] #store two Dates and Vmon in pair
         smonData = [] #store two Dates and Status in pair
         isonData = [] #store two Dates and Ison in pair
         tempData = [] #store two Dates and Temp in pair

         queryAll = "select CHANGE_DATE, ACTUAL_IMON, ACTUAL_VMON, ACTUAL_STATUS, ACTUAL_ISON, ACTUAL_TEMP, ACTUAL_IMONREAL from " + tableData + " where DPID = " + str(allChosenChamberIDs[chIdx][channelIDIdx]) + " and CHANGE_DATE > to_date( " + sta_period + ", 'YYYY-MM-DD HH24:MI:SS') and CHANGE_DATE < to_date( " + end_period + ", 'YYYY-MM-DD HH24:MI:SS')"
         #print( queryAll ) 

         #queryAll = "select CHANGE_DATE, ACTUAL_IMON, ACTUAL_VMON, ACTUAL_STATUS, ACTUAL_ISON, ACTUAL_TEMP from CMS_GEM_PVSS_COND.FWCAENCHANNELA1515 where  DPID = 55 and CHANGE_DATE > to_date( '2018-04-01 00:00:00', 'YYYY-MM-DD HH24:MI:SS') and CHANGE_DATE < to_date ( '2018-05-01 00:00:00', 'YYYY-MM-DD HH24:MI:SS')"

         cur.execute(queryAll)
         curAllData = cur
         contData = 0
         for result in curAllData:
            #print (result)
            dateElem = result[0]
            imonElem = result[1]
            vmonElem = result[2]
            smonElem = result[3]
            isonElem = result[4] #it can be only 0 or 1
            tempElem = result[5] #in celcius degrees
            imonRealElem = result[6]

            #take the first Date
            if contData == 0:
               startTs = result[0]
               
            tot_secondsDate = (dateElem - startTs).total_seconds()
            #print("tot_secondsDate:", tot_secondsDate) #('tot_secondsDate:', 16512.532)

            #convert dateElem in a usable format
            dateElemStr = str(dateElem)  #2017-04-01 00:00:32.439000 
            #print("dateElemStr", dateElemStr)
            if (dateElemStr.find(".") != -1): #if dot found
               dotIdx = dateElemStr.index(".")
               dateNoMicro = dateElemStr[:dotIdx]
               micro = dateElemStr[dotIdx+1:] 
            else:                             #if dot not found
               dateNoMicro = dateElemStr
               micro = "000000"

            da1 = ROOT.TDatime( dateNoMicro )
            convertedDate = da1.Convert()            

            floatMicro = "0." + micro
            dateElemSQL = convertedDate + float(floatMicro)

            #ATTENTION: I use ACTUAL_IMONREAL only if I have no info from ACTUAL_IMON
            if imonElem is not None:       #imon
               tripleList = [ tot_secondsDate, dateElemSQL, imonElem ]
               imonData.append( tripleList )
            else:
               if imonRealElem is not None:
                  tripleList = [ tot_secondsDate, dateElemSQL, imonRealElem ]
                  imonData.append( tripleList )
            if vmonElem is not None:       #vmon
               tripleList = [ tot_secondsDate, dateElemSQL, vmonElem ]
               vmonData.append( tripleList )
            if smonElem is not None:       #smon          
               tripleList = [ tot_secondsDate, dateElemSQL, smonElem ]
               smonData.append( tripleList )
            if isonElem is not None:       #ison
               tripleList = [ tot_secondsDate, dateElemSQL, isonElem ]
               isonData.append( tripleList )
            if tempElem is not None:       #temp
               tripleList = [ tot_secondsDate, dateElemSQL, tempElem ]
               tempData.append( tripleList )
       
            contData = contData + 1

         #print("imonData", imonData)
         #print("vmonData", vmonData)
         #print("smonData", smonData)
         #print("isonData", isonData)
         #print("tempData", tempData)

         print( chamberList[chIdx]+ ": Not sorted lists created: WAIT PLEASE!!")

         #----------------SORT DATA-------------------------------------------------------
         #after collecting all data (we are inside the loop over chambers)
         #reorder data by date, the may not be in the correct time order
         #sort data in each of the seven channels

         imonSortList = sorted(imonData, key=lambda element: element[0]) #reorder using the internal list of imonData( element[0] is tot_secondsDate )
         vmonSortList = sorted(vmonData, key=lambda element: element[0])
         smonSortList = sorted(smonData, key=lambda element: element[0])
         isonSortList = sorted(isonData, key=lambda element: element[0])
         tempSortList = sorted(tempData, key=lambda element: element[0])
      
         for idx in range(len(imonSortList)):
            now = imonSortList[idx][0]
            after = imonSortList[idx][0]
            if now > after:
               print("ERROR: sort error in imonSortList")

         for idx in range(len(vmonSortList)):
            now = vmonSortList[idx][0]
            after = vmonSortList[idx][0]
            if now > after:
               print("ERROR: sort error in vmonSortList")

         for idx in range(len(smonSortList)):
            now = smonSortList[idx][0]
            after = smonSortList[idx][0]
            if now > after:
               print("ERROR: sort error in smonSortList")

         for idx in range(len(isonSortList)):
            now = isonSortList[idx][0]
            after = isonSortList[idx][0]
            if now > after:
               print("ERROR: sort error in isonSortList")

         for idx in range(len(tempSortList)):
            now = tempSortList[idx][0]
            after = tempSortList[idx][0]
            if now > after:
               print("ERROR: sort error in tempSortList")
      
         print("Lists sorted: WAIT PLAESE!!")

         #empty not sortedLists
         imonData = []
         vmonData = []
         smonData = []
         isonData = []
         tempData = []

         for idxElem in range(len(imonSortList)):
            secondAndThird = []
            secondAndThird.append(imonSortList[idxElem][1])
            secondAndThird.append(imonSortList[idxElem][2])
            imonData.append(secondAndThird)

         for idxElem in range(len(vmonSortList)):
            secondAndThird = []
            secondAndThird.append(vmonSortList[idxElem][1])
            secondAndThird.append(vmonSortList[idxElem][2])
            vmonData.append(secondAndThird)

         for idxElem in range(len(smonSortList)):
            secondAndThird = []
            secondAndThird.append(smonSortList[idxElem][1])
            secondAndThird.append(int(smonSortList[idxElem][2]))
            smonData.append(secondAndThird)

         for idxElem in range(len(isonSortList)):
            secondAndThird = []
            secondAndThird.append(isonSortList[idxElem][1])
            secondAndThird.append(isonSortList[idxElem][2])
            isonData.append(secondAndThird)

         for idxElem in range(len(tempSortList)):
            secondAndThird = []
            secondAndThird.append(tempSortList[idxElem][1])
            secondAndThird.append(tempSortList[idxElem][2])
            tempData.append(secondAndThird)
         
         print("Sorted lists filled!")
   
         #----------------CREATE HISTOGRAMS----------------------------------------------
         if monitorFlag == "HV":
            IMin = -20   #uA 
            IMax = 20    #uA
            NBinImon = int(IMax-IMin)
            IUnitMeasure = "I [uA]"
  
            VMin = -50   #V
            VMax = 800
            NBinVmon = int((VMax-VMin)/10)
 
            StatusMin = 0
            StatusMax = 4100
            NBinStatus = StatusMax
 
            IsonMin = -1
            IsonMax = 3
            NBinIson = int(IsonMax-IsonMin)
 
            TempMin = 0  #celsius
            TempMax = 100
            NBinTemp = TempMax

         if monitorFlag == "LV":
            IMin = -10  #A
            IMax = 10
            NBinImon = int(IMax-IMin)
            IUnitMeasure = "I [A]"
    
            VMin = -50  #V
            VMax = 200  #V
            NBinVmon = int((VMax-VMin)/10)
    
            StatusMin = 0
            StatusMax = 65536
            NBinStatus = StatusMax
            
            IsonMin = -1
            IsonMax = 3
            NBinIson = int(IsonMax-IsonMin)
    
            TempMin = 0 #celsius
            TempMax = 100
            NBinTemp = TempMax
    
         #declare histograms
         chamberNameRootFile = chamberList[chIdx].replace("-", "_")

         Imonh1 = ROOT.TH1F(monitorFlag+"_ImonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", monitorFlag+"_ImonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", NBinImon, IMin, IMax)	
         Vmonh1 = ROOT.TH1F(monitorFlag+"_VmonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", monitorFlag+"_VmonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", NBinVmon, VMin, VMax)	
         Smonh1 = ROOT.TH1F(monitorFlag+"_StatusChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", monitorFlag+"_StatusChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", NBinStatus, StatusMin, StatusMax)	
         Isonh1 = ROOT.TH1F(monitorFlag+"_IsonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", monitorFlag+"_IsonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", NBinIson, IsonMin, IsonMax)	
         Temph1 = ROOT.TH1F(monitorFlag+"_TempChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", monitorFlag+"_TempChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_TH1", NBinTemp, TempMin, TempMax)	
      
         #axis titles
         Imonh1.GetXaxis().SetTitle(IUnitMeasure)
         Imonh1.GetYaxis().SetTitle("counts")
         Vmonh1.GetXaxis().SetTitle("V [V]")
         Vmonh1.GetYaxis().SetTitle("counts")
         Smonh1.GetXaxis().SetTitle("Status code")
         Smonh1.GetYaxis().SetTitle("counts")
         Isonh1.GetXaxis().SetTitle("Ison status (0=OFF, 1=ON)")
         Isonh1.GetYaxis().SetTitle("counts")
         Temph1.GetXaxis().SetTitle("Temperature [Celsius degrees]")
         Temph1.GetYaxis().SetTitle("counts")

         #fill histograms: remember thet each row of Data has (Date, Value)
         for idxPoint in range(len(imonData)):
            Imonh1.Fill(imonData[idxPoint][1])
 
         for idxPoint in range(len(vmonData)):
            Vmonh1.Fill(vmonData[idxPoint][1])
 
         for idxPoint in range(len(smonData)):
            Smonh1.Fill(smonData[idxPoint][1])
 
         for idxPoint in range(len(isonData)):
            Isonh1.Fill(isonData[idxPoint][1])
 
         for idxPoint in range(len(tempData)):
            Temph1.Fill(tempData[idxPoint][1])

         #write TH1
         Imonh1.Write()
         Vmonh1.Write()
         Smonh1.Write()
         Isonh1.Write()
         Temph1.Write()

         #--------------------CREATE TGRAPHS-------------------------------------------
         #to create the TGraph I have to pass two lists: one with times and the other with values
         imonData_dates = array ( 'd' )
         vmonData_dates = array ( 'd' )
         smonData_dates = array ( 'd' )
         isonData_dates = array ( 'd' )
         tempData_dates = array ( 'd' )

         imonData_values = array ( 'd' )
         vmonData_values = array ( 'd' )
         smonData_values = array ( 'd' )
         isonData_values = array ( 'd' )
         tempData_values = array ( 'd' )

         for imonIdx in range(len(imonData)):
            imonData_dates.append(imonData[imonIdx][0])
            imonData_values.append(imonData[imonIdx][1])

         for vmonIdx in range(len(vmonData)):
            vmonData_dates.append(vmonData[vmonIdx][0])
            vmonData_values.append(vmonData[vmonIdx][1])

         for smonIdx in range(len(smonData)):
            smonData_dates.append(smonData[smonIdx][0])
            smonData_values.append(smonData[smonIdx][1])

         for isonIdx in range(len(isonData)):
            isonData_dates.append(isonData[isonIdx][0])
            isonData_values.append(isonData[isonIdx][1])

         for tempIdx in range(len(tempData)):
            tempData_dates.append(tempData[tempIdx][0])
            tempData_values.append(tempData[tempIdx][1])

         #in case there is nothing the TGraph gives error: put a dummy value
         dummyNumber = -999999999
         dummyPair = [0, dummyNumber]
         if len(imonData)==0: 
            imonData_dates.append(0)
            imonData_values.append(dummyNumber)
            imonData.append( dummyPair ) 
         if len(vmonData)==0:
            vmonData_dates.append(0)
            vmonData_values.append(dummyNumber) 
            vmonData.append( dummyPair ) 
         if len(smonData)==0:
            smonData_dates.append(0)
            smonData_values.append(dummyNumber) 
            smonData.append( dummyPair ) 
         if len(isonData)==0:
            isonData_dates.append(0)
            isonData_values.append(dummyNumber) 
            isonData.append( dummyPair ) 
         if len(tempData)==0:
            tempData_dates.append(0)
            tempData_values.append(dummyNumber) 
            tempData.append( dummyPair ) 

         #declare TGraphs
         Imontg1 = ROOT.TGraph(len(imonData),imonData_dates,imonData_values)
         Vmontg1 = ROOT.TGraph(len(vmonData),vmonData_dates,vmonData_values)
         Smontg1 = ROOT.TGraph(len(smonData),smonData_dates,smonData_values)
         Isontg1 = ROOT.TGraph(len(isonData),isonData_dates,isonData_values)
         Temptg1 = ROOT.TGraph(len(tempData),tempData_dates,tempData_values)

         #setting for TGraphs
         Imontg1.SetLineColor(2)
         Imontg1.SetLineWidth(4)
         Imontg1.SetMarkerColor(4)
         Imontg1.SetMarkerStyle(21)
         Imontg1.SetMarkerSize(1)

         Vmontg1.SetLineColor(2)
         Vmontg1.SetLineWidth(4)
         Vmontg1.SetMarkerColor(4)
         Vmontg1.SetMarkerStyle(21)
         Vmontg1.SetMarkerSize(1)

         Smontg1.SetLineColor(2)
         Smontg1.SetLineWidth(4)
         Smontg1.SetMarkerColor(4)
         Smontg1.SetMarkerStyle(21)
         Smontg1.SetMarkerSize(1)

         Isontg1.SetLineColor(2)
         Isontg1.SetLineWidth(4)
         Isontg1.SetMarkerColor(4)
         Isontg1.SetMarkerStyle(21)
         Isontg1.SetMarkerSize(1)

         Temptg1.SetLineColor(2)
         Temptg1.SetLineWidth(4)
         Temptg1.SetMarkerColor(4)
         Temptg1.SetMarkerStyle(21)
         Temptg1.SetMarkerSize(1)

         #TGraph names
         Imontg1.SetName(monitorFlag+"_ImonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")
         Vmontg1.SetName(monitorFlag+"_VmonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")
         Smontg1.SetName(monitorFlag+"_StatusChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")
         Isontg1.SetName(monitorFlag+"_IsonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")
         Temptg1.SetName(monitorFlag+"_TempChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")

         #TGraph title
         Imontg1.SetTitle(monitorFlag+"_ImonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")
         Vmontg1.SetTitle(monitorFlag+"_VmonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")
         Smontg1.SetTitle(monitorFlag+"_StatusChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")
         Isontg1.SetTitle(monitorFlag+"_IsonChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")
         Temptg1.SetTitle(monitorFlag+"_TempChamber"+chamberNameRootFile+"_"+channelName[channelIDIdx]+"_UTC_time")

         #Y axis
         if monitorFlag == "HV":
            currentBrak = "[uA]"
         if monitorFlag == "LV":
            currentBrak = "[A]"
         Imontg1.GetYaxis().SetTitle("Imon "+chamberNameRootFile+" "+channelName[channelIDIdx]+" "+currentBrak)
         Vmontg1.GetYaxis().SetTitle("Vmon "+chamberNameRootFile+" "+channelName[channelIDIdx]+" [V]")
         Smontg1.GetYaxis().SetTitle("Status code "+chamberNameRootFile+" "+channelName[channelIDIdx])
         Isontg1.GetYaxis().SetTitle("Ison code: 0=ON 1=OFF "+chamberNameRootFile+" "+channelName[channelIDIdx])
         Temptg1.GetYaxis().SetTitle("Temperature "+chamberNameRootFile+" "+channelName[channelIDIdx]+" [Celsius degrees]")

         #X axis
         Imontg1.GetXaxis().SetTimeDisplay(1)
         Vmontg1.GetXaxis().SetTimeDisplay(1)
         Smontg1.GetXaxis().SetTimeDisplay(1)
         Isontg1.GetXaxis().SetTimeDisplay(1)
         Temptg1.GetXaxis().SetTimeDisplay(1)

         Imontg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
         Vmontg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
         Smontg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
         Isontg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
         Temptg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")

         Imontg1.GetXaxis().SetLabelOffset(0.025)
         Vmontg1.GetXaxis().SetLabelOffset(0.025)
         Smontg1.GetXaxis().SetLabelOffset(0.025)
         Isontg1.GetXaxis().SetLabelOffset(0.025)
         Temptg1.GetXaxis().SetLabelOffset(0.025)

         #Write TGraph
         Imontg1.Write()
         Vmontg1.Write()
         Smontg1.Write()
         Isontg1.Write()
         Temptg1.Write()

         #----------------------TREE STATUS------------------------------------------------



































if __name__ == '__main__':
   main()

