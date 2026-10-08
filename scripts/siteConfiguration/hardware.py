from dataclasses import dataclass#, field, make_dataclass
from datetime import datetime
from functools import partial
from helperFunctions.baseClass import fromYamlDefault
from typing import Iterable
import numpy as np
import random
import os
# mdMap = baseClass.mdMap

# def getSec(base,name):
#     return(base[name])

# def fieldBuilder(name,base):
#     value = partial(getSec,base=base,name=name)
#     if value() is not None:
#         if not name.startswith('date'):
#             typ = type(value())
#         else:
#             typ = type(datetime.now())
#         if typ not in [dict,list]:  
#             return (name,type(value()),value())
#         else:
#             return (name,type(value()),field(default_factory=value))            
#     else:
#         return (name)

configPath = os.path.join(os.path.split(__file__)[0].split('scripts')[0],'configurationFiles','instrumentation')

# def fromYamlDefault(className,bases=(),dc=True):
#     fileName = os.path.join(configPath,f"{className}.yml")
#     config = baseClass.baseFunctions.loadDict(None,fileName,safe=True)
#     if not dc: return(config)
#     dc = make_dataclass(
#         className,
#         [fieldBuilder(fld,config) for fld in config.keys()],
#         bases=bases,
#         kw_only=True
#     )
#     return dc
@dataclass(kw_only=True)
class sensor():
    # Takes values from configs defined below, maps basic functionality for key fields
    def __post_init__(self):
        self.modelName = self.modelName.lower()
        if self.serialNumber == self.__dataclass_fields__['serialNumber'].default:
            self.serialNumber = f"{str(random.randint(0,999999)).zfill(6)}"
        if self.instrumentID == self.__dataclass_fields__['instrumentID'].default:
            self.instrumentID = f"{self.modelName}_{self.serialNumber}"
        try:
            if not type(self.dateStart) is str:
                self.dateStart = self.dateStart.isoformat()
            self.dateStart = datetime.fromisoformat(self.dateStart)
            if self.dateStop != '':
                if not type(self.dateStop) is str:
                    self.dateStop = self.dateStop.isoformat()
                self.dateStop = datetime.fromisoformat(self.dateStop)
            else:
                self.dateStop = datetime.fromisoformat('2028-03-31T23:59:59+00:00')
            if self.dateStart.tzinfo is None or self.dateStop.tzinfo is None:
                exit(f"Erro in {self.modelName}: dates must specify UTC offset in yaml timestamp, e.g., +00:00, -06:00, etc.")
                self.logError(f'Error in {self.siteID} {obj.modelName}: dateStop: {obj.dateStop}, must specify UTC offset in yaml timestamp, e.g., +00:00, -06:00, etc. ')
        except Exception as e:
            exit(f"Error in {self.modelName}: date objects must be in iso format, e.g. 2099-12-31T23:59:59+00:00\n\n{e}")#

genericSensor = fromYamlDefault(os.path.join(configPath,"genericSensor.yml"),(sensor,))
hardwareModels = fromYamlDefault(os.path.join(configPath,"hardwareModels.yml"),asDataclass=False)
# Read the sensor list-config mapping
for kind in hardwareModels.keys():
    for key,value in hardwareModels[kind].items():
        filePath = os.path.join(configPath,f"{value}.yml")
        hardwareModels[kind][key] = fromYamlDefault(filePath,(genericSensor,))
hardwareModels['path'] = os.path.join(configPath,"hardwareModels.yml")

@dataclass(kw_only=True)
class ecSystem:
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






# @dataclass(kw_only=True)
# class sensorPosition():
#     Zm: float = field(default = None,metadata=mdMap('Measurement height in meters (negative for depth), for EC sensors Sonic is reference, all others are blank'))
#     northwardSeparation: float = field(default = None,metadata=mdMap('Northward separation from reference sonic (in m).  For EC sensors, value is relative to the reference sonic, and can be calculated from xSeparation & ySeparation + northOffset if not provided.'))
#     eastwardSeparation: float = field(default = None,metadata=mdMap('Eastward separation from reference sonic (in m).  For EC sensors, value is relative to the reference sonic, and can be calculated from xSeparation & ySeparation + northOffset if not provided.'))
    
