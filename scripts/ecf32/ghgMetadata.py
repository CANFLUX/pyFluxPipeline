import os
from functools import partial
from datetime import datetime
from configparser import ConfigParser
from dataclasses import dataclass, field, make_dataclass
from helperFunctions.baseClass import baseDataClass

def getSec(cfg,sec):
    return(dict(cfg[sec]))

configPath = os.path.join(os.path.split(__file__)[0].split('scripts')[0],'configurationFiles','ghgTemplates')

# Read config files as templats for dataclasses
ghgMetadata = ConfigParser()
ghgMetadata.read(os.path.join(configPath,'template.metadata'))
ghgMetadata = make_dataclass('dotEddyPro',[(fld,dict,field(default_factory=partial(getSec,cfg=ghgMetadata,sec=fld))) for fld in ghgMetadata.keys()])

eddyproProject = ConfigParser()
eddyproProject.read(os.path.join(configPath,'template.eddypro'))
eddyproProject = make_dataclass('dotEddyPro',[(fld,dict,field(default_factory=partial(getSec,cfg=eddyproProject,sec=fld))) for fld in eddyproProject.keys()])

yamlTranslator = baseDataClass().loadDict(os.path.join(configPath,'ghgTranslations.yml'))

@dataclass(kw_only=True)
class eddyproProjectWriter(baseDataClass,eddyproProject):

    def __post_init__(self):
        self.Project['file+type'] = 7
        super().__post_init__()

    def setDates(self,startDate,stopDate):
        startDate=datetime.fromisoformat(startDate)
        if stopDate is None: stopDate = datetime.now()
        else: stopDate=datetime.fromisoformat(stopDate)
        for key,value in eddyproProject().__dict__.items():
            for dval in [k.split('start_date')[0] for k in value if 'start_date' in k]:
                value[f"{dval}start_date"] = startDate.strftime('%Y-%m-%d')
                value[f"{dval}start_time"] = startDate.strftime('%H:%M')
                value[f"{dval}end_date"] = stopDate.strftime('%Y-%m-%d')
                value[f"{dval}end_time"] = stopDate.strftime('%H:%M')
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
        for key in eddyproProject.__annotations__:
            if key == 'DEFAULT':
                continue
            epOut.add_section(key)
            epOut[key] = getattr(self,key)
        with open(self.Project['file_name'],'w+') as fout:
            fout.write(';EDDYPRO_PROCESSING\n')
            epOut.write(fout)



# Metadata format of LICOR .ghg files
@dataclass(kw_only=True)
class ghgMetadataWriter(baseDataClass,ghgMetadata):

    def __post_init__(self):
        self.Project['creation_date'] = datetime.now().isoformat()
        self.Project['last_change_date'] = self.Project['creation_date']

    def setSite(self,siteConfig,sensorList,start_date=None,stop_date=None,retrunDict=True):
        if start_date is None:
            self.Project['start_date'] = siteConfig.startDate.isoformat()
        else:
            self.Project['start_date'] = start_date.isoformat()
        if stop_date is None:
            if siteConfig.stopDate:
                self.Project['end_date'] = siteConfig.stopDate.isoformat()
        else:
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
        self.setInstruments(siteConfig,sensorList)
        if retrunDict:
            return(self.to_dict())

    def setInstruments(self,siteConfig,sensorSet):
        ix = 0
        for i,sensor in enumerate(sensorSet):
            ix += 1
            try:
                sensor = siteConfig.sensors[sensor]
            except:
                breakpoint()
            self.Instruments[f"instr_{ix}_manufacturer"] = sensor.manufacturer
            self.Instruments[f"instr_{ix}_model"] = sensor.modelName
            self.Instruments[f"instr_{ix}_id"] = sensor.sensorID
            if 'sonic' in sensor.sensorType:
                if ix != 1:
                    print('Not setup for multi-sonic setup yet')
                    breakpoint()
                self.Instruments[f"instr_{ix}_height"] = sensor.Zm
                self.Instruments[f"instr_{ix}_north_offset"] = sensor.northOffset
            if sensor.sensorType == 'sonic-irga':
                ix += 1
                self.Instruments[f"instr_{ix}_manufacturer"] = sensor.manufacturer
                self.Instruments[f"instr_{ix}_model"] = sensor.modelName
                self.Instruments[f"instr_{ix}_id"] = sensor.sensorID
            if 'irga' in sensor.sensorType:
                self.Instruments[f"instr_{ix}_manufacturer"] = sensor.manufacturer
                self.Instruments[f"instr_{ix}_northward_separation"]=0.00
                self.Instruments[f"instr_{ix}_eastward_separation"]=0.00
                self.Instruments[f"instr_{ix}_vertical_separation"]=0.00
                if sensor.sensorType == 'irga-closed':
                    self.Instruments[f"instr_{ix}_tube_length"]=0.0
                    self.Instruments[f"instr_{ix}_tube_diameter"]=0.0
                    self.Instruments[f"instr_{ix}_tube_flowrate"]=0.00

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
        # map all variables onto preferred vairables (first in list from yamlTranslator *if any present*)
        vnList = [values['variableName'] for values in traces.values()]
        variables = {
            names[0]:var for var,names in {
                var:[name for name in names if name in vnList]
                for var,names in yamlTranslator['variable'].items()
                }.items() 
            if len(names)
            }
        return(variables)

    def translate(self,key,value):
        if key in ['measurementType']:
            for key,v in yamlTranslator[key].items():
                if value in v or value == v:
                    return(key)
            return('')
        elif key == 'instrument':
            for instrument in self.instrumentList:
                if instrument.rsplit('_')[0] not in yamlTranslator['instrument'].keys():
                    self.logMessage(f'Add variables for {instrument.rsplit('_')[0]}')
                elif value in yamlTranslator['instrument'][instrument.rsplit('_')[0]]:
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



   