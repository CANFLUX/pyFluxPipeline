from dataclasses import dataclass, field
from datetime import datetime
from helperFunctions import baseClass, randomID
import numpy as np

mdMap = baseClass.mdMap

sensorTypes = {
'EC':['sonic','sonic-irga','irga','irga-closed','fast_t_sensor'],
'Biomet': ['biomet']
}

@dataclass(kw_only=True)
class common(baseClass.baseDataClass):
    dateIn: datetime = None
    dateOut: datetime = None
    stationName: str = field(
        default = '',
        metadata = mdMap('Custom descriptor variable')
            )
    manufacturer: str = field(
        default = '',
        metadata = mdMap('Self explanatory')
        )
    modelName: str = field(
        default='',
        metadata = mdMap('The logger model, auto-filled from class name')
        )
    serialNumber: str = field(
        default = '',
        metadata = mdMap('Serial# (if known)')
        )
    hardwareID: str = field(init=False,repr=False)

    def __post_init__(self):
        if self.serialNumber is None:
            self.logMessage(f"serial number missing, unique ID required, generating a random ID")
            self.serialNumber = randomID.randomID(5)
        self.manufacturer = self.manufacturer.lower()
        self.modelName = self.modelName.lower()
        self.hardwareID = f"{self.modelName}-{self.serialNumber}"

        super().__post_init__()

@dataclass(kw_only=True)
class dataLogger(common):
    dataLoggerID: str = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        if self.dataLoggerID is None:
            self.dataLoggerID = self.hardwareID


@dataclass(kw_only=True)
class sensorPosition():
    Zm: float = field(default = None,metadata=mdMap('Measurement height in meters (negative for depth), for EC sensors Sonic is reference, all others are blank'))
    northwardSeparation: float = field(default = None,metadata=mdMap('Northward separation from reference sonic (in m).  For EC sensors, value is relative to the reference sonic, and can be calculated from xSeparation & ySeparation + northOffset if not provided.'))
    eastwardSeparation: float = field(default = None,metadata=mdMap('Eastward separation from reference sonic (in m).  For EC sensors, value is relative to the reference sonic, and can be calculated from xSeparation & ySeparation + northOffset if not provided.'))
    
    northOffset: float = field(default = None, metadata=mdMap('Offset from North in degrees (clockwise) of main sonic'))
    verticalSeparation: float = field(default = None,metadata=mdMap('Vertical separation from reference sonic (in m) required for irgas, and any secondary sonics.'))
    xSeparation: float = field(default = None,metadata=mdMap('Lateral separation from reference sonic (in m) parallel to the main axis of the sonic (towards mast/sonic head = positive).  See Fig D2 in (https://s.campbellsci.com/documents/us/manuals/easyflux-dl-cr6op.pdf) for example.  Required for irgas, and any secondary sonics to calculate northward/eastward separation if not provided.'))
    ySeparation: float = field(default = None,metadata=mdMap('Lateral separation from reference sonic (in m) perpendicular to the main axis of the sonic (right of mast/sonic head = positive).  See Fig D2 in (https://s.campbellsci.com/documents/us/manuals/easyflux-dl-cr6op.pdf) for example.  Required for irgas, and any secondary sonics to calculate northward/eastward separation if not provided.'))

    tubeLenght: float = field(default = 0.0,metadata=mdMap('Length of closed path tube'))
    tubeDiameter: float = field(default = 0.0,metadata=mdMap('Diameter of closed path tube'))

    def getPosition(self):
        if self.eastwardSeparation is None or self.northwardSeparation is None:
            self.geographicSeparation()
        elif self.xSeparation is None or self.ySeparation is None:
            self.cartesianSeparation()
        if self.verticalSeparation is None:
            self.logError('Specify vertical separation')
                
    def geographicSeparation(self):
        # Convert to radians
        # **Note**: north offset is relative to geographic (meteorologic) north, while x,y offsets are in cartesian coordinates.  To perform the coordinate rotation properly theta must be converted to cartesian coordinate (positive is counter-clockwise from the x axis)
        theta = np.deg2rad(270-self.northOffset)
        # Calculate counter-clockwise rotation matrix
        R = np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
        # Evaluate rotation matrix.
        v = np.array([[self.xSeparation,self.ySeparation]])
        Rv = (R*v)
        Rv = Rv.sum(axis=1).round(3)
        self.northwardSeparation = float(Rv[1])
        self.eastwardSeparation = float(Rv[0])
        # breakpoint()
        # return(northwardSeparation,eastwardSeparation)
    
    def cartesianSeparation(self,tolerance=0.01):
        # Get the inverse of geographic separation
        # If xy not provided, calculate, if provided along with north/south check values make sense
        theta = np.deg2rad(self.northOffset-270)
        R = np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
        v = np.array([[self.eastwardSeparation,self.northwardSeparation]])
        Rv = (R*v)
        Rv = Rv.sum(axis=1).round(3)
        xSeparation = float(Rv[0])
        ySeparation = float(Rv[1])
        if self.xSeparation is not None and self.ySeparation is not None:
            if abs(self.xSeparation-xSeparation) > tolerance or abs(self.ySeparation-ySeparation) > tolerance:
                self.logError(f"provided and calculated (from north/eastSeparation + bearing) xSeparation {self.xSeparation} and {xSeparation} or ySeparation {self.ySeparation}, {ySeparation} differ by more than the tolerance of {tolerance}, double-check you configurations file")
        else:
            self.xSeparation = float(Rv[0])
            self.ySeparation = float(Rv[1])

    
@dataclass(kw_only=True)
class sensor(common,sensorPosition):
    sensorID: str = field(default=None)
    sensorType: str = field(default=None,metadata=mdMap('type of sensor',options=sensorTypes['EC']+sensorTypes['Biomet']))
    sensorClass: str = field(default=None)
    

    def __post_init__(self):
        super().__post_init__()
        self.logMessage('Update sensor checks?')
        if self.sensorType.lower() in sensorTypes['EC']:
            if self.sensorType in ['sonic','sonic-irga']:
                if self.Zm is None:
                    self.logError('Specify measurement height')
            else:
                self.getPosition()
            self.sensorClass = 'EC'
        elif self.sensorType.lower() in sensorTypes['Biomet']:
            self.sensorClass = 'Biomet'
        
        if self.sensorID is None:
            self.sensorID = self.hardwareID
        if self.dateIn is None:
            self.logError(f"{self.sensorID} missing required dateIn")   

        if self.sensorType != 'irga-closed':
            self.__dataclass_fields__['tubeLenght'].repr=False
            self.__dataclass_fields__['tubeDiameter'].repr=False
        else:
            self.__dataclass_fields__['tubeLenght'].repr=True
            self.__dataclass_fields__['tubeDiameter'].repr=True
        if self.sensorType == 'irga' or self.sensorType == 'irga-closed':
            self.__dataclass_fields__['Zm'].repr=False
        else:
            self.__dataclass_fields__['Zm'].repr=True

