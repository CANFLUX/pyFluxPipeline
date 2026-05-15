from dataclasses import dataclass, field
from datetime import datetime
from helperFunctions import baseClass, randomID
import numpy as np

mdMap = baseClass.mdMap

@dataclass(kw_only=True)
class common(baseClass.baseDataClass):
    dateIn: datetime = None
    dateOut: datetime = None
    stationName: str = field(
        default = None,
        metadata = mdMap('Custom descriptor variable')
            )
    manufacturer: str = field(
        default = None,
        metadata = mdMap('Self explanatory')
        )
    modelName: str = field(
        default=None,
        metadata = mdMap('The logger model, auto-filled from class name')
        )
    serialNumber: str = field(
        default = None,
        metadata = mdMap('Serial# (if known)')
        )
    hardwareID: str = field(init=False,repr=False)

    def __post_init__(self):
        if self.serialNumber is None:
            self.logMessage(f"serial number missing, unique ID required, generating a random ID")
            self.serialNumber = randomID.randomID(5)
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

    def getPosition(self,sensorType):
        if sensorType not in ['sonic','sonic-irga','irga']:
            return
        elif sensorType in ['sonic','sonic-irga']:
            if 'Zm' is None:
                self.logError('Specify measurement height')
            # for v in ['northwardSeparation', 'eastwardSeparation',  'verticalSeparation', 'xSeparation', 'ySeparation']:
            #     if getattr(self,v) is None:
            #         setattr(self,v,0.0)
        else:
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
    sensorType: str = field(default=None,metadata=mdMap('type of sensor',options=['sonic','sonic-irga','irga','biomet']))
    

    def __post_init__(self):
        super().__post_init__()
        if self.sensorType is not None:
            self.getPosition(self.sensorType.lower())
        
        if self.sensorID is None:
            self.sensorID = self.hardwareID
        