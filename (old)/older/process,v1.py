"""
The main algorithm for processing an input table of changes,
doing all the geometric changes and creating the final shapefile.
"""

# The idea
# ========
# For each composite prov (ie it received territory from another):
#	Cut into subparts based on geotransfer entries.
#
# After processing all changes for the event:
# 	Group all subparts by old prov (incl the newer prov if survived)
#	If more than one subpart incl newer prov:
#		Union all geoms
#	Else:
#		Just keep the part


##############

filepath = "pshapes_test.xlsx"


import itertools
import datetime
import dateutil, dateutil.parser
import pygeoj
import shapely, shapely.ops, shapely.geometry



# Validate that the table is correctly formatted for parsing
# ...
def validate_table():
    pass



# Read the table and insert into event-changes object model hierarchy

class Event:
    def __init__(self):
        self.id = None
        self.date = None
        self.changes = []

class TransferChange:
    def __init__(self, type, fromprov, toprov, cutline, selectorpoint):
        self.type = type
        self.fromprov = fromprov
        self.toprov = toprov
        self.cutline = shapely.geometry.shape(eval(cutline))
        self.selectorpoint = shapely.geometry.shape(eval(selectorpoint))

class SplitChange:
    def __init__(self, type, fromprov, toprov):
        self.type = type
        self.fromprov = fromprov
        self.toprov = toprov

import sys
sys.path.append(r"C:\Users\kimo\Documents\GitHub\Tably")
import tably
fulltable = tably.load(filepath)
events = []
for changetable in fulltable.split(["EventID"]):
    event = Event()
    event.id = changetable[0].dict["EventID"]
    event.date = dateutil.parser.parse(changetable[0].dict["EventDate"])
    for row in changetable:
        if row["Type"] in ("FullTransfer","PartTransfer"):
            if not row["CutLine"] or not row["FromProv"]:
                continue
            change = TransferChange(row["Type"],
                                    row["FromProv"],
                                    row["ToProv"],
                                    row["CutLine"],
                                    row["SelectorPoint"])
        elif row["Type"] == "Breakaway":
            change = SplitChange(row["Type"],
                                    row["FromProv"],
                                    row["ToProv"])
        else:
            continue
        print row["Type"]
        event.changes.append(change)
    events.append(event)
    



# Start by registering all contemporary provs to final data
# MAKE INTO AN OBJECT INSTEAD, AND ONLY WRITE TO FILE AFTER?
# AND GROUP BOTH PROVS AND CHANGE TABLE BY COUNTRY, SO NOT TOO MUCH INFO AT ONCE.

finaldata = pygeoj.GeojsonFile()
for feat in pygeoj.load("BaseData/natearthprovs.geojson", encoding="latin1"):
    if feat.properties["geonunit"] != "Vietnam": continue
    finaldata.add_feature(properties={"id": feat.properties["code_hasc"],
                                      "id2": feat.properties["gn_a1_code"],
                                      "StartDate": datetime.date(year=1946, month=1, day=1),
                                      "EndDate": datetime.date(year=2014, month=12, day=31)
                                      },
                          geometry=feat.geometry)

def idsequal(find, comparison):
    if comparison.properties["id"] == find:
        return True
    elif find == "VN.HI" and "id2" in comparison.properties and comparison.properties["id2"] == "VN.44":
        return True
    
def find_prov(provid, provsequal=idsequal):
    "Lookup id and return matching feature GeoJSON among existing registered provs"
    newprovs = sorted((feat for feat in finaldata if provsequal(provid, feat)), key=lambda f: f.properties["EndDate"])
    if newprovs:
        return newprovs[0]


# Process input and create output
# NOTE: new entry is created if: 1) just new info [but not guaranteed to include all such changes], 2) new info and new geometry, 3) just new geometry

class ProvPart:
    def __init__(self):
        self.fromprov = None
        self.toprov = None
        self.geom = None

