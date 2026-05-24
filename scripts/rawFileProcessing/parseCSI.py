# Reads campbell scientific .dat files in TOA5, TOB3, and mixed array (not yet supported) formats

from dataclasses import dataclass,field
from collections import defaultdict
from helperFunctions.parseFrequency import parseFrequency
from helperFunctions.baseClass import mdMap
from scripts.traceAnalysis.traceParameters import rawTrace
from scripts.rawFileProcessing.sharedFields import sharedFields
from datetime import datetime
import pandas as pd
import numpy as np
import struct
import re
import os

@dataclass(kw_only=True)
class csiTable(sharedFields):
    stationName: str = field(default=None,init=False,repr=False)
    loggerModel: str = field(default=None,init=False,repr=False)
    serialNumber: str = field(default=None,init=False,repr=False)
    program: str = field(default=None,init=False,repr=False)
    campbellBaseTime = 631152000.0      
            
    def parseHeader(self,fileObject):
        # Read header and parse common parameters between formats
        def readHeaderLine(line):
            if type(line) == str:
                return(line.strip().replace('"','').split(','))
            else:
                return(line.decode('ascii').strip().replace('"','').split(','))
        self.header = [readHeaderLine(fileObject.readline()) for l in range(self.headerRows)]
        self.stationName=self.header[0][1]
        self.loggerModel=self.header[0][2]
        self.serialNumber=self.header[0][3]
        self.program=self.header[0][5]

    def finishTable(self):
        if hasattr(self,'gpsDriftCorrection') and self.gpsDriftCorrection:
            # Identify gaps in time series
            Offset = (self.dataTable.index.diff().fillna(self.dataIntervalSeconds)-self.dataIntervalSeconds).cumsum()
            self.dataTable.index -= Offset
            if self.verbose:
                self.logMessage(f"Total GPS induced offset in {self.fileName} is {Offset.iloc[-1]}s",verbose=False)
class TOA5(csiTable):

    def readTOA5(self):
        self.headerRows = 4
        with open(self.fileName,'r') as fileObject:
            self.parseHeader(fileObject)
            self.fileTimestamp = datetime.strptime(re.search(r'([0-9]{4}\_[0-9]{2}\_[0-9]{2}\_[0-9]{4})', self.fileName.rsplit('.',1)[0]).group(0),'%Y_%m_%d_%H%M')
            self.tableName = self.header[0][-1]
            defaultTypes = defaultdict(lambda: '<f4',RECORD ='<u4',TIMESTAMP = 'str')
            self.dataTable = pd.read_csv(fileObject,dtype=defaultTypes,names=self.header[1])
        self.dataTable['TIMESTAMP'] = pd.to_datetime(self.dataTable['TIMESTAMP'],format='ISO8601')
        self.dataIntervalSeconds = self.dataTable.TIMESTAMP.diff().median().total_seconds()
        self.dataTable.index = self.dataTable['TIMESTAMP']
        if self.traces == {}:
            typeMap = self.dataTable.dtypes
            self.traces = {variable:rawTrace(originalVariable=variable,units=unit,dtype=typeMap[variable]).to_dict() for variable,unit in zip(self.header[1],self.header[2])}
        self.finishTable()

