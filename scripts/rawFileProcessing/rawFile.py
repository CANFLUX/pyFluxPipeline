from scripts.rawFileProcessing.parseCSV import EddyProOutput, HOBOcsv
from scripts.rawFileProcessing.parseCSI import TOB3, TOA5
from helperFunctions.baseClass import mdMap
from dataclasses import dataclass, field
import numpy as np
import os

@dataclass(kw_only=True)
class rawFile(TOB3,TOA5,EddyProOutput,HOBOcsv):
    fileName: str = field(repr=False)
    templateFile: str = None
    siteID: str
    fileID: str
    fileFormat: str = field(metadata=mdMap('used to determine which file parser', options=['EddyProOutput','HOBOcsv','TOB3','TOA5']))
    traces: dict = field(default_factory=dict)
    configFileName: str = field(default=None,repr=False)

    def __post_init__(self):
        configFileName = os.path.join(self.projectPath,'Sites',self.siteID,self.fileFormat,f'{self.fileID}.yml')
        if self.mode == 'extractData' and self.configFile is None:
            if not os.path.isfile(configFileName):
                self.logError(f"does not exist: {configFileName}")
            params = self.loadDict(configFileName)
            for key in self.__annotations__.keys():
                if key in params:
                    setattr(self,key,params[key])
        super().__post_init__()

        if self.fileFormat == 'EddyProOutput':
            self.readEddyProOutput()
        elif self.fileFormat == 'HOBOcsv':
            self.readHOBOcsv()
        elif self.fileFormat == 'TOB3':
            self.readTOB3()
        elif self.fileFormat == 'TOA5':
            self.readTOA5()
        if self.mode == 'identifyTraces':
            self.templateFile = self.fileName
            self.saveConfigFile(configFileName)
    
        breakpoint()
        # method = eval(self.fileFormat)
        # if self.mode == 'identifyTraces':
        #     processed = method(fileName=self.fileName,traces=self.traces,mode=self.mode)
        #     self.traces = processed.traces
        #     if self.templateFile is None:
        #         self.templateFile = self.fileName
        #     self.saveDict(self.to_dict(),fileName=self.configFileName)
        # else:
        #     processed = method.from_yaml(self.configFileName,kwargs={'fileName':self.fileName,'mode':'extractData'})
        #     self.rawDataTable = processed.rawDataTable
        #     self.rawDataTable = self.rawDataTable.drop(columns=[key for key,value in self.traces.items() if value['ignore']])
        #     self.rawDataTable = self.rawDataTable.dropna(how='all')
        #     self.formatTable()


    def formatTable(self):
        # breakpoint()
        pass
        # names = {val['originalVariable']:val['variableName'] for val in self.traces.values()}
        # self.rawDataTable=self.rawDataTable.rename(columns=names)
        # typeMap = {val['variableName']:val['dtype'] for val in self.traces.values() if val['variableName'] in self.rawDataTable.columns}
                
        # for c,d in typeMap.items():
        #     if np.issubdtype(np.dtype(d),np.integer):
        #         self.rawDataTable[c] = self.rawDataTable[c].fillna(-9999)

        # self.rawDataTable.index.name='datetime'
        # self.rawDataTable.index=self.rawDataTable.index.tz_localize(self.timezone)

# python -m scripts.rawFileProcessing.rawFile --fileName testing\data\eddypro_t_full_output_2025-05-02T224906_exp.csv --siteID SCL --projectPath testing/testProject --fileFormat EddyProOutput --fileID EP_recalc_2024 
# python -m scripts.rawFileProcessing.rawFile --fileName testing\data\Met_Data122.dat --siteID SCL --projectPath testing/testProject --fileFormat TOB3 --fileID EC_Met_2024 

# python -m scripts.rawFileProcessing.rawFile --fileName testing\data\20750528-SHSC.SSM.SGT.240720_240913readout.csv --siteID SCL --projectPath testing/testProject --fileFormat HOBOcsv --fileID TS_SSM
if __name__ == '__main__':
    current = rawFile.from_cmd(safeMode=False)

    breakpoint()