from scripts.defaultSettings import fileMetadata
from dataclasses import dataclass, field
from scripts.project import project
from zoneinfo import ZoneInfo

@dataclass(kw_only=True)
class sharedMethods(project,fileMetadata):
    extractData: bool = field(default=True,repr=False)

    def __post_init__(self):
        super().__post_init__()

    def formatMetadata(self):
        self.dateStart = self.dateStart.replace(tzinfo=ZoneInfo(self.timezone))
        if self.dateStop is not None:
            self.dateStop = self.dateStop.replace(tzinfo=ZoneInfo(self.timezone))
        if self.sourceID == fileMetadata.sourceID:
            self.sourceID = f"{self.tableName}_{self.fileTimestamp.strftime('%Y%m%d%H%M')}"
        self.fileTimestamp = self.fileTimestamp.tz_localize(self.timezone)
        if self.dataIntervalSeconds <= 0:
            self.dataFrequency = None
        elif self.dataIntervalSeconds < 1:
            self.dataFrequency = 'highFrequency'
        else:
            self.dataFrequency = 'Database'