class TOB3(csiTable):

    def readTOB3(self):
        self.headerRows = 6
        self.headerSize = 12
        self.footerSize = 4
        self.indexColumns = {variable:rawTrace(originalVariable=variable,units=unit,dtype=dtype).to_dict(keepNull=False) for variable,unit,dtype in [
                    ('POSIX_Time','s','<i4'),('NANOSECONDS','ns','<i4'),('RECORD','','<u4')
                    ]}
        self.fileSize = os.path.getsize(self.fileName)
        with open(self.fileName,'rb') as fileObject:
            self.parseHeader(fileObject)
            self.fileTimestamp = pd.to_datetime(self.header[0][-1])
            self.tableName = self.header[1][0]
            self.dataIntervalSeconds = pd.to_timedelta(parseFrequency(self.header[1][1])).total_seconds()
            self.dataFrequencyHertz = (1.0 / self.dataIntervalSeconds)
            self.frameSize = int(self.header[1][2])
            self.tableSize = int(self.header[1][3])
            self.validationStamp = int(self.header[1][4])
            self.compValidationStamp=(0xFFFF^self.validationStamp)
            self.frameResolution = pd.to_timedelta(parseFrequency(self.header[1][5])).total_seconds()
            self.nframes = int((self.fileSize-fileObject.tell())/self.frameSize)
            dtypes = self.translateTypes(self.header[5])
            if self.traces == {}:
                self.traces = {variable:rawTrace(originalVariable=variable,units=unit,dtype=dtype).to_dict() for variable,unit,dtype in zip(self.header[2],self.header[3],dtypes)}
                self.tracesIn = list(self.traces.keys())
            else:
                # Check of mismatches
                # Less than defined is fine, extra undefined will cause problems
                tracesIn = {variable:rawTrace(originalVariable=variable,units=unit,dtype=dtype).to_dict() for variable,unit,dtype in zip(self.header[2],self.header[3],dtypes)}
                if tracesIn.keys()!=self.traces.keys():
                    tIn = tracesIn.keys()
                    tEx = self.traces.keys()
                    if len([t for t in tIn if t not in tEx]):
                        self.logError(f"Unexpected traces in {self.fileName}:\n{[t for t in tIn if t not in tEx]} are not defined in configuration file")
                self.tracesIn = list(tracesIn.keys())
            if self.mode == 'extractData':
                self.readFrames(fileObject.read())

    def translateTypes(self,dtypes):
        csiTypeMap = {
                    'FP2':{'struct':'H','output':'<f4'},
                    'IEEE4B':{'struct':'f','output':'<f4'},
                    'IEEE8B':{'struct':'d','output':'<f8'},
                    'LONG':{'struct':'l','output':'<i8'},
                    'INT4':{'struct':'i','output':'<i4'},
                    'ASCII':{'struct':'s','output':'str'},
                }
        self.byteMap = []
        pyTypes = []
        for value in dtypes:
            if value in csiTypeMap:
                self.byteMap.append(csiTypeMap[value]['struct'])
                pyTypes.append(csiTypeMap[value]['output'])
            elif type(value) is str and value.startswith('ASCII'):
                self.byteMap.append(value.strip('ASCII()') + csiTypeMap['ASCII']['struct'])
                pyTypes.append(csiTypeMap['ASCII']['output'])
        self.byteMap = ''.join(self.byteMap)
        return(pyTypes)


    def readFrames(self,binaryData):
        # Parameters dictating extraction  
        self.recordSize = struct.calcsize('>'+self.byteMap)
        self.recordsPerFrame = int((self.frameSize-self.headerSize-self.footerSize)/self.recordSize)
        self.byteMap_Body = '>'+''.join([self.byteMap for r in range(self.recordsPerFrame)])
        # Extract the binary data
        
        tracesIn = {key:self.traces[key] for key in self.tracesIn}

        # Process frame by frame
        frames = [f for i in range(self.nframes) for f in 
                self.decodeFrame(binaryData[i*self.frameSize:(i+1)*self.frameSize])]
        dataTable = pd.DataFrame(frames,columns=list(self.indexColumns.keys())+list(tracesIn.keys()))
        # Separate indices (parsed from headers) from traces
        self.indexTraces = dataTable[list(self.indexColumns.keys())].astype(
            {key:var['dtype'] for key,var in self.indexColumns.items()}
        )
        if self.indexTraces[['POSIX_Time','NANOSECONDS']].duplicated().sum():
            self.logWarning(f"Duplicated timestamps found in {self.fileName} at\n{self.indexTraces[self.indexTraces[['POSIX_Time','NANOSECONDS']].duplicated(keep=False)]}\n Replicated indices will be offset by 1ns*(counter) to avoid conflicts")
            ix = self.indexTraces[['POSIX_Time','NANOSECONDS']].duplicated()
            rix = self.indexTraces.loc[ix,'RECORD'].astype('int32')
            self.indexTraces.loc[ix,'NANOSECONDS'] += (rix-(rix.min()+1))
            if self.dataIntervalSeconds<1:
                self.logError('develop better approach?')

        self.dataTable = dataTable[list(tracesIn.keys())].astype(
            {key:var['dtype'] for key,var in tracesIn.items()}
        )
        self.dataTable.index=pd.to_datetime((self.indexTraces['POSIX_Time']*1e9).astype('int64')+self.indexTraces['NANOSECONDS'],unit='ns') 
    
    def decodeFrame(self,frame):
        frame = [struct.unpack('iii', frame[:self.headerSize]),
                 struct.unpack(self.byteMap_Body, frame[self.headerSize:-self.footerSize]),
                 struct.unpack('i',frame[-self.footerSize:])[0]]
        # frame[0] = [frame[0][0]+frame[0][1]*self.frameResolution+self.campbellBaseTime,frame[0][2]]
        # Use nanoseconds so timestamp can be stored as int64 instead of float64, avoids floating point precision issues
        # frame[0] = [int((frame[0][0]+self.campbellBaseTime)*1e9)+int((frame[0][1]*self.frameResolution)*1e9),frame[0][2]]
        frame[0] = [int((frame[0][0]+self.campbellBaseTime)),int((frame[0][1]*self.frameResolution)*1e9),frame[0][2]]
        if 'H' in self.byteMap_Body:
            frame[1] = self.decode_fp2(frame[1])
        frame[1] = list(frame[1])
        npr = int(len(frame[1])/self.recordsPerFrame)
        frame[1] = [frame[1][i*npr:(i+1)*npr] for i in range(self.recordsPerFrame)]
        # True/False flag for valid frame
        # Adapted from https://github.com/ansell/camp2ascii/blob/cea750fb721df3d3ccc69fe7780b372d20a8160d/frame_read.c#L109
        footerValidation = (0xFFFF0000 & frame[2]) >> 16
        footerOffset = (0x000007FF & frame[2])
        frame[2] = (footerValidation == self.validationStamp)
        # For handling partial frames
        if frame[2] and footerOffset > 0:
            d = self.frameSize-(footerOffset+self.headerSize+self.footerSize)
            if d:
                offset = int(d/self.recordSize)
            else:
                offset = 0
        else:
            offset = self.recordsPerFrame
        frame = [[int((frame[0][0]+frame[0][1]*1e-9+self.dataIntervalSeconds*i)//1),int((frame[0][1]+self.dataIntervalSeconds*i*1e9) % 1e9),frame[0][2]+i]+frame[1][i] for i in range(self.recordsPerFrame) if i < offset and frame[2]]
        return(frame)
  
    def decode_fp2(self,Body):
        # adapted from: https://github.com/ansell/camp2ascii/tree/cea750fb721df3d3ccc69fe7780b372d20a8160d
        def FP2_map(int):
            sign = (0x8000 & int) >> 15
            exponent =  (0x6000 & int) >> 13 
            mantissa = (0x1FFF & int)       
            if exponent == 0: 
                Fresult=mantissa
            elif exponent == 1:
                Fresult=mantissa*1e-1
            elif exponent == 2:
                Fresult=mantissa*1e-2
            else:
                Fresult=mantissa*1e-3

            if sign != 0:
                Fresult*=-1
            return Fresult
        FP2_ix = [m.start() for m in re.finditer('H', self.byteMap_Body.replace('>','').replace('<',''))]
        Body = list(Body)
        for ix in FP2_ix:
            Body[ix] = FP2_map(Body[ix])
        return(Body)
    
class MixedArray(csiTable):

    def readMixedArray(self):
        if self.traces == {}:
            self.readDEF()
        else:
            self.readArray()
    
    def readDEF(self):
        with open(self.templateFile,'r',encoding='utf-8-sig') as f:
            lines = f.readlines()
        Header,header = '',True
        Wiring,wiring = '',False
        Labels,labels = {},False
        entries = False
        tableID,Tables,tables,ntables = None,{},False,0
        self.mxCols = 0
        for i,l in enumerate(lines):
            if 'final storage' in l:
                Storage = l
            elif 'Output_Table' in l or tables:
                tables = True
                if 'Output_Table' in l:
                    ntables += 1
                    tableID,self.dataIntervalSeconds = [m.strip() for m in l.split('Output_Table')]
                    self.dataIntervalSeconds = pd.to_timedelta(parseFrequency(self.dataIntervalSeconds)).total_seconds()
                    tableID = int(tableID)
                    Tables[tableID] = ''
                else:
                    Tables[tableID]  = Tables[tableID]+l
            elif 'Table Entries' in l:
                entries = True
            elif 'Labels' in l or labels:
                labels = True
                if 'Labels' not in l:
                    l = l.split()
                    if len(l):
                        if not l[0].isdigit():
                            sensor = '_'.join(l)
                        else:
                            Labels[l[1]]=sensor
            elif 'Wiring' in l or wiring:
                if 'Wiring' in l:
                    self.loggerModel = l.split('for ')[-1].rstrip('-\n')
                wiring = True
                Wiring = Wiring+l
            elif header:
                Header = Header+l
        for ID in Tables:
            data = {'originalVariable':[],'units':[],'ignore':[],'dtype':[]}
            ix = 0
            for v in Tables[ID].split():
                if ix == 1:
                    if v == str(ID):
                        data['originalVariable'].append(f'{ID}-ID_{v}')
                        data['dtype'].append('<i2')
                        ignore=True
                    else:
                        data['originalVariable'].append(f'{ID}-{v}')
                        data['dtype'].append('<f4')
                        if 'RTM' in v:
                            ignore=True
                        else:
                            ignore=False
                    # data['originalVariable'].append(v)
                    operation = v.split('_')[-1]
                    if operation not in ['AVG','STD','MAX','MIN','TOT']:
                        operation = ''
                    r = v.rstrip(f'_{operation}').split('_')
                    if r[-1][0].isdigit():
                        r.pop(-1)
                    if len(r)>1:
                        unit = r[-1]
                    else:
                        unit = ''
                    # data['operation'].append(operation)
                    data['units'].append(unit)
                    data['ignore'].append(ignore)
                ix += 1
                if ix ==3: ix = 0
            
            df = pd.DataFrame(data=data)
            if len(df.index)>self.mxCols:
                self.mxCols = len(df.index)
            df['sensorID'] = ''
            for l,sensor in Labels.items():
                df.loc[df['originalVariable'].str.contains(l),'sensorID']=sensor
            df.index = df['originalVariable']
            self.traces = {key:rawTrace(originalVariable=key,units=value['units'],dtype=value['dtype']).to_dict() for key,value in df.to_dict('index').items()}
            # df = {key:csiTrace.from_dict(value|{'ignoreByDefault':self.ignoreTraces,'kwargs':self.traceKwargs.copy(),'stageID':self.stageID}).to_dict() for key,value in df.to_dict('index').items()}
            # self.traces = self.updateDict(self.traces,df)
            
            
    def readArray(self):
        # Count by arrayID prefixes to get max cols
        self.mxCols = pd.DataFrame(data=[k.split('-') for k in self.traces.keys()],columns=['Array','Cols']).groupby('Array').count().max().values[0]
        df = pd.read_csv(self.fileName,header=None,names=[i for i in range(self.mxCols)])
        cols = list(self.traces.keys())
        for i,ID in enumerate(df[0].unique()):
            sub = df.loc[df[0]==ID].copy()
            sub = sub.dropna(how='all',axis=1)
            sub.columns = [c for c in cols if int(c.split('-')[0])==ID]
            HHMM = sub[f'{ID}-Hour_Minute_RTM'].astype(str).str.zfill(4)
            HH = HHMM.str[:2]
            MM = HHMM.str[2:4]
            SS = '00'
            HHMM = HH+':'+MM+':'+SS
            YJ = sub[f'{ID}-Year_RTM'].astype(str)+'-'+sub[f'{ID}-Day_RTM'].astype(str)
            sub.index = pd.DatetimeIndex(pd.to_datetime(YJ,format='%Y-%j')+pd.to_timedelta(HHMM))
            if i == 0:
                self.dataTable = sub.copy()
            else:
                self.dataTable = self.dataTable.join(sub,how='outer')
        self.dataTable = self.dataTable.loc[~self.dataTable.index.duplicated(keep='last')]
        typeMap = {var['originalVariable']:var['dtype'] for var in self.traces.values()}
        self.dataTable = self.dataTable.astype(typeMap)
        # self.dataTable.index = self.dataTable.index.tz_localize(self.timezone)