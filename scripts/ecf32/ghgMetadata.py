
import numpy as np
from datetime import datetime
from configparser import ConfigParser
from dataclasses import dataclass
from submodules.helperFunctions.baseClass import baseDataClass
from scripts.defaultSettings import eddyproTemplate, ghgTemplate, ghgTranslator

# def getSec(cfg,sec):
#     breakpoint()
#     return(dict(cfg[sec]))

# configPath = os.path.join(os.path.split(__file__)[0].split('scripts')[0],'configurationFiles','ghgTemplates')

# breakpoint()
# fromIniDefault(os.path.join(configPath,'template.metadata'))
# # Read config files as templats for dataclasses
# ghgMetadata = ConfigParser()
# ghgMetadata.read()

# #     breakpoint()
# ghgMetadata = make_dataclass('dotEddyPro',[(fld,dict,field(default_factory=partial(getSec,cfg=ghgMetadata,sec=fld))) for fld in ghgMetadata.keys()])

# eddyproProject = ConfigParser()
# eddyproProject.read(os.path.join(configPath,'template.eddypro'))
# eddyproProject = make_dataclass('dotEddyPro',[(fld,dict,field(default_factory=partial(getSec,cfg=eddyproProject,sec=fld))) for fld in eddyproProject.keys()])

# ghgTranslator = baseDataClass().loadDict(os.path.join(configPath,'ghgTranslations.yml'))

@dataclass(kw_only=True)
class eddyproProjectWriter(baseDataClass,eddyproTemplate):

    def __post_init__(self):
        self.Project['file+type'] = 7
        super().__post_init__()

    def setDates(self,dateStart,dateStop):
        dateStart=datetime.fromisoformat(dateStart)
        if dateStop is None: dateStop = datetime.now()
        else: dateStop=datetime.fromisoformat(dateStop)
        for key,value in eddyproTemplate().__dict__.items():
            for dval in [k.split('start_date')[0] for k in value if 'start_date' in k]:
                value[f"{dval}start_date"] = dateStart.strftime('%Y-%m-%d')
                value[f"{dval}start_time"] = dateStart.strftime('%H:%M')
                value[f"{dval}end_date"] = dateStop.strftime('%Y-%m-%d')
                value[f"{dval}end_time"] = dateStop.strftime('%H:%M')
            setattr(self,key,value)

    def fill(self,ghgMetadataFile):
        for key,value in ghgMetadataFile.Project.items():
            if key in getattr(self,'Project'):
                self.Project[key]=value
        self.Project['master_sonic'] = ghgMetadataFile.Instruments['instr_1_id']
        for key,value in self.Project.items():
            if key.startswith('col_'):
                col = key.split('col_')[-1]
                if col in ghgMetadataFile.variableColumns:
                    self.Project[key] = ghgMetadataFile.variableColumns[col]
        self.Project['file_name'] = ghgMetadataFile.Project['file_name'].replace('.metadata','.eddypro')
        self.writeFile()

    def writeFile(self):
        # self.fill(ghgMetadataFile)
        epOut = ConfigParser()
        for key in eddyproTemplate.__annotations__:
            if key == 'DEFAULT':
                continue
            epOut.add_section(key)
            epOut[key] = getattr(self,key)
        with open(self.Project['file_name'],'w+') as fout:
            fout.write(';EDDYPRO_PROCESSING\n')
            epOut.write(fout)



@dataclass(kw_only=True)
class coordinateTransformation:
    Zm: float
    northOffset: float

    def __post_init__(self):        
        # Convert to radians
        # **Note**: north offset is relative to geographic (meteorologic) north, while x,y offsets are in cartesian coordinates.  To perform the coordinate rotation properly theta must be converted to cartesian coordinate (positive is counter-clockwise from the x axis)
        theta = np.deg2rad(270-self.northOffset)
        # Calculate counter-clockwise rotation matrix
        self.R = np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])

    def geographicSeparation(self,xSeparation,ySeparation):
        # Evaluate rotation matrix.
        v = np.array([[xSeparation,ySeparation]])
        Rv = (self.R*v)
        Rv = Rv.sum(axis=1).round(3)
        northwardSeparation = float(Rv[1])
        eastwardSeparation = float(Rv[0])
        return(northwardSeparation,eastwardSeparation)

