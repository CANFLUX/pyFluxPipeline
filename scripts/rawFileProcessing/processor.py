from scripts.rawFileProcessing.parseCSI import TOB3, TOA5, MixedArray
# from dataclasses import dataclass, field
import json
import sys

processor = {
    'TOB3':TOB3,
    'TOA5':TOA5
}

def check(fileFormat):
    if fileFormat not in processor:
        sys.exit(f'File format not supported: {fileFormat}')

def getRawFileMetadata(
    fileName: str,
    projectPath: str,
    fileFormat: str,
    siteID: str,
    timezone: str,
    ignoreTraces: list = [],
    renameTraces: dict = {}
    ):
    check(fileFormat)
    out = processor[fileFormat](
        projectPath=projectPath,
        siteID=siteID,
        fileName=fileName,
        mode='identifyTraces',
        ignoreTraces=ignoreTraces,
        renameTraces=renameTraces
        )
    
    out.formatMetadata()
    out.traces = json.dumps(out.traces)
    return(out.to_dict())
        
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