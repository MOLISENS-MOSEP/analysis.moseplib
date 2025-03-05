"""
WMO Synop Code 4680 wawa (Present Weather, automated station) and preciputaion 
type as defined by Lufft.
"""

from dataclasses import dataclass


@dataclass
class WMOCode:
    # code: int
    description: str
    limits: str | None


wmo_codes = {
    00: WMOCode("No significant weather", None),
    51: WMOCode("drizzle, not freezing, slight", "< 0,1mm/h"),
    52: WMOCode("drizzle, not freezing, moderate", ">= 0,1mmh ... < 0 ,5mm/h"),
    53: WMOCode("drizzle, not freezing, heavy", ">= 0,5mm"),
    57: WMOCode("drizzle + rain, slight", "< 2,5mm/h"),
    58: WMOCode("drizzle + rain, moderate/heavy", ">= 2,5mm/h"),
    61: WMOCode("rain not freezing, slight", "< 2,5mm/h"),
    62: WMOCode("rain, not freezing, moderate", ">= 2,5mm/h ... < 10mm/h"),
    63: WMOCode("rain, not freezing, heavy", ">= 10mm/h"),
    67: WMOCode("rain/drizzle + snow, slight", "< 2,5mm/h"),
    68: WMOCode("rain/drizzle + snow, mod./heavy", ">= 2,5mm/h"),
    71: WMOCode("snow, slight", "< 1mm/h"),
    72: WMOCode("snow, moderate", ">= 1mm/h ... < 4,0mm/h"),
    73: WMOCode("snow, heavy", "> 4,0mm/h"),
    89: WMOCode("hail", None),
}


precipitation_type = {
    0: "No precipitation",
    40: "unspecified precipitation",
    60: "Liquid precipitation, e.g. rain",
    67: "freezing rain",
    69: "sleet",
    70: "Solid precipitation, e.g. snow",
    90: "hail",
}
