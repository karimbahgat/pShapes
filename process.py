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


import itertools
import datetime
import dateutil, dateutil.parser
import pygeoj
import shapely, shapely.ops, shapely.geometry




#############################################################



# Validate that the table is correctly formatted for parsing
# ...
def validate_changetable():
    pass



# Read the table and insert into event-changes object model hierarchy

class Event:
    def __init__(self):
        self.date = None
        self.changes = []

class FullTransferChange:
    def __init__(self, fromprov, toprov, cutpoly):
        self.type = "FullTransfer"
        self.fromprov = fromprov
        self.toprov = toprov
        self.cutpoly = shapely.geometry.shape(eval(cutpoly))

class PartTransferChange:
    def __init__(self, fromprov, toprov, cutpoly):
        self.type = "PartTransfer"
        self.fromprov = fromprov
        self.toprov = toprov
        self.cutpoly = shapely.geometry.shape(eval(cutpoly))

class BreakawayChange:
    def __init__(self, fromprov, toprov):
        self.type = "Breakaway"
        self.fromprov = fromprov
        self.toprov = toprov

class NewInfoChange:
    def __init__(self, fromprov, toprov):
        self.type = "NewInfo"
        self.fromprov = fromprov
        self.toprov = toprov

class Remainder:
    def __init__(self, fromprov, geom):
        self.type = "Remainder"
        self.fromprov = fromprov
        self.geom = geom
        


#############################################################


# Start by registering all contemporary provs to final data
# MAKE INTO AN OBJECT INSTEAD, AND ONLY WRITE TO FILE AFTER?
# AND GROUP BOTH PROVS AND CHANGE TABLE BY COUNTRY, SO NOT TOO MUCH INFO AT ONCE.

def ids_equal(find, comparison):
    # find is just the dict, comparison is the prov obj
    def validid(val):
        if val:
            if isinstance(val, str): return len(val) > 3
            else: return True
    match = any((validid(otherid) and otherid in find.values()
                 for otherid in comparison.ids.values() ))
    #match = find["Name"] == comparison.ids["Name"] or (len(find["HASC"]) > 3 and comparison.ids["HASC"] == find["HASC"])
    return match

class Province:
    def __init__(self, start, end, ids, other, geometry):
        self.start = start
        self.end = end
        self.ids = ids
        self.other = other
        self.geometry = geometry

