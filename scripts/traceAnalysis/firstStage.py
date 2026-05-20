from dataclasses import dataclass,field
from scripts.database.database import database

@dataclass(kw_only=True)
class firstStage(database):
    sites: list
    years: list

    def __post_init__(self):
        super().__post_init__()
        breakpoint()