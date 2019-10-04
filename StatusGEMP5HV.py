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














if __name__ == '__main__':
   main()

