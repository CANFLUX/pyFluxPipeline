from scripts.traceAnalysis.traceParameters import secondStageTrace
from scripts.traceAnalysis.customMethods import customMethods
from scripts.database.database import database
from dataclasses import dataclass,field
from time import time
import pandas as pd
import numpy as np
import os
customMethods = customMethods()

@dataclass(kw_only=True)
class secondStage(database):
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

            
            typeMap = {value['variableName']:value['dtype'] if 'dtype' in value else self.defaultDataType for value in siteConfig.ini['Processing']['FirstStage'].values()}
            # create empty dataframe of desired types for firstStage data
            firstStageData = self.noDataTable(timestamp,typeMap)

            # Load firstStage data
            dby = os.path.join(self.projectPath,'Database','YYYY',siteID,'FirstStage')
            temp = pd.concat([self.loadTraceFolder(dby.replace('YYYY',str(year))) for year in range(self.years[0],self.years[-1]+1)])
            firstStageData.loc[temp.index,temp.columns] = temp.copy()

            # load secondStage instructions
            # ensure inputs conform to convention and replace arbitrary keys with desired variable names
            iniSecondStage = {}
            for value in siteConfig.ini['Processing']['SecondStage'].values():
                value = secondStageTrace.from_dict(value).to_dict()
                iniSecondStage[value['variableName']] = value
            # value['variableName']:value for value in siteConfig.ini['Processing']['SecondStage'].values()}
            # and for of desired types for raw inputs outputs
            dataTable = self.noDataTable(timestamp,{key:value['dtype'] for key,value in iniSecondStage.items()})
            dataTable[self.posixName] = posix_time
            
           
            for traceName,traceSS in iniSecondStage.items():
                if traceName in firstStageData.columns:
                    dataTable.loc[firstStageData.index,traceName] = firstStageData[traceName].copy()                       
                if traceSS['minMax'] != [-np.inf,np.inf]:
                    dataTable.loc[
                        ((dataTable[traceName]<traceSS['minMax'][0])|(dataTable[traceName]>traceSS['minMax'][-1])),
                        traceName
                        ] = self.intMask if np.issubdtype(traceSS['dtype'],np.integer) else np.nan
                if len(traceSS['Evaluate'])>0:
                    exec(traceSS['Evaluate'])
                if traceSS['linearInterpLimit']>0:
                    dataTable[traceName] = dataTable[traceName].interpolate(limit=traceSS['linearInterpLimit'],limit_area='inside')
            self.writeTraceFolder(dataTable,siteID,'SecondStage',clearFirst=True)
            print(f'Executed {siteID} SecondStage in:',time()-T1)
