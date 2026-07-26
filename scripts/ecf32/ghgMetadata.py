import os
from datetime import datetime
from configparser import ConfigParser
from dataclasses import dataclass, field
from helperFunctions.baseClass import baseDataClass

eddyproMetadataTemplate = ConfigParser()
eddyproMetadataTemplate.read(os.path.join(os.path.split(__file__)[0],'template.metadata'))

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
            self.__setattr__(section,dict(eddyproMetadataTemplate[section]))
        self.Project['creation_date'] = datetime.strftime(datetime.now(),format='%Y-%m-%dT%H:%M:%S')
        self.Project['lastChangeDate'] = self.Project['creation_date']

    def siteData(self,siteConfig,sensorList,retrunDict=True):
        self.Project['start_date'] = datetime.strftime(siteConfig.startDate,format='%Y-%m-%dT%H:%M:%S')
        if siteConfig.stopDate:
            self.Project['end_date'] = datetime.strftime(siteConfig.stopDate,format='%Y-%m-%dT%H:%M:%S')
        self.Site['site_id'] = siteConfig.siteID
        if siteConfig.siteName:
            self.Site['site_name'] = siteConfig.siteName
        self.Site['latitude'] = siteConfig.lat_lon[0]
        self.Site['longitude'] = siteConfig.lat_lon[1]
        if siteConfig.altitude:
            self.Site['altitude'] = siteConfig.altitude
        if siteConfig.canopyHeight:
            self.Site['canopy_height'] = siteConfig.canopyHeight
        self.sensorData(siteConfig,sensorList)
        if retrunDict:
            return(self.to_dict())

    def sensorData(self,siteConfig,sensorSet):
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


    def fileData(self,fileConfig):
        breakpoint()


    #     kl = list(self.Instruments.keys())
    #     for key in kl:
    #         kix = int(key.split('_')[1])
    #         if kix>ix:
    #             self.Instruments.pop(key)
   