# Metadata format of LICOR .ghg files
@dataclass(kw_only=True)
class ghgMetadataWriter(baseDataClass,ghgTemplate):

    def __post_init__(self):
        self.Project['creation_date'] = datetime.now().isoformat()
        self.Project['last_change_date'] = self.Project['creation_date']

    def setSite(self,siteConfig,sensorList,start_date=None,stop_date=None,returnDict=True):
        self.Project['start_date'] = start_date.isoformat()
        self.Project['end_date'] = stop_date.isoformat()
        self.Site['site_id'] = siteConfig.siteID
        if siteConfig.siteName:
            self.Site['site_name'] = siteConfig.siteName
        self.Site['latitude'] = siteConfig.lat_lon[0]
        self.Site['longitude'] = siteConfig.lat_lon[1]
        if siteConfig.altitude:
            self.Site['altitude'] = siteConfig.altitude
        if siteConfig.canopyHeight:
            self.Site['canopy_height'] = siteConfig.canopyHeight
        self.setInstruments(sensorList)
        if returnDict:
            return(self.to_dict())

    def setInstruments(self,sensorSet):
        ix = 0
        for i,sensor in enumerate(sensorSet):
            ix += 1
            self.Instruments[f"instr_{ix}_manufacturer"] = sensor.manufacturer
            self.Instruments[f"instr_{ix}_model"] = sensor.modelName
            self.Instruments[f"instr_{ix}_id"] = sensor.instrumentID
            if ix == 1 and 'sonic' in sensor.sensorType:#if 'sonic' in sensor.sensorType:
                if ix != 1:
                    self.logError('Not setup for multi-sonic setup yet')
                self.Instruments[f"instr_{ix}_height"] = sensor.Zm
                self.Instruments[f"instr_{ix}_north_offset"] = sensor.northOffset
                ct = coordinateTransformation(Zm=sensor.Zm,northOffset=sensor.northOffset)
            elif ix == 1:
                self.logError(f'Reference sonic required for EC systems.  Fix error in {self.Site["site_id"]}')
            elif ix > 1 and ('irga' in sensor.sensorType or 'fast_t' in sensor.sensorType):
                n,e = ct.geographicSeparation(sensor.xSeparation,sensor.ySeparation)
                self.Instruments[f"instr_{ix}_northward_separation"]=n
                self.Instruments[f"instr_{ix}_eastward_separation"]=e
                self.Instruments[f"instr_{ix}_vertical_separation"]=sensor.zSeparation
                if sensor.sensorType == 'irga_closed':
                    self.Instruments[f"instr_{ix}_tube_length"]=sensor.tubeLength
                    self.Instruments[f"instr_{ix}_tube_diameter"]=sensor.tubeDiameter
                    # Set to 0, overwritten with data from the file anyway
                    self.Instruments[f"instr_{ix}_tube_flowrate"]=0.00
            else:
                self.logError('Not setup for this edge cases yet')

    def getInstrumentList(self):
        # get list of instruments for cross referencing
        self.instrumentList = [self.Instruments[f'instr_{i+1}_id'] for i,_ in enumerate([k for k in self.Instruments.keys() if k.endswith('_id')])]

    def setFileDescription(self,traces):
        self.getInstrumentList()
        col_n = [k for k in self.FileDescription.keys() if k.startswith('col_1')]
        columns = {k.replace('_1_','_n_'):self.FileDescription.pop(k) for k in col_n}
        # To prevent duplication, get variable translation, then select preffered opton
        selectedVariables = self.variableSelection(traces)
        self.variableColumns = {}
        for ix,values in enumerate(traces.values()):
            i = ix + 1
            if values['variableName'] not in selectedVariables:
                self.FileDescription[f'col_{i}_variable'] = 'ignore'
            else:
                variable = selectedVariables[values['variableName']]
                self.FileDescription[f'col_{i}_variable'] = variable
                self.variableColumns[variable] = i
                self.FileDescription[f"col_{i}_instrument"] = self.translate('instrument',variable)
                self.logMessage('set units, type, etc.')

    def variableSelection(self,traces):
        # map all variables onto preferred vairables (first in list from ghgTranslator *if any present*)
        vnList = [values['variableName'] for values in traces.values()]
        variables = {
            names[0]:var for var,names in {
                var:[name for name in names if name in vnList]
                for var,names in ghgTranslator['variable'].items()
                }.items() 
            if len(names)
            }
        return(variables)

    def translate(self,key,value):
        if key in ['measurementType']:
            for key,v in ghgTranslator[key].items():
                if value in v or value == v:
                    return(key)
            return('')
        elif key == 'instrument':
            for instrument in self.instrumentList:
                if instrument.rsplit('_')[0] not in ghgTranslator['instrument'].keys():
                    self.logMessage(f'Add variables for {instrument.rsplit("_")[0]}')
                elif value in ghgTranslator['instrument'][instrument.rsplit("_")[0]]:
                    return(instrument)
            self.logMessage(f'Could not par instrument for {value}')
            return('')

    def writeFiles(self,filepath):
        self.Project['file_name'] = filepath
        ghgMetadataFile = ConfigParser()
        for key in ghgMetadata.__annotations__:
            if key == 'DEFAULT':
                continue
            ghgMetadataFile.add_section(key)
            ghgMetadataFile[key] = getattr(self,key)
        with open(self.Project['file_name'],'w+') as fout:
            fout.write(';GHG_METADATA\n')
            ghgMetadataFile.write(fout)



   