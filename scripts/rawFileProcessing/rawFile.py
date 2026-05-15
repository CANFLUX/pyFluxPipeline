from scripts.rawFileProcessing.parseCSV import EddyProOutput, HOBOcsv
from scripts.rawFileProcessing.parseCSI import TOB3, TOA5
from scripts.projectParameters import project
from helperFunctions.baseClass import mdMap
from dataclasses import dataclass, field
import numpy as np
import os

@dataclass(kw_only=True)
class rawFile(project):
    fileName: str = field(repr=False)
    templateFile: str = None
    siteID: str
    fileID: str
    mode: str = field(repr=False,metadata=mdMap('extract data or inspect header',options=['extractData','inspectHeader']))
    fileFormat: str = field(metadata=mdMap('used to determine which file parser', options=['EddyProOutput','HOBOcsv','TOB3','TOA5']))
    traces: dict = field(default_factory=dict)
    traceConfiguration: str = field(default=None,repr=False)

    def __post_init__(self):
        if self.traceConfiguration is None:
            self.traceConfiguration = os.path.join(self.projectPath,'Sites',self.siteID,self.fileFormat,f'{self.fileID}.yml')
        if self.mode == 'extractData':
            params = self.loadDict(self.traceConfiguration)
            for key in self.__annotations__.keys():
                if key in params:
                    setattr(self,key,params[key])
        super().__post_init__()

        method = eval(self.fileFormat)
        if self.mode == 'inspectHeader':
            processed = method(fileName=self.fileName,traces=self.traces,mode=self.mode)
            self.traces = processed.traces
            if self.templateFile is None:
                self.templateFile = self.fileName
            self.saveDict(self.to_dict(),fileName=self.traceConfiguration)
        else:
            processed = method.from_yaml(self.traceConfiguration,kwargs={'fileName':self.fileName,'mode':'extractData'})
            self.rawDataTable = processed.rawDataTable
            self.rawDataTable = self.rawDataTable.drop(columns=[key for key,value in self.traces.items() if value['ignore']])
            self.rawDataTable = self.rawDataTable.dropna(how='all')
            self.formatTable()


    def formatTable(self):
        breakpoint()
        # pass
        # names = {val['originalVariable']:val['variableName'] for val in self.traces.values()}
        # self.rawDataTable=self.rawDataTable.rename(columns=names)
        # typeMap = {val['variableName']:val['dtype'] for val in self.traces.values() if val['variableName'] in self.rawDataTable.columns}
                
        # for c,d in typeMap.items():
        #     if np.issubdtype(np.dtype(d),np.integer):
        #         self.rawDataTable[c] = self.rawDataTable[c].fillna(-9999)

        # self.rawDataTable.index.name='datetime'
        # self.rawDataTable.index=self.rawDataTable.index.tz_localize(self.timezone)