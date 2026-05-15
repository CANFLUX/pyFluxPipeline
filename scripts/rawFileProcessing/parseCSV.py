from scripts.traceAnalysis.traceParameters import rawTrace
from helperFunctions.baseClass import baseDataClass,mdMap
from helperFunctions.safeFormat import cleanString
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import warnings
import re

@dataclass(kw_only=True)
class csvFile(baseDataClass):
    fileName: str
    labelColumnBy: str = field(default='name',metadata=mdMap('label columns by by name or index',options=['name','index']))
    delimiter: str = ','
    skipRows: int = 0
    headerRows: int = 1
    encoding: str = None
    na_values: str = None
    mode: str = field(repr=False,metadata=mdMap('extract data or inspect header',options=['extractData','inspectHeader']))
    traces: dict = field(default_factory=dict)
    # timestampFormat: dict = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        if self.encoding:
            rawFile = open(self.fileName,'r',encoding=self.encoding)
        else:
            rawFile = open(self.fileName,'r')
            
        self.preamble = []
        for i in range(self.skipRows):
            self.preamble.append(''.join(rawFile.readline().rstrip('\n').split(self.delimiter)))
        self.preamble = '\n'.join(self.preamble)
        # # some files (eg. hoboCSV) have less than tidy formatting in their headers
        def delimSub(text,subText):
            text = re.sub(r'"([^"]*)"', 
                    lambda match: match.group(0).replace(',', subText), 
                    text)
            return(text)
        def format(text):
            text = text.strip('"').replace(subText,self.delimiter)
            if text=='':
                text='Unnamed'
            return(text)
        # parse the header to a list (only if not user provided, otherwise just skip)
        self.header = []
        for i in range(self.headerRows):
            HL = cleanString(rawFile.readline(),repKey={'\n':''},passKey={'°','µ'})
            subText ='THISISADELIMTERITDOESNTBELONGHERE'
            HL = delimSub(HL,subText)
            HL = [format(h) for h in HL.split(self.delimiter)]
            self.header.append(HL)

        self.rawDataTable = pd.read_csv(rawFile,delimiter=self.delimiter,header=None,na_values=self.na_values)
        rawFile.close()
        self.rawDataTable = self.rawDataTable.dropna(how='all')
        if self.labelColumnBy == 'name':
            names = self.header[0]
            self.rawDataTable.columns = names
        self.typeMap = self.rawDataTable.dtypes
        self.typeMap[self.typeMap=='float64'] = 'float32'
        self.rawDataTable = self.rawDataTable.astype(self.typeMap)
        

@dataclass(kw_only=True)
class EddyProOutput(csvFile):
    skipRows: int = 1
    headerRows: int = 2
    labelColumnBy: str = 'name'
    timestampFormat: dict = field(default_factory=lambda:{'date':'%Y-%m-%d','time':'%H:%M'})
    na_values: int = field(default=-9999,repr=False)   
    def __post_init__(self):
        super().__post_init__()


        if self.traces == {}:
            self.traces = {key:rawTrace.from_dict({'originalVariable':key,'units':value,'dtype':self.typeMap[key]}).to_dict() for i,(key,value) in enumerate(zip(self.header[0],self.header[1]))}

        TIMESTAMP = pd.to_datetime(
            self.rawDataTable[self.timestampFormat.keys()].agg(' '.join,axis=1),
            format=' '.join([v for v in self.timestampFormat.values()])
            )

        self.rawDataTable.index = TIMESTAMP 