class ResultsTable:
    def __init__(self, mindate, maxdate):
        self.provs = []
        self.events = []
        self.mindate = mindate
        self.maxdate = maxdate

    def add_province(self, start, end, ids, other, geometry):
        if start is None: start = self.mindate
        if end is None: end = self.maxdate
        prov = Province(start, end, ids, other, geometry)
        self.provs.append(prov)
   
    def find_prov(self, findprov, matchfunc=ids_equal):
        "Lookup id and return matching feature GeoJSON among existing registered provs"
        newprovs = sorted((prov for prov in self.provs if matchfunc(findprov, prov)), key=lambda f: f.end)
        if len(newprovs) > 1:
            print("!!!! Warning, more than one mathcing ids...", [p.ids for p in newprovs])
        if newprovs:
            return newprovs[0]

    def add_event(self, event):
        self.events.append(event)

    def begin_backtracking(self):
        """
        Process input and create output.

        NOTE: new entry is created if: 1) just new info [but not guaranteed to include all such changes], 2) new info and new geometry, 3) just new geometry
        """
                
        # For each event
        for event in sorted(self.events, key=lambda ev: ev.date, reverse=True):
            print "----------"
            print event.date



            # 1) Group all entries by toprov
            print "by toprov"
            subparts = []
            for toprovids,changes in itertools.groupby(event.changes, key=lambda ch: ch.toprov):
                changes = list(changes)

                # Lookup the toprov geometry
                newprov = self.find_prov(toprovids)
                if not newprov or (newprov.geometry["type"] == "GeometryCollection" and not newprov.geometry["geometries"]):
                    # couldnt find provcode, need better lookup, maybe using multiple ids
                    continue

                newprovgeom = shapely.geometry.shape(newprov.geometry)

                print "NEWGEOM", toprovids, newprovgeom.area

                # Also change the startdate of the newer prov
                newprov.start = event.date
                
                # For each change
                for change in changes:
                    print change.type, change.fromprov, change.toprov

                    # Handle each type of change separately
                    if change.type == "FullTransfer":
                        # Get the geom that was transferred as the intersection with the change cutpoly
                        change.geom = newprovgeom.intersection(change.cutpoly)
                        newprovgeom = newprovgeom.difference(change.cutpoly) # trim the geom for each time so no overlap
                        subparts.append(change)

                    elif change.type == "PartTransfer":
                        # Get the geom that was transferred as the intersection with the change cutpoly
                        change.geom = newprovgeom.intersection(change.cutpoly)
                        newprovgeom = newprovgeom.difference(change.cutpoly) # trim the geom for each time so no overlap
                        subparts.append(change)

                    elif change.type == "Breakaway":
                        # The newprov is a breakaway, so the whole thing used to be part of an older prov
                        # ...and so should just be unioned as it is
                        change.geom = newprovgeom
                        subparts.append(change)

                # Trim the breakoffs off the receiving toprov so it can later be added as its own prov, by taking the difference from the unioned breakoffs
                # FIGURE THIS OUT BETTER, WHEN IS NEEDED AND WHEN NOT??
                breakoffs = [ch for ch in changes if ch.type != "NewInfo"]
                print "breakoffs", breakoffs
                if breakoffs:
                    if len(breakoffs) > 1:
                        allbreakoffs = shapely.ops.cascaded_union([part.geom for part in breakoffs])
                    elif len(breakoffs) == 1:
                        allbreakoffs = breakoffs[0].geom
                    trimmedgeom = newprovgeom.difference(allbreakoffs)
                    print newprovgeom.area, allbreakoffs.area, newprov.ids
                    if trimmedgeom:
                        print "trimmedgeom", newprovgeom.area, allbreakoffs.area, subparts
                        newinfo = next((change for change in changes if change.type == "NewInfo"), None)
                        if newinfo:
                            prereceiving = Remainder(newinfo.fromprov, trimmedgeom)
                        else:
                            prereceiving = Remainder(toprovids, trimmedgeom)
                        subparts.append(prereceiving)

                # If newinfo is the only change
                if len(changes) == 1 and changes[0].type == "NewInfo":
                    # The oldprov only changed info, so should have the same geom as the newprov
                    changes[0].geom = newprovgeom
                    subparts.append(changes[0])




            # 2) Group and union all geom parts by fromprov
            print "by fromprov"
            for fromprovids,subparts in itertools.groupby(subparts, key=lambda sb: sb.fromprov):
                subparts = list(subparts)
                
                # Union all parts belonging to same fromprov, ie breakaways and parttransfers
                print fromprovids, subparts
                if len(subparts) > 1:
                    print fromprovids, "union", subparts
                    fullgeom = shapely.ops.cascaded_union([part.geom for part in subparts])
                else:
                    # Only one item, so prob means there was nothing left of the giving prov, ie fulltransfers or maybe also just newinfo
                    print fromprovids, "single"
                    fullgeom = subparts[0].geom
                    


                                
                # 3) Add to final data
                #print fullgeom, subparts[0].type
                if not fullgeom.is_valid or fullgeom.is_empty:
                    continue # hack
                self.add_province(start=None,
                                 end=event.date,
                                 ids=fromprovids,
                                 other={},
                                 geometry=fullgeom.__geo_interface__)






