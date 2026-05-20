from helperFunctions.baseClass import baseClassMethods,baseDataClass,mdMap
from helperFunctions.safeFormat import safeFormat,cleanString
from pandas.api.types import is_numeric_dtype
from dataclasses import dataclass,field
import os

defaultSettings = baseClassMethods().loadDict(os.path.join(os.getcwd(),'configurationFiles','defaultSettings.yml'))

@dataclass(kw_only=True)
class common(baseDataClass):
    variableName: str = field(default=None,metadata=mdMap('Name of the variable (must be filename safe, alphanumeric with underscores accepted)'))
    units: str = field(default='', metadata=mdMap(''))
    dtype: str = field(default=defaultSettings['defaultDataType'],metadata=mdMap('data type (float, string, etc.)'))
    
    def __post_init__(self):
        self.variableName = safeFormat(self.variableName)
        self.units = cleanString(self.units,permit={'°','µ'})
        super().__post_init__()

@dataclass(kw_only=True)
class rawTrace(common):
    variableName: str = field(default=None,metadata=mdMap('Name of the variable (must be filename safe, alphanumeric with underscores accepted)'))
    originalVariable: str
    sensorID: str = None
    ignore: bool = False

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
class firstStageTrace(common):
    variableName: str = field(metadata=mdMap('Name of the variable (must be filename safe, alphanumeric with underscores accepted)'))
    inputFiles: dict = None
    inputDates: list = field(default_factory=list,metadata=mdMap('date rang corresponding to input files (s)'),repr=False)
    dependent: list = field(default_factory=list,metadata=mdMap('Other variables upon which this trace will be filtered for nan'))
    # dataTrace: pd.Series = field(default=None,repr=False,metadata=mdMap('Initalize with data to do within-trace cleaning. Accept dataframe for instances of composite traces.'))
    singlePointInterpolation: bool = False
    linearRescale: list = field(default=None,metadata=mdMap('List of one or more len=4 list [m,b,start,stop].  Rescales as dataTrace = m*dataTrace+b over range [start:stop], or full trace if start and stop are None'))
    
    def __post_init__(self):
        if not isinstance(self.inputFiles,dict):
            self.inputFiles = {self.inputFiles:self.inputDates}
        super().__post_init__()
