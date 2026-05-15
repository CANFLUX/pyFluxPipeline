from scripts.rawFileProcessing.sharedFields import sharedFields
from scripts.traceAnalysis.traceParameters import rawTrace
from helperFunctions.safeFormat import cleanString
from helperFunctions.baseClass import mdMap
# from dataclasses import dataclass, field
from typing import ClassVar
import pandas as pd
import numpy as np
import warnings
import re

# @dataclass(kw_only=True)
class csvFile(sharedFields):
    labelColumnBy = 'name'
    delimiter = ','

    def open_csv_file(self):
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
        

# @dataclass(kw_only=True)
class EddyProOutput(csvFile):

    def readEddyProOutput(self):
        self.skipRows = 1
        self.headerRows = 2
        self.labelColumnBy = 'name'
        self.na_values = -9999
        self.open_csv_file()
        if self.timestampFormat is None:
            self.timestampFormat = {'date':'%Y-%m-%d','time':'%H:%M'}


        if self.traces == {}:
            self.traces = {key:rawTrace.from_dict({'originalVariable':key,'units':value,'dtype':self.typeMap[key]}).to_dict() for i,(key,value) in enumerate(zip(self.header[0],self.header[1]))}

        TIMESTAMP = pd.to_datetime(
            self.rawDataTable[self.timestampFormat.keys()].agg(' '.join,axis=1),
            format=' '.join([v for v in self.timestampFormat.values()])
            )

        self.rawDataTable.index = TIMESTAMP 

# @dataclass(kw_only=True)
class HOBOcsv(csvFile):

    def readHOBOcsv(self):
        self.skipRows = 1
        self.headerRows = 1
        self.labelColumnBy = 'index'
        self.open_csv_file()
        if self.traces == {}:
            self.traces = {i:rawTrace.from_dict({'originalVariable':key,'dtype':self.typeMap[i]}).to_dict() for i,key in enumerate(self.header[0])}

        with warnings.catch_warnings():
            warnings.simplefilter("error", category=UserWarning)
            if self.timestampFormat is None:
                try:
                    TIMESTAMP = pd.to_datetime(self.rawDataTable[1])
                except:
                    self.logWarning('Bulk parsing of timestamp failed on first attempt, indicating suspicious format.  This is common in hobo files. Parsed assuming yearfirst=True. Double check results.  For better performance, explicitly provide timestamp format.')
                    TIMESTAMP = pd.to_datetime(self.rawDataTable[1],format='mixed',yearfirst=True)
            else:
                
                TIMESTAMP = pd.to_datetime(
                    self.rawDataTable[self.timestampFormat.keys()].agg(' '.join,axis=1),
                    format=' '.join([v for v in self.timestampFormat.values()])
                    )
                    
        self.rawDataTable.index = TIMESTAMP 
        ix = np.where(self.rawDataTable.values=='Logged')[0]
        ix = self.rawDataTable.index[ix]
        self.rawDataTable = self.rawDataTable.drop(ix)
