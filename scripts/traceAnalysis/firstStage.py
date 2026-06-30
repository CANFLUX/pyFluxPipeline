from scripts.traceAnalysis.traceParameters import firstStageTrace
from scripts.database.database import database
from dataclasses import dataclass,field
from time import time
import pandas as pd
import numpy as np
import os

@dataclass(kw_only=True)
class firstStage(database):
    sites: list
    years: list = None

    def __post_init__(self):
        super().__post_init__()
        for siteID in self.sitesList:
            T1 = time()
            # load site configuration
            siteConfig = self.loadSiteConfiguration(siteID)
            # Assign all years if not otherwise specified            
            if self.years is None:
                if siteConfig.stopDate is None:
                    self.years = [i for i in range(siteConfig.startDate.year,self.currentYear+1)]
                else:
                    self.years = [i for i in range(siteConfig.startDate.year,self.stopDate.year+1)]
            # create timestamp spanning years
            posixYearIndex = self.posixYears(self.dataIntervalSeconds)
            startTime = posixYearIndex[posixYearIndex==self.years[0]].index.values[0]
            stopTime = posixYearIndex[posixYearIndex==self.years[-1]+1].index.values[0]
            posix_time = np.arange(startTime,stopTime,self.dataIntervalSeconds).astype('int64')
            timestamp = pd.to_datetime(posix_time,unit='s').tz_localize(self.timezone)

            # load firstStage instructions
            # ensure inputs conform to convention and replace arbitrary keys with desired variable names
            iniFirstStage = {}
            for value in siteConfig.ini['Processing']['FirstStage'].values():
                value = firstStageTrace.from_dict(value).to_dict()
                iniFirstStage[value['variableName']] = value
            # and for of desired types for raw inputs outputs
            dataTable = self.noDataTable(timestamp,{key:value['dtype'] for key,value in iniFirstStage.items()})
            dataTable[self.posixName] = posix_time

            # Load metadata for raw traces
            if 'preEvaluate' in siteConfig.ini['rawData'].keys():
                preEvaluate = siteConfig.ini['rawData'].pop('preEvaluate')
            else:
                preEvaluate = None
            metadataIn = {key: self.loadDict(os.path.join(self.projectPath,'Sites',siteID,'rawFiles',f'{key}.yml'))
                      for key in siteConfig.ini['rawData'].keys()}
            #get all dtypes and cast to full, empty array
            typeMap = {f"{key}.{k}":v['dtype'] for key in metadataIn.keys() for k,v in metadataIn[key]['traces'].items() if not v['ignore']}
            # create empty dataframe of desired types for raw inputs
            rawData = self.noDataTable(timestamp,typeMap)

            
           
            # Load raw traces
            dby = os.path.join(self.projectPath,'Database','YYYY',siteID,'raw')

            for key,value in metadataIn.items():
                if value['dataIntervalSeconds']<self.dataIntervalSeconds:
                    self.logError('Not setup for >30min freq yet')
                dbyPth = os.path.join(dby,key)
                dateRange = pd.to_datetime(value['dateRange'])
                if dateRange[0] < timestamp[0]:
                    dateRange = pd.to_datetime([timestamp[0],dateRange[1]])
                if dateRange[-1] > timestamp[-1]:
                    dateRange = pd.to_datetime([dateRange[0],timestamp[-1]])
                years = dateRange.year
                df = pd.concat([self.loadTraceFolder(dbyPth.replace('YYYY',str(year))) for year in range(years[0],years[-1]+1)])
                df.columns = [f"{key}.{c}" for c in df.columns]
                # Cast data to pre-generated "empty" df
                # Maybe not the fastest option? but saves the hassle of having to re-cast types after pd.concat()
                # as constituent dataframes may not have mutually inclusive indices 
                rawData.loc[df.index,df.columns] = df.copy()
            
            rawData.to_csv('testing/rawData.csv',index_label='timestamp')
            
            if preEvaluate:    
                exec(preEvaluate)
                
            firstStageDependencies = {} 
            for traceName,traceFS in iniFirstStage.items():
                if traceName == self.posixName:
                    continue
                for key,value in traceFS['inputFiles'].items():
                    value = pd.to_datetime(value)
                    dataTable.loc[value[0]:value[-1],traceName] = rawData.loc[value[0]:value[-1],key].copy()  

                if traceFS['minMax'] != [-np.inf,np.inf]:
                    dataTable.loc[
                        ((dataTable[traceName]<traceFS['minMax'][0])|(dataTable[traceName]>traceFS['minMax'][-1])),
                        traceName
                        ] = self.intMask if np.issubdtype(traceFS['dtype'],np.integer) else np.nan
                if len(traceFS['dependent']):
                    firstStageDependencies[traceName] = traceFS['dependent']
            if firstStageDependencies != {}:
                dataTable = self.Dependencies(dataTable,firstStageDependencies)
            self.writeTraceFolder(dataTable,siteID,'FirstStage',clearFirst=True)
            print(f'Executed {siteID} FirstStage in:',time()-T1)
            
    def Dependencies(self,dataTable,dependencies):
        if len(dependencies):
            self.logMessage('\nDependency Filtering:')
        for traceName,dependent in dependencies.items():
            # split dependencies by int/float to properly check missing values
            intDep = [k for k,v in dataTable[dependent].dtypes.items() if np.issubdtype(v,np.integer)]
            floatDep = [k for k in dependent if k not in intDep]
            nanIn = dataTable[traceName].isna().sum()   
            if np.issubdtype(dataTable[traceName].dtype,np.integer):
                dataTable.loc[dataTable[floatDep].isna().any(axis=1) + (dataTable[intDep]==self.intMask).any(axis=1),traceName] = self.intMask
            else:
                dataTable.loc[dataTable[floatDep].isna().any(axis=1) + (dataTable[intDep]==self.intMask).any(axis=1),traceName] = np.nan
            nanDep = dataTable[traceName].isna().sum() - nanIn
            self.logMessage(f"{traceName}: {nanDep} filtered by missing values in {dependent}")
        return(dataTable)