@dataclass(kw_only=True)
class HOBOcsv(csvFile):
    skipRows: int = 1
    labelColumnBy: str = 'index'
    timeStampFormat: dict = field(default_factory=lambda:{1:'autoParse'})
    autoParseDate: bool = True

    def __post_init__(self):
        super().__post_init__()
        if self.traces == {}:
            self.traces = {i:rawTrace.from_dict({'originalVariable':key,'dtype':self.typeMap[i]}).to_dict() for i,key in enumerate(self.header[0])}

        with warnings.catch_warnings():
            warnings.simplefilter("error", category=UserWarning)
            if list(self.timeStampFormat.values())[0] == 'autoParse':
                try:
                    TIMESTAMP = pd.to_datetime(self.rawDataTable[list(self.timeStampFormat.keys())[0]])
                except:
                    self.logWarning('Bulk parsing of timestamp failed on first attempt, indicating suspicious format.  This is common in hobo files. Parsed assuming yearfirst=True. Double check results.  For better performance, explicitly provide timestamp format.')
                    TIMESTAMP = pd.to_datetime(self.rawDataTable[list(self.timeStampFormat.keys())[0]],format='mixed',yearfirst=True)
            else:
                
                TIMESTAMP = pd.to_datetime(
                    self.rawDataTable[self.timestampFormat.keys()].agg(' '.join,axis=1),
                    format=' '.join([v for v in self.timestampFormat.values()])
                    )
                    
        self.rawDataTable.index = TIMESTAMP 
        ix = np.where(self.rawDataTable.values=='Logged')[0]
        ix = self.rawDataTable.index[ix]
        self.rawDataTable = self.rawDataTable.drop(ix)


# @dataclass(kw_only=True)
# class HOBOcsv(csvFile):
#     skiprows: int = 1
#     fileFormat: str = 'HOBOcsv'
#     stationName: str = None
#     serialNumber: str = None
#     ignoreTraces: list = field(default_factory=['#','Host Connected', 'Stopped', 'End Of File','Readout','Unnamed','_'])

#     def __post_init__(self,extractData=None):
#         parseDate = True
#         # Append ignore traces if user-provided defaults (or MRO) don't include them
#         for val in HOBOcsv.__dataclass_fields__['ignoreTraces'].default_factory:
#             rem = [i for i,itm in enumerate(self.ignoreTraces) if itm.startswith(val)]
#             for r in rem:
#                 self.ignoreTraces.pop(r)
#             self.ignoreTraces.append(val)
#         if self.timestampFormat != {} and 'timestampFormat' not in self.traceKwargs:
#             parseDate = False
#         elif 'timestampFormat' in self.traceKwargs:
#             self.timestampFormat = self.traceKwargs.pop('timestampFormat')
#             self.logError('Assign timestampName?')
#         else:
#             for key,value in self.traceKwargs.items():
#                 if 'measurementType' in value and value['measurementType'] == 'TIMESTAMP':
#                     if 'originalVariable' in value:
#                         self.timestampName = value['originalVariable']
#                     else:
#                         self.timestampName = key
#             if self.timestampName is None:
#                 self.logError('Must specify timestampName name if parseDate = True, or provide timestampFormat explicitly')
#         super().__post_init__()
#         self.rawDataTable.columns=self.headerText[0]
#         self.getDateTime(parseDate=parseDate)
#         self.parseHoboPreamble() 
#         self.ignoreTraces = list(self.rawDataTable.columns[self.rawDataTable.columns.str.contains('|'.join(self.ignoreTraces))].values)
#         dropRows = self.rawDataTable.iloc[np.where(self.rawDataTable=='Logged')[0]].index  
#         self.rawDataTable = self.rawDataTable.drop(index=dropRows).drop(columns=[c for c in self.ignoreTraces if c in self.rawDataTable.columns])
#         # dt = self.rawDataTable.dtypes
        
#         dt = {n:str for n,dt in self.rawDataTable.dtypes.items() if dt == 'string' or n == self.timestampName}
#         dt = {n:'<f4' if n not in dt.keys() else dt[n] for n in self.rawDataTable.columns}
#         self.rawTraceParameters = {
#             columnName:rawTrace(
#                 originalVariable=columnName,
#                 dtype=dt[columnName],
#                 ignoreByDefault=self.ignoreTraces,
#                 kwargs=self.traceKwargs.copy(),
#                 stageID=self.stageID
#             ).to_dict(keepNull=True) for columnName in self.rawDataTable.columns
#         }
#         # Ensure the fileNames are safe etc.
#         self.formatTable()
    
#     def parseHoboPreamble(self):
#         logger = getattr(dataLoggers,'HOBO')
#         self.preamble = self.preamble.split('Plot Title: ')[-1]
#         self.serialNumber,self.stationName = self.preamble.split('-')
#         self.dataLogger = logger(
#             stationName=self.stationName,
#             serialNumber=self.serialNumber,
#             ).to_dict(keepNull=False)