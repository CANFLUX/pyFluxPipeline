# from scripts.siteConfiguration.siteConfiguration import siteConfiguration
# from helperFunctions.baseClass import mdMap
from dataclasses import dataclass, field
from scripts.project import project
# from scripts.defaultSettings import defaultSettings
import pandas as pd
import numpy as np
import shutil
import os

@dataclass(kw_only=True)
class database(project):
    sitesList: list = field(default_factory=list,repr=False)

    def __post_init__(self):  
        super().__post_init__()
        # breakpoint()
        if self.projectPath is None:
        #     return
            breakpoint()
        self.databasePath = os.path.join(self.projectPath,'Database')
        # self.highFrequencyPath = os.path.join(self.projectPath,'HighFrequencyData')
        if self.sitesList == []:
            self.sitesList = [pth for pth in os.listdir(self.metaPath)]

    def secondsToHertz(self,interval):
        if interval <= 0:
            frequency = np.nan
        else:
            frequency = (1.0 / interval)
        return frequency
    
    def getStagePath(self,siteID,stageID,year='YYYY'):
        return (os.path.join(self.databasePath,str(year),siteID,stageID))
    
    # def typeName(self,dtype):
    #     if dtype == '<f4':
    #         return 'float32'
    #     elif dtype == '<i4':
    #         return 'int32'
    #     elif dtype == '<f8':
    #         return 'float64'
    #     elif dtype == '<i8':
    #         return 'int64'
    #     else:
    #         self.logError('Not coded yet')


        
    def posixYears(self,interval):
        # Get the first timestamp of first record in every possible database year 
        # start of epoch (1970) to two years past current
        timestamp = pd.date_range('1970-01-01T00:00',f"{self.currentYear+2}-01-01T00:00",freq='YS')+pd.to_timedelta(interval,unit='s') 
        if timestamp.unit=='us':
            #Default in pandas >=3.0
            timestamp = ((timestamp.astype(int)//1e6).values).astype('int64')
        elif timestamp.unit == 'ns':
            #Default in pandas <3.0
            timestamp = ((timestamp.astype(int)//1e9).values).astype('int64')
        else:
            exit(f'add process for {timestamp.unit}')
        return(pd.Series({ts:i+1970 for i,ts in enumerate(timestamp)},name='Year'))


    def writeTrace(self,trace,filePath):
        dtype = str(trace.dtype)
        filePath = f"{filePath}.{dtype}"
        trace.tofile(filePath)

    def readTrace(self,filePath):
        return(np.fromfile(filePath,dtype=filePath.split('.')[-1]))
    
    def noDataTable(self,index,typeMap):
        empty = pd.DataFrame(index = index,
            data = {
                column: (np.ones(index.shape[0])*self.intMask).astype(dtype) if np.issubdtype(dtype,np.integer)
                else (np.ones(index.shape[0])*np.nan).astype(dtype)
                for column,dtype in typeMap.items()
            })
        return(empty)

    def loadTraceFolder(self,traceFolder,expectedTraces={}):
        dataTable = pd.DataFrame(
            data = {f.split('.')[0]:self.readTrace(os.path.join(traceFolder,f)) for f in os.listdir(traceFolder)}
        )
        expectedTraces = {key:value for key,value in expectedTraces.items() if key not in dataTable.columns}
        if len(expectedTraces):
            dataTable = pd.concat([dataTable,self.noDataTable(dataTable.index,expectedTraces)],axis=1)
        dataTable.index = pd.to_datetime(dataTable[self.posixName],unit='s').dt.tz_localize(self.timezone)
        return(dataTable)
        
    def writeTraceFolder(self,newData,siteID,stageID,interval=None,clearFirst=False):
        # Output by year, all contents within the dataframe
        if interval is None:
            interval = self.dataIntervalSeconds
        posixYearIndex= self.posixYears(interval)
        start = posixYearIndex[posixYearIndex.index<=newData[self.posixName].min()].max()
        stop = posixYearIndex[posixYearIndex.index>newData[self.posixName].max()].min()
        for startTime,year in posixYearIndex[(posixYearIndex>=start) * (posixYearIndex<stop)].to_dict().items():
            stopTime = posixYearIndex[posixYearIndex==year+1].index[0]
            traceFolder = os.path.join(self.databasePath,str(year),siteID,stageID)
            if not os.path.exists(traceFolder):
                os.makedirs(traceFolder)
            elif clearFirst and len(os.listdir(traceFolder)):
                shutil.rmtree(traceFolder)
                os.makedirs(traceFolder)
            for traceName in newData.columns:
                self.writeTrace(
                    trace=newData.loc[((newData.posix_time>=startTime)&(newData.posix_time<stopTime)),traceName].values,
                    filePath=os.path.join(traceFolder,traceName)
                )

    def uploadRawData(self,newData,siteID,stageID,interval=None):
        # remove duplicated rows
        if newData.index.duplicated().sum()>0:
            newData =  newData.loc[~newData.index.duplicated()].copy()
        if interval is None:
            interval = self.dataIntervalSeconds
        posixYearIndex = self.posixYears(interval)
        start = posixYearIndex[posixYearIndex.index<=newData[self.posixName].min()].max()
        stop = posixYearIndex[posixYearIndex.index>newData[self.posixName].max()].min()
        dataTable = []
        for startTime,year in posixYearIndex[(posixYearIndex>=start) * (posixYearIndex<stop)].to_dict().items():
            stopTime = posixYearIndex[posixYearIndex==year+1].index[0]
            traceFolder = os.path.join(self.databasePath,str(year),siteID,stageID)
            if not os.path.exists(traceFolder):
                os.makedirs(traceFolder)
                timestamp = np.arange(startTime,stopTime,interval).astype('int64')
                self.writeTrace(timestamp,os.path.join(traceFolder,self.posixName))
            dataTable.append(self.loadTraceFolder(traceFolder,expectedTraces=newData.dtypes.to_dict()))
        dataTable = pd.concat(dataTable)
        dataTable.loc[newData.index] = newData.copy()
        self.writeTraceFolder(dataTable,siteID,stageID,interval)
