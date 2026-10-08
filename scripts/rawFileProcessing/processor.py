from scripts.rawFileProcessing.parseCSI import TOB3, TOA5, MixedArray
from scripts.defaultSettings import fileMetadata
from dataclasses import dataclass, field
import fnmatch
import json
import sys

processor = {
    'TOB3':TOB3,
    'TOA5':TOA5
}

def check(fileFormat):
    if fileFormat not in processor:
        sys.exit(f'File format not supported: {fileFormat}')

@dataclass(kw_only=True)
class getRawFileMetadata(fileMetadata):
    fileName: str
    projectPath: str
    siteID: str
    fileFormat: str
    ignoreTraces: list = field(default_factory=list)
    renameTraces: dict = field(default_factory=dict)
    def read(self):
        check(self.fileFormat)
        obj = processor[self.fileFormat](
            projectPath=self.projectPath,
            siteID=self.siteID,
            ).read(self.fileName)
        if len(self.ignoreTraces) or len(self.renameTraces):
            for trace in self.traces.values():
                if any([fnmatch.fnmatch(trace['originalVariable'],ignore) for ignore in self.ignoreTraces]):
                    trace['ignore'] = True
                if trace['originalVariable'] in self.renameTraces:
                    trace['variableName'] = self.renameTraces[trace['variableName']]
        obj.traces = json.dumps(obj.traces)
        if obj.dataFrequency == '':
            exit(f"No data frequency: {self.fileName}")
        # Limit output to just parameters defined in the yaml template
        return ({key:value for key,value in obj.__dict__.items() if key in fileMetadata.__annotations__.keys()})

    # def formatMetadata(self,obj):
    #     if obj.dataIntervalSeconds > 60:
    #         obj.dataFormat = 'Database'
    #     elif obj.dataIntervalSeconds > 0 and obj.dataIntervalSeconds<60:
    #         obj.dataFormat = 'ecf32'

# def getRawFileMetadata(
#     fileName: str,
#     projectPath: str,
#     fileFormat: str,
#     siteID: str,
#     ignoreTraces: list = [],
#     renameTraces: dict = {}
#     ):
#     check(fileFormat)
#     out = processor[fileFormat](
#         projectPath=projectPath,
#         siteID=siteID,
#         fileName=fileName,
#         mode='identifyTraces',
#         ignoreTraces=ignoreTraces,
#         renameTraces=renameTraces
#         )
    
#     out.formatMetadata()
#     out.traces = json.dumps(out.traces)
#     return(out.to_dict())
        
def readRawFileData(
    projectPath: str,
    fileName: str,
    fileFormat: str,
    fileMetadata: dict = {},
    ):
    if fileName is None: return(None)
    check(fileFormat)
    out = processor[fileFormat].from_dict(fileMetadata|{'projectPath':projectPath,'fileName':fileName,'mode':'extractData'})
    out.formatTable()
    return(out.dataTable)

    # if self.mode == 'extractData':
    #     self.formatTable()

    
        # T1 = time.time()
        # self.logMessage(f"Searching: {len(fileList)} files")
        # get = partial(getRawFileMetadata,
        #         fileFormat=self.fileFormat,
        #         siteID=self.siteID,
        #         ignoreTraces=self.ignoreTraces)
        # if not self.useParallel:
        #     files = pd.DataFrame({f:get(fileName=f) for f in fileList}).T
        # else:
        #     with ProcessPoolExecutor(max_workers=1) as executor:
        #         files = pd.DataFrame({f:out for f,out in zip(fileList,executor.map(get,fileList))}).T
        # self.logMessage(f'Metadata extracted in : {time.time()-T1} s')