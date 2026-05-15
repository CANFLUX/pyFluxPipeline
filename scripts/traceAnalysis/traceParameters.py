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

@dataclass(kw_only=True)
class rawTrace(common):
    variableName: str = field(default=None,metadata=mdMap('Name of the variable (must be filename safe, alphanumeric with underscores accepted)'))
    originalVariable: str
    sensorID: str = None
    ignore: bool = False

    def __post_init__(self):
        if self.variableName is None:
            self.variableName = safeFormat(self.originalVariable)
        if not self.ignore:
            if not is_numeric_dtype(self.dtype):
                self.ignore = True
            elif self.variableName == '_':
                self.ignore = True
        self.units = cleanString(self.units,passKey={'°','µ'})
        super().__post_init__()