# For each event
for event in events:
    
    # For each change
    subparts = []
    for change in event.changes:

        # Get info
        print change.fromprov, change.toprov
        subpart = ProvPart()
        subpart.fromprov = change.fromprov
        subpart.toprov = change.toprov
        newprov = find_prov(change.toprov)
        if not newprov:
            # couldnt find provcode, need better lookup, maybe using multiple ids
            continue 
        newprovgeom = shapely.geometry.shape(newprov.geometry)

        # Get geom from newer prov, cut only subpart where necessary
        if change.type in ("FullTransfer","PartTransfer"):
            print change.fromprov, "cut"
            print newprovgeom.area
            # INSTEAD OF USING SPLITLINE, USE PURE POLYGON OR MULTIPOLYGON INTERSECTION INSTEAD
            # THIS WAY BETTER HANDLE HOLES AND INCLUDE ISLANDS (WHICH WOULD BE UNAFFECTED IF USING SPLITLINE)
            # AND NO MORE NEED FOR SELECTOR POINT            
            cutgeoms = shapely.ops.polygonize(newprovgeom.boundary.union(change.cutline))
            cutgeoms = list(cutgeoms)
            print len(cutgeoms)
            breakoffs = [geom for geom in cutgeoms if geom.intersects(change.selectorpoint)]
            subpart.geom = shapely.ops.cascaded_union(breakoffs)
            # AND AFTER find way to trim the breakoffs off the receiving prov, by taking the difference from the unioned breakoffs
            # DO SO ONLY ONCE AFTER FINDING ALL BREAKOFFS BY GROUPING THIS ENTIRE FIRST PART BY TOPROV (instead of for change in event.changes)
            ###remainders = [geom for geom in cutgeoms if not geom.intersects(change.selectorpoint)]
            ###newprov.geom = shapely.ops.cascaded_union(remainders)
            # ...
            print subpart.geom.area
        else:
            print change.fromprov, "normal"
            if change.type == "NewInfo":
                # set subparts info to that of oldprov
                # OR maybe just create newinfo event and handle that during next groupby oldprov stage
                pass
            elif change.type == "Breakaway":
                # WHAT about breakoffs, if the main from which there was a breakoff has a newinfo entry then fine,
                # HOWEVER if it remained unchanged, we still need a separate entry with updated geometry for the main
                # SO prob best to just add the breakoff difference immediately, and only update its info after if any
                pass
                
            subpart.geom = newprovgeom

        subparts.append(subpart)

    # Group and union all geom parts by old prov
    for provid,subparts in itertools.groupby(subparts, key=lambda sb: sb.fromprov):
        subparts = list(subparts)
        
        # do we also need to add newer version of the fromprov (if didnt dissolve) so parts can be unioned with main?
        # yes, necessary, because not all provs that give away territory also change their info as a separate entry so we cannot rely on that.
        # so if there is a newinfo entry for the giving prov
        # lookup the geometry based on the toprov newinfo
        # otherwise there was no newinfo change but still needs a new geometry so just lookup based on the fromprov giving info
        # eg
        #if subpart.type in ("PartTransfer","Breakaway"):
        #    # find newer version of fromprov and add to subparts list so can be unioned
        #maybe after change info if newinfo type change??
        # ...
        if len(subparts) > 1:
            print provid, "union"
            fullgeom = shapely.ops.cascaded_union([part.geom for part in subparts])
        else:
            print provid, "single"
            fullgeom = subparts[0].geom
                        
        # Add to final data
        oldprov = pygeoj.Feature(properties={"id": provid,
                                             "StartDate": None,
                                             "EndDate": event.date},
                                  geometry=fullgeom)
        finaldata.add_feature(oldprov)
        
        # Set startdate for newer prov
        for subpart in subparts:
            newprov = find_prov(subpart.toprov)
            newprov.properties["StartDate"] = event.date


#dsafdas

# Save final geojson table
for feat in finaldata:
    feat.properties["StartDate"] = str(feat.properties["StartDate"])
    feat.properties["EndDate"] = str(feat.properties["EndDate"])
finaldata.save("processed.geojson")




        
        