if __name__ == "__main__":

    import pythongis as pg

    CURRENTFILE = r"C:\Users\kimo\Downloads\ne_10m_admin_1_states_provinces\ne_10m_admin_1_states_provinces.shp"
    CHANGESFILE = r"C:\Users\kimo\Downloads\pshapes_raw (7).csv"
    OUTFILE = r"C:\Users\kimo\Downloads\processed.geojson"
    BUILD = 1

    if BUILD:

        # Initiate results table

        results = ResultsTable(mindate=datetime.date(year=1946, month=1, day=1),
                               maxdate=datetime.date(year=2014, month=12, day=31))


        # Load contemporary table
        
        for feat in pg.VectorData(CURRENTFILE, encoding="latin1"):   
            if feat["geonunit"] not in ("Cameroon","Nigeria"): continue
            results.add_province(start=None,
                                 end=None,
                                 ids={"Name": feat["name"],
                                      "HASC": feat["code_hasc"],
                                      "ISO": feat["iso_3166_2"],
                                      "FIPS": feat["fips"]
                                      },
                                 other={},
                                 geometry=feat.geometry)


        # Load events table

        import sys
        sys.path.append(r"C:\Users\kimo\Documents\GitHub\Tably")
        import tably

        eventstable = tably.load(CHANGESFILE) # CSV EXPORT FROM WEBSITE DATABASE
        eventstable = eventstable.exclude('status == "NonActive"')
        for changetable in eventstable.split(["date"]):
            event = Event()

            # parse date correctly
            date = dateutil.parser.parse(changetable[0].dict["date"])
            event.date = datetime.date(year=date.year, month=date.month, day=date.day)
            
            for row in changetable:

                # remove junk tably.<None> obj
                def parseval(val):
                    if not val or val == "X": return None
                    else: return val
                for i,val in enumerate(row):
                    row[i] = parseval(val)

                # create id dicts
                fromprovids = {"Name":row["FromName".lower()],
                               "HASC":row["FromHASC".lower()],
                               "ISO":row["FromISO".lower()],
                               "FIPS":row["FromFIPS".lower()]}
                toprovids = {"Name":row["ToName".lower()],
                             "HASC":row["ToHASC".lower()],
                             "ISO":row["ToISO".lower()],
                             "FIPS":row["ToFIPS".lower()]}
                
                if row["Type".lower()] == "FullTransfer":
                    if not row["transfer_geom"]: #or not row["FromHASC"]:
                        continue
                    change = FullTransferChange(fromprovids,
                                                toprovids,
                                                row["transfer_geom"])
                elif row["Type".lower()] == "PartTransfer":
                    if not row["transfer_geom"]: #or not row["FromHASC"]:
                        continue
                    change = PartTransferChange(fromprovids,
                                                toprovids,
                                                row["transfer_geom"])
                elif row["Type".lower()] == "Breakaway":
                    change = BreakawayChange(fromprovids,
                                             toprovids)
                elif row["Type".lower()] == "NewInfo":
                    change = NewInfoChange(fromprovids,
                                         toprovids)
                else:
                    continue
                print row["Type".lower()]
                event.changes.append(change)
            results.add_event(event)


        # Process and create final provs
        results.begin_backtracking()


        # Save final geojson table
        import pygeoj
        finaldata = pygeoj.GeojsonFile()
        for prov in results.provs:
            properties = {}
            properties.update(prov.ids)
            properties.update(prov.other)
            properties["start"] = str(prov.start)
            properties["end"] = str(prov.end)
            geometry = prov.geometry
            finaldata.add_feature(properties=properties, geometry=geometry)
        finaldata.save(OUTFILE)

    # Test time animation
    final = pg.VectorData(OUTFILE, encoding="latin")
    print final.inspect()
    layout = pg.renderer.Layout(width=500, height=500, background=(111,111,111))
    for start in sorted(set(( f["start"] for f in final))):
        print start
        mapp = pg.renderer.Map(width=500, title=str(start), background=(111,111,111))
        mapp.add_layer( final.select(lambda f: f["start"] <= start < f["end"]) , # not sure if this filters correct
                        #text=lambda f:f["Name"],
                        fillcolor=pg.renderer.Color("random", opacity=155)
                        )
        mapp.zoom_auto()
        #mapp.view()
        layout.add_map(mapp)
    layout.view()


        
        

