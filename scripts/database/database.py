from scripts.siteConfiguration.siteConfiguration import siteConfiguration
from helperFunctions.baseClass import mdMap
from dataclasses import dataclass, field
from datetime import datetime
from scripts.project import project
import pandas as pd
import numpy as np
import os

currentYear = datetime.now().year
posixYears = pd.date_range('1970-01-01T00:30',f"{currentYear+2}-01-01T00:00",freq='YS')
if posixYears.unit=='us':
    #Default in pandas >=3.0
    posixYears = ((posixYears.astype(int)//1e6).values).astype('int64')
elif posixYears.unit == 'ns':
    #Default in pandas <3.0
    posixYears = ((posixYears.astype(int)//1e9).values).astype('int64')
else:
    exit(f'add process for {posixYears.unit}')
posixYears = pd.Series({timestamp:i+1970 for i,timestamp in enumerate(posixYears)},name='Year')

@dataclass
class defaultSettings(project):
    dataIntervalSeconds: float = 1800.0 # Defaults to 1800s (30 min) for the database, however any format is acceptable for a given database folder
    timezone: str = 'UTC' # defaults to UTC for simplicity, but can be set to any timezone on a site or data-source specific basis

    posixYears = posixYears
    intMask = -9999 # NO DATA value for integer data
    defaultDataType = 'float32' # Any numeric type acceptable, float32 & int32 preferred for optimizing precisions vs. storage requirements
    posixName = 'posix_time' # Filename of python time-trace (stored in posix format with int64 dtype)
    datenumName = 'clean_tv' # Legacy variable to allow interoperability of generated database with Biomet.net
    
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
        

    def loadSiteConfiguration(self,siteID,template=False):
        # Create an empty template
        # if template:
        #     self.logMessage(f"Creating empty template for {siteID}")
        #     return(siteConfiguration(siteID=siteID,projectPath=self.projectPath,template=True))
        # # read a user-provided file
        # if os.path.isfile(siteID):
        #     return(
        #         siteConfiguration.from_yaml(
        #             siteID,
        #             kwargs={'projectPath':self.projectPath}
        #             )
        #         )
        # # read a project file
        # else:
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

    def loadTraceFolder(self,traceFolder,expectedTraces={}):
        dataTable = pd.DataFrame(
            data = {f.split('.')[0]:self.readTrace(os.path.join(traceFolder,f)) for f in os.listdir(traceFolder)}
        )
        dataTable = pd.concat([dataTable,pd.DataFrame(
            index = dataTable.index,
            data = {column: (np.ones(dataTable.shape[0])*self.intMask).astype(dtype) if np.issubdtype(dtype,np.integer) else (np.ones(dataTable.shape[0])*np.nan).astype(dtype)
                    for column,dtype in expectedTraces.items() if column not in dataTable.columns
                    })],axis=1)
        dataTable.index = pd.to_datetime(dataTable['posix_time'],unit='s').dt.tz_localize(self.timezone)
        return(dataTable)
    
    def writeTraceFolder(self,newData,siteID,stageID):
        start = self.posixYears[self.posixYears.index<=newData[self.posixName].min()].max()
        stop = self.posixYears[self.posixYears.index>newData[self.posixName].max()].min()
        for startTime,year in self.posixYears[(self.posixYears>=start) * (self.posixYears<stop)].to_dict().items():
            stopTime = self.posixYears[self.posixYears==year+1].index[0]
            traceFolder = os.path.join(self.databasePath,str(year),siteID,stageID)
            if not os.path.exists(traceFolder):
                os.makedirs(traceFolder)
            for traceName in newData.columns:
                self.writeTrace(
                    trace=newData.loc[((newData.posix_time>=startTime)&(newData.posix_time<=stopTime)),traceName].values,
                    filePath=os.path.join(traceFolder,traceName)
                )

    def uploadRawData(self,newData,siteID,stageID,interval=None):
        stageID = os.path.join('raw',stageID)
        if interval is None:
            interval = self.dataIntervalSeconds
        start = self.posixYears[self.posixYears.index<=newData[self.posixName].min()].max()
        stop = self.posixYears[self.posixYears.index>newData[self.posixName].max()].min()
        dataTable = []
        for startTime,year in self.posixYears[(self.posixYears>=start) * (self.posixYears<stop)].to_dict().items():
            stopTime = self.posixYears[self.posixYears==year+1].index[0]
            traceFolder = os.path.join(self.databasePath,str(year),siteID,stageID)
            if not os.path.exists(traceFolder):
                os.makedirs(traceFolder)
                timestamp = np.arange(startTime,stopTime,interval).astype('int64')
                self.writeTrace(timestamp,os.path.join(traceFolder,self.posixName))
            dataTable.append(self.loadTraceFolder(traceFolder,expectedTraces=newData.dtypes.to_dict()))
        dataTable = pd.concat(dataTable)
        dataTable.loc[newData.index] = newData.copy()
        self.writeTraceFolder(dataTable,siteID,stageID)