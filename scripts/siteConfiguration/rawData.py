from dataclasses import dataclass, field
from datetime import datetime
from helperFunctions import baseClass, randomID
import numpy as np

mdMap = baseClass.mdMap

@dataclass(kw_only=True)
class rawFileParameters(baseClass.baseDataClass):
    fileFormat: str
    measurementType: str
    dateStart: datetime = None
    dateStop: datetime = None
    dataLoggerID: str = None
    rawFileID: str = None
    traces: dict = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()