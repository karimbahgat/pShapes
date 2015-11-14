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




#############################################################



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
    def __init__(self, type, fromprov, toprov, cutpoly):
        self.type = type
        self.fromprov = fromprov
        self.toprov = toprov
        self.cutpoly = shapely.geometry.shape(eval(cutpoly))

class SplitChange:
    def __init__(self, type, fromprov, toprov):
        self.type = type
        self.fromprov = fromprov
        self.toprov = toprov

class NewInfo:
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
            if not row["CutPoly"] or not row["FromProv"]:
                continue
            change = TransferChange(row["Type"],
                                    row["FromProv"],
                                    row["ToProv"],
                                    row["CutPoly"])
        elif row["Type"] == "Breakaway":
            change = SplitChange(row["Type"],
                                    row["FromProv"],
                                    row["ToProv"])
        elif row["Type"] == "NewInfo":
            change = NewInfo(row["Type"],
                             row["FromProv"],
                             row["ToProv"])
        else:
            continue
        print row["Type"]
        event.changes.append(change)
    events.append(event)
    


#############################################################


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




#############################################################


# Process input and create output
# NOTE: new entry is created if: 1) just new info [but not guaranteed to include all such changes], 2) new info and new geometry, 3) just new geometry

class Remainder:
    def __init__(self, fromprov, geom):
        self.type = "Remainder"
        self.fromprov = fromprov
        self.geom = geom
        
# For each event
for event in events:
    print "----------"
    print event



    # 1) Group all entries by toprov
    subparts = []
    for toprovid,changes in itertools.groupby(event.changes, key=lambda ch: ch.toprov):
        changes = list(changes)

        # Lookup the toprov geometry
        newprov = find_prov(toprovid)
        if not newprov:
            # couldnt find provcode, need better lookup, maybe using multiple ids
            continue
        newprovgeom = shapely.geometry.shape(newprov.geometry)

        # Also change the startdate of the newer prov
        newprov.properties["StartDate"] = event.date
        
        # For each change
        for change in changes:
            print change.fromprov, change.toprov

            # Handle each type of change separately
            if change.type == "FullTransfer":
                # Get the geom that was transferred as the intersection with the change cutpoly
                change.geom = newprovgeom.intersection(change.cutpoly)
                subparts.append(change)

            elif change.type == "PartTransfer":
                # Get the geom that was transferred as the intersection with the change cutpoly
                change.geom = newprovgeom.intersection(change.cutpoly)
                subparts.append(change)

            elif change.type == "Breakaway":
                # The newprov is a breakaway, so the whole thing used to be part of an older prov
                # ...and so should just be unioned as it is
                change.geom = newprovgeom
                subparts.append(change)

        # Trim the breakoffs off the receiving toprov so it can later be added as its own prov, by taking the difference from the unioned breakoffs
        # FIGURE THIS OUT BETTER, WHEN IS NEEDED AND WHEN NOT??
        breakoffs = [part for part in subparts if part.type != "NewInfo"]
        print "breakoffs", breakoffs
        if len(breakoffs) > 1:
            allbreakoffs = shapely.ops.cascaded_union([part.geom for part in breakoffs])
        elif len(breakoffs) == 1:
            allbreakoffs = breakoffs[0].geom
            trimmedgeom = newprovgeom.difference(allbreakoffs)
            if trimmedgeom:
                print "trimmedgeom", newprovgeom.area, allbreakoffs.area, subparts
                newinfo = next((change for change in changes if change.type == "NewInfo"), None)
                if newinfo:
                    prereceiving = Remainder(newinfo.fromprov, trimmedgeom)
                else:
                    prereceiving = Remainder(toprovid, trimmedgeom)
                subparts.append(prereceiving)

        # If newinfo is the only change
        if len(changes) == 1 and changes[0].type == "NewInfo":
            # The oldprov only changed info, so should have the same geom as the newprov
            changes[0].geom = newprovgeom
            subparts.append(changes[0])




    # 2) Group and union all geom parts by fromprov
    for fromprovid,subparts in itertools.groupby(subparts, key=lambda sb: sb.fromprov):
        subparts = list(subparts)
        
        # Union all parts belonging to same fromprov, ie breakaways and parttransfers
        print fromprovid, subparts
        if len(subparts) > 1:
            print fromprovid, "union"
            fullgeom = shapely.ops.cascaded_union([part.geom for part in subparts])
        else:
            # Only one item, so prob means there was nothing left of the giving prov, ie fulltransfers or maybe also just newinfo
            print fromprovid, "single"
            fullgeom = subparts[0].geom
            


                        
        # 3) Add to final data
        #print fullgeom, subparts[0].type
        finaldata.add_feature(properties={"id": fromprovid,
                                             "StartDate": None,
                                             "EndDate": event.date},
                                  geometry=fullgeom)
        


#############################################################

# Save final geojson table
for feat in finaldata:
    feat.properties["StartDate"] = str(feat.properties["StartDate"])
    feat.properties["EndDate"] = str(feat.properties["EndDate"])
finaldata.save("processed.geojson")




        
        

