from scripts.database.database import database
from dataclasses import dataclass,field
import pandas as pd
import numpy as np
import os

@dataclass(kw_only=True)
class firstStage(database):
    sites: list
    years: list = None

    def __post_init__(self):
        super().__post_init__()
        for siteID in self.sites:
            siteConfig = self.loadSiteConfiguration(siteID)
            dataIn = siteConfig.ini['rawData']
            # load firstStage instructions and replace arbitrary keys with desired variable names
            iniFirstStage = {value['variableName']:value for value in siteConfig.ini['Processing']['FirstStage'].values()}
            # Load raw traces
            dby = os.path.join(self.projectPath,'Database','YYYY',siteID,'raw')
            for key,value in dataIn.items():
                dbyPth = os.path.join(dby,key)
                years = pd.to_datetime(value).year
                df = pd.concat([self.loadTraceFolder(dbyPth.replace('YYYY',str(year))) for year in range(years[0],years[-1]+1)])
                df.columns = [f"{key}.{c}" for c in df.columns]
                interval = df.index.diff().median().total_seconds()
                # force to common time interval
                if interval!=self.dataIntervalSeconds:
                    typeMap=df.dtypes
                    if interval > self.dataIntervalSeconds:
                        df = df.resample(f"{self.dataIntervalSeconds}s").asfreq()
                        self.logWarning('Offset time intervals, resampling with asfreq()')
                    elif interval < self.dataIntervalSeconds:
                        df = df.resample(f"{self.dataIntervalSeconds}s").mean()
                        self.logWarning('Offset time intervals, resampling with mean()')
                    for kx,value in df.dtypes.to_dict().items():
                        dtype = typeMap[kx]
                        if value!=dtype:
                            if np.issubdtype(dtype,np.integer):
                                df[kx] = df[kx].fillna(self.intMask).astype(dtype)
                            else:
                                self.logError('Unexpected type issues?')
                dataIn[key] = df
            breakpoint()
            rawData = pd.concat([value for value in dataIn.values()])

            if self.years is None:
                self.years = [i for i in range(siteConfig.startDate.year,self.currentYear+1)]

            posixYearIndex = self.posixYears(self.dataIntervalSeconds)
            startTime = posixYearIndex[posixYearIndex==self.years[0]].index.values[0]
            stopTime = posixYearIndex[posixYearIndex==self.years[-1]+1].index.values[0]
            timestamp = np.arange(startTime,stopTime,self.dataIntervalSeconds).astype('int64')
            # create empty dataframe of desired types
            dataTable = self.noDataTable(timestamp,{key:value['dtype'] for key,value in iniFirstStage.items()})
            # for key,value in iniFirstStage.items():

            
            breakpoint()