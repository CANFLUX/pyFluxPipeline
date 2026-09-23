import os
from datetime import datetime
from configparser import ConfigParser
from dataclasses import dataclass, field
from helperFunctions.baseClass import baseDataClass

configPath = os.path.join(os.path.split(__file__)[0].split('scripts')[0],'configurationFiles')

eddyproMetadataTemplate = ConfigParser()
eddyproMetadataTemplate.read(os.path.join(configPath,'template.metadata'))
translator = baseDataClass().loadDict(os.path.join(configPath,'ghgTranslations.yml'))

def measurementType(units):
    # Translate to eddypro specific expectation (gas samples only)
    if 'm-3' in units or 'm^3' in units:
        mType = 'density'
    elif 'mol' in units:
        mType = 'mixing ratio'
    else:
        mType = None
    return(mType)

def variables(variableName):
    ghgVariables = {
        'u':['Ux'],
        'v':['Uy'],
        'w':['Uz'],
        'ts':['T_SONIC'],
        'sos':[],
        'anemometer_diagnostic':['diag_sonic'],
        'co2':['CO2_density','CO2_density_fast_tmpr'],
        'h2o':['H2O_density'],
        'ch4':['CH4_density', 'CH4_mole_fraction'],
        'n2o':[],
        'air_t':['TA_1_1_1','Temperature'],
        'air_p':['PA','Pressure'],
        'co2_signal':['CO2_sig_strgth'],
        'h2o_signal':['H2O_sig_strgth'],
        'diag_72':[],
        'diag_75':[],
        'diag_77':['Diagnostic'],
        'ch4_signal':['RSSI_LI7700'],
        'flowrate':[],
        'fast_t':[],
        'cell_t':[],
        'int_t_1':[],
        'int_t_2':[],

    }
    for key,value in ghgVariables.keys():
        if variableName in value:
            return(key)    
    return(variableName)


# Metadata format of LICOR .ghg files
@dataclass(kw_only=True)
class ghgMetadata(baseDataClass):
    Project: dict = None
    Files: dict = None
    Site: dict = None
    Station: dict = None
    Timing: dict = None
    Instruments: dict = None
    FileDescription: dict = None

    def __post_init__(self):
        for section in eddyproMetadataTemplate.sections():
            if getattr(self,section) is None:
                self.__setattr__(section,dict(eddyproMetadataTemplate[section]))
        self.Project['creation_date'] = datetime.now().isoformat()
        self.Project['lastChangeDate'] = self.Project['creation_date']

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
            sensor = siteConfig.sensors[sensor]
            self.Instruments[f"instr_{ix}_manufacturer"] = sensor.manufacturer
            self.Instruments[f"instr_{ix}_model"] = sensor.modelName
            self.Instruments[f"instr_{ix}_id"] = sensor.sensorID
            if 'sonic' in sensor.sensorType:
                if ix != 1:
                    print('Not setup for multi-sonic setup yet')
                    breakpoint()
                self.Instruments[f"instr_{ix}_height"] = sensor.Zm
                self.Instruments[f"instr_{ix}_north_offset"] = sensor.northOffset
                # print('path length?')
                # instr_2_vpath_length=1.0000
                # instr_2_hpath_length=1.0000
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
                # print('path length?')
                # instr_2_vpath_length=1.0000
                # instr_2_hpath_length=1.0000


    def setFileDescription(self,traces):
        col_n = [k for k in self.FileDescription.keys() if k.startswith('col_1')]
        columns = {k.replace('_1_','_n_'):self.FileDescription.pop(k) for k in col_n}
        print(columns)
        for i,(k,v) in enumerate(traces.items()):
            self.FileDescription[f'col_{i}_variable'] = self.translate('variable',k)
            breakpoint()
            self.FileDescription[f"col_{i}_instrument"] = v['sensorID']
            # print(i,k,v)
            # print()
        breakpoint()

    def translate(self,key,value):
        for k,v in translator[key].items():
            if value in v or value == v:
                return(k)
        # return(value)
        return('')



   