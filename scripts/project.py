from datetime import datetime
from dataclasses import field, dataclass
from helperFunctions.baseClass import baseDataClass, mdMap

@dataclass(kw_only=True)
class project(baseDataClass):
    projectPath: str = field(repr=False,metadata=mdMap('Root path of the current project'))


@dataclass
class defaultSettings(project):
    dataIntervalSeconds: float = 1800.0 # Defaults to 1800s (30 min) for the database, however any format is acceptable for a given database folder
    timezone: str = 'UTC' # defaults to UTC for simplicity, but can be set to any timezone on a site or data-source specific basis
    # posixYears = posixYears
    intMask = -9999 # NO DATA value for integer data
    defaultDataType = 'float32' # Any numeric type acceptable, float32 & int32 preferred for optimizing precisions vs. storage requirements
    posixName = 'posix_time' # Filename of python time-trace (stored in posix format with int64 dtype)
    datenumName = 'clean_tv' # Legacy variable to allow interoperability of generated database with Biomet.net
    
    currentYear = datetime.now().year
