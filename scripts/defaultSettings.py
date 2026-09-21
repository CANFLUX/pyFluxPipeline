from helperFunctions.baseClass import baseDataClass
from dataclasses import dataclass,field
from datetime import datetime

@dataclass(kw_only=True)
class defaultSettings(baseDataClass):
    projectPath: str = field(repr=False) # Root path of project, all paths realative to this
    databaseInterval: float = field(default=1800,init=False,repr=False) # Interval of database
    dataIntervalSeconds: float = 1800.0 # Defaults to 1800s (30 min) for the database, however any format is acceptable for a given database folder
    timezone: str = 'UTC' # defaults to UTC for simplicity, but can be set to any timezone on a site or data-source specific basis
    intMask = -9999 # NO DATA value for integer data
    defaultDataType = 'float32' # Any numeric type acceptable, float32 & int32 preferred for optimizing precisions vs. storage requirements
    posixName = 'posix_time' # Filename of python time-trace (stored in posix format with int64 dtype)
    datenumName = 'clean_tv' # Legacy variable to allow interoperability of generated database with Biomet.net
    currentYear = datetime.now().year