#     northOffset: float = field(default = None, metadata=mdMap('Offset from North in degrees (clockwise) of main sonic'))
#     zSeparation: float = field(default = None,metadata=mdMap('Vertical separation from reference sonic (in m) required for irgas, and any secondary sonics.'))
#     xSeparation: float = field(default = None,metadata=mdMap('Lateral separation from reference sonic (in m) parallel to the main axis of the sonic (towards mast/sonic head = positive).  See Fig D2 in (https://s.campbellsci.com/documents/us/manuals/easyflux-dl-cr6op.pdf) for example.  Required for irgas, and any secondary sonics to calculate northward/eastward separation if not provided.'))
#     ySeparation: float = field(default = None,metadata=mdMap('Lateral separation from reference sonic (in m) perpendicular to the main axis of the sonic (right of mast/sonic head = positive).  See Fig D2 in (https://s.campbellsci.com/documents/us/manuals/easyflux-dl-cr6op.pdf) for example.  Required for irgas, and any secondary sonics to calculate northward/eastward separation if not provided.'))

#     tubeLenght: float = field(default = 0.0,metadata=mdMap('Length of closed path tube'))
#     tubeDiameter: float = field(default = 0.0,metadata=mdMap('Diameter of closed path tube'))

#     def getPosition(self):
#         if self.eastwardSeparation is None or self.northwardSeparation is None:
#             self.geographicSeparation()
#         elif self.xSeparation is None or self.ySeparation is None:
#             self.cartesianSeparation()
#         if self.zSeparation is None:
#             self.logError('Specify vertical separation')
                
#     def geographicSeparation(self):
#         # Convert to radians
#         # **Note**: north offset is relative to geographic (meteorologic) north, while x,y offsets are in cartesian coordinates.  To perform the coordinate rotation properly theta must be converted to cartesian coordinate (positive is counter-clockwise from the x axis)
#         theta = np.deg2rad(270-self.northOffset)
#         # Calculate counter-clockwise rotation matrix
#         R = np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
#         # Evaluate rotation matrix.
#         v = np.array([[self.xSeparation,self.ySeparation]])
#         Rv = (R*v)
#         Rv = Rv.sum(axis=1).round(3)
#         self.northwardSeparation = float(Rv[1])
#         self.eastwardSeparation = float(Rv[0])
#         # breakpoint()
#         # return(northwardSeparation,eastwardSeparation)
    
#     def cartesianSeparation(self,tolerance=0.01):
#         # Get the inverse of geographic separation
#         # If xy not provided, calculate, if provided along with north/south check values make sense
#         theta = np.deg2rad(self.northOffset-270)
#         R = np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
#         v = np.array([[self.eastwardSeparation,self.northwardSeparation]])
#         Rv = (R*v)
#         Rv = Rv.sum(axis=1).round(3)
#         xSeparation = float(Rv[0])
#         ySeparation = float(Rv[1])
#         if self.xSeparation is not None and self.ySeparation is not None:
#             if abs(self.xSeparation-xSeparation) > tolerance or abs(self.ySeparation-ySeparation) > tolerance:
#                 self.logError(f"provided and calculated (from north/eastSeparation + bearing) xSeparation {self.xSeparation} and {xSeparation} or ySeparation {self.ySeparation}, {ySeparation} differ by more than the tolerance of {tolerance}, double-check you configurations file")
#         else:
#             self.xSeparation = float(Rv[0])
#             self.ySeparation = float(Rv[1])

    
# @dataclass(kw_only=True)
# class sensor(common,sensorPosition):
#     instrumentID: str = field(default=None)
#     sensorType: str = field(default=None,metadata=mdMap('type of sensor',options=sensorTypes['EC']+sensorTypes['Biomet']))
#     sensorClass: str = field(default=None)
    

#     def __post_init__(self):
#         super().__post_init__()
#         self.logMessage('Update sensor checks?')
#         if self.sensorType.lower() in sensorTypes['EC']:
#             if self.sensorType in ['sonic','sonic_irga']:
#                 if self.Zm is None:
#                     self.logError('Specify measurement height')
#             else:
#                 self.getPosition()
#             self.sensorClass = 'EC'
#         elif self.sensorType.lower() in sensorTypes['Biomet']:
#             self.sensorClass = 'Biomet'
        
#         if self.instrumentID is None:
#             self.instrumentID = self.hardwareID
#         if self.dateStart is None:
#             self.logError(f"{self.instrumentID} missing required dateStart")   

#         if self.sensorType != 'irga_closed':
#             self.__dataclass_fields__['tubeLenght'].repr=False
#             self.__dataclass_fields__['tubeDiameter'].repr=False
#         else:
#             self.__dataclass_fields__['tubeLenght'].repr=True
#             self.__dataclass_fields__['tubeDiameter'].repr=True
#         if self.sensorType == 'irga' or self.sensorType == 'irga_closed':
#             self.__dataclass_fields__['Zm'].repr=False
#         else:
#             self.__dataclass_fields__['Zm'].repr=True

