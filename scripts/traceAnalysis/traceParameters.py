from helperFunctions.baseClass import baseDataClass,mdMap
from helperFunctions.safeFormat import safeFormat,cleanString
from ruamel.yaml.scalarstring import LiteralScalarString
from pandas.api.types import is_numeric_dtype
from dataclasses import dataclass,field
import numpy as np
import os

defaultSettings = baseDataClass().loadDict(os.path.join(os.getcwd(),'configurationFiles','defaultSettings.yml'))

class sharedMethods(baseDataClass):

    def __post_init__(self):
        self.variableName = safeFormat(self.variableName)
        self.units = cleanString(self.units,replace={'°':'deg','µ':'micro'})
        super().__post_init__()

@dataclass(kw_only=True)
class rawTrace(sharedMethods):
    variableName: str = field(default=None,metadata=mdMap('Name of the variable (must be filename safe, alphanumeric with underscores accepted)'))
    units: str = field(default='', metadata=mdMap(''))
    dtype: str = field(default=defaultSettings['defaultDataType'],metadata=mdMap('data type (float32, int64, etc.)'))
    originalVariable: str
    sensorID: str = None
    ignore: bool = False
    notes: str = None

    def __post_init__(self):
        self.originalVariable = cleanString(self.originalVariable,replace={'*':'star'})
        if self.variableName is None:
            self.variableName = self.originalVariable
        if not self.ignore:
            if not is_numeric_dtype(self.dtype):
                self.ignore = True
            elif self.variableName == '_':
                self.ignore = True
        super().__post_init__()

@dataclass(kw_only=True)
class firstStageTrace(sharedMethods):
    variableName: str = field(default=None,metadata=mdMap('Name of the variable (must be filename safe, alphanumeric with underscores accepted)'))
    units: str = field(default='', metadata=mdMap(''))
    dtype: str = field(default=defaultSettings['defaultDataType'],metadata=mdMap('data type (float32, int64, etc.)'))
    inputFiles: dict = None
    inputDates: list = field(default_factory=list,metadata=mdMap('date rang corresponding to input files (s)'),repr=False)
    
    minMax: list = field(default_factory=lambda:[-np.inf,np.inf], metadata=mdMap('optional to set min/max clipping'))
    clamped_minMax: list = field(default_factory=lambda:[-np.inf,np.inf], metadata=mdMap('optional to set min/max clipping'))
    # Evaluate: Iterable = field(default=None,metadata=mdMap('Code block, evaluated using an exec statement, to manipulate the trace variable'))
    dependent: list = field(default_factory=list,metadata=mdMap('Other variables upon which this trace will be filtered for nan'))
    # linearInterpLimit: int = 1
    # linearRescale: list = field(default=None,metadata=mdMap('List of one or more len=4 list [m,b,start,stop].  Rescales as dataTrace = m*dataTrace+b over range [start:stop], or full trace if start and stop are None'))
    notes: str = None

    def __post_init__(self):
        # if isinstance(self.inputFiles,list) and isinstance(self.inputDates,list) and isinstance(self.inputDates[0],list):
        #     self.inputFiles = {f:d for f,d in zip(self.inputFiles,self.inputDates)}
        if not isinstance(self.inputFiles,dict):
            self.inputFiles = {self.inputFiles:self.inputDates}
        # if not np.issubdtype(self.dtype,np.floating):
        #     self.linearInterpLimit = 0
        super().__post_init__()

@dataclass(kw_only=True)
class secondStageTrace(sharedMethods):
    variableName: str = field(default=None,metadata=mdMap('Name of the variable (must be filename safe, alphanumeric with underscores accepted)'))
    units: str = field(default='', metadata=mdMap(''))
    dtype: str = field(default=defaultSettings['defaultDataType'],metadata=mdMap('data type (float32, int64, etc.)'))
    linearInterpLimit: int = 0
    minMax: list = field(default_factory=lambda:[-np.inf,np.inf], metadata=mdMap('optional to set min/max clipping'))
    Evaluate: str = ''

    def __post_init__(self):
        self.Evaluate = LiteralScalarString(self.Evaluate)
        super().__post_init__()
