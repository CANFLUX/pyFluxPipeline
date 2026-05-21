from scripts.siteConfiguration.siteConfiguration import siteConfiguration
from helperFunctions.baseClass import mdMap
from dataclasses import dataclass, field
from datetime import datetime
from scripts.project import project
import pandas as pd
import numpy as np
import os



@dataclass
class defaultSettings(project):
    dataIntervalSeconds: float = 1800.0 # Defaults to 1800s (30 min) for the database, however any format is acceptable for a given database folder
    timezone: str = 'UTC' # defaults to UTC for simplicity, but can be set to any timezone on a site or data-source specific basis
    # posixYears = posixYears
    intMask = -9999 # NO DATA value for integer data
    defaultDataType = 'float32' # Any numeric type acceptable, float32 & int32 preferred for optimizing precisions vs. storage requirements
    posixName = 'posix_time' # Filename of python time-trace (stored in posix format with int64 dtype)
    datenumName = 'clean_tv' # Legacy variable to allow interoperability of generated database with Biomet.net
    
    currentYear = datetime.now().year

@dataclass(kw_only=True)
class database(defaultSettings):

    projectPath: str = field(repr=False,metadata=mdMap('Root path of the current project'))
    sites: list = field(default_factory=list)
    # siteInventory: dict = field(init=False,default_factory=dict,repr=False)

    def __post_init__(self):  
        super().__post_init__()
        self.databasePath = os.path.join(self.projectPath,'Database')
        if self.sites == []:
            self.sites = [pth for pth in os.listdir(os.path.join(self.projectPath,'Sites'))]
        
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


    def loadSiteConfiguration(self,siteID):
        return(
            siteConfiguration.from_yaml(
                os.path.join(self.projectPath,'Sites',siteID,f"{siteID}_siteMetadata.yml"),
                kwargs={'projectPath':self.projectPath}
                )
            )

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
        try:
            dataTable = pd.DataFrame(
                data = {f.split('.')[0]:self.readTrace(os.path.join(traceFolder,f)) for f in os.listdir(traceFolder)}
            )
            expectedTraces = {key:value for key,value in expectedTraces.items() if key not in dataTable.columns}
            if len(expectedTraces):
                dataTable = pd.concat([dataTable,self.noDataTable(dataTable.index,expectedTraces)],axis=1)
            dataTable.index = pd.to_datetime(dataTable['posix_time'],unit='s').dt.tz_localize(self.timezone)
            return(dataTable)
        except:
            breakpoint()
        
    def writeTraceFolder(self,newData,siteID,stageID,interval):
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
            for traceName in newData.columns:
                self.writeTrace(
                    trace=newData.loc[((newData.posix_time>=startTime)&(newData.posix_time<stopTime)),traceName].values,
                    filePath=os.path.join(traceFolder,traceName)
                )

    def uploadRawData(self,newData,siteID,stageID,interval=None):
        # remove duplicated rows
        if newData.index.duplicated().sum()>0:
            newData =  newData.loc[~newData.index.duplicated()].copy()
        stageID = os.path.join('raw',stageID)
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
