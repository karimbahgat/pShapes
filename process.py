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
import warnings
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

    def __repr__(self):
        return "FullTransfer {fromm} --> {to}".format(fromm=self.fromprov, to=self.toprov)

class PartTransferChange:
    def __init__(self, fromprov, toprov, cutpoly):
        self.type = "PartTransfer"
        self.fromprov = fromprov
        self.toprov = toprov
        self.cutpoly = shapely.geometry.shape(eval(cutpoly))

    def __repr__(self):
        return "PartTransfer {fromm} --> {to}".format(fromm=self.fromprov, to=self.toprov)

class BreakawayChange:
    def __init__(self, fromprov, toprov):
        self.type = "Breakaway"
        self.fromprov = fromprov
        self.toprov = toprov

    def __repr__(self):
        return "Breakaway {fromm} --> {to}".format(fromm=self.fromprov, to=self.toprov)

class NewInfoChange:
    def __init__(self, fromprov, toprov):
        self.type = "NewInfo"
        self.fromprov = fromprov
        self.toprov = toprov

    def __repr__(self):
        return "NewInfo {fromm} --> {to}".format(fromm=self.fromprov, to=self.toprov)

class Remainder:
    def __init__(self, fromprov, geom):
        self.type = "Remainder"
        self.fromprov = fromprov
        self.geom = geom

    def __repr__(self):
        return "Remainder %s" % self.fromprov
        


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
    match = False
    
    if find.country == comparison.country:
        #match = any((validid(otherid) and otherid in find.ids.values()
        #             for otherid in comparison.ids.values() ))
        match = find.ids["Name"] == comparison.ids["Name"] or find.ids["Name"] in comparison.ids["Alterns"] or (find.ids["HASC"] and len(find.ids["HASC"]) > 3 and comparison.ids["HASC"] == find.ids["HASC"])
    else:
        # country not matched
        pass
    return match

class Province:
    def __init__(self, country, start, end, ids, other, geometry):
        self.country = country
        self.start = start
        self.end = end
        self.ids = ids
        self.other = other
        self.geometry = geometry

    def __repr__(self):
        name = self.ids["Name"].encode("utf8")
        country = self.country.encode("utf8")
        if self.end:
            return "Province: {name}, {country} (until {end})".format(name=name, country=country, end=self.end)
        else:
            return "Province: {name}, {country}".format(name=name, country=country)

class ResultsTable:
    def __init__(self, mindate, maxdate):
        self.provs = []
        self.events = []
        self.mindate = mindate
        self.maxdate = maxdate

    def add_province(self, country, start, end, ids, other, geometry):
        if start is None: start = self.mindate
        if end is None: end = self.maxdate
        prov = Province(country, start, end, ids, other, geometry)
        self.provs.append(prov)
   
    def find_prov(self, findprov, matchfunc=ids_equal):
        "Lookup id and return matching feature GeoJSON among existing registered provs"
        newprovs = sorted((prov for prov in self.provs if matchfunc(findprov, prov)), key=lambda f: f.end)
        if len(newprovs) > 1:
            end = newprovs[0].end
            if len([p.end for p in newprovs if p.end == end]) > 1:
                raise Exception("!!!! Found duplicate provinces with same ids existing simultaneously... %s" % [(p.country,p.ids) for p in newprovs])
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
            allsubparts = []
            key = lambda ch: (ch.toprov.ids["Name"],ch.toprov.country)
            for (toprovname,toprovcountry),changes in itertools.groupby(sorted(event.changes, key=key), key=key):
                changes = list(changes)
                toprov = changes[0].toprov
                print changes

                # Lookup the toprov geometry
                newprov = self.find_prov(toprov)
                if not newprov:
                    # couldnt find provcode, need better lookup, maybe using multiple ids
                    raise Exception("Couldnt find province")
                
                if not newprov.geometry or newprov.geometry["type"] == "GeometryCollection":
                    # lookup prov has invalid geom
                    raise Exception("Lookup province has invalid geometry")

                newprovgeom = shapely.geometry.shape(newprov.geometry)

                print "NEWGEOM", toprov, " = ", newprov, newprovgeom.area

##                if toprov.ids["Name"] == "Nord":
##                    import pythongis as pg
##                    dat = pg.VectorData(type="Polygon")
##                    pg.vector.data.Feature(dat, [], newprovgeom.__geo_interface__).view(500,500)

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
                        allsubparts.append(change)

                    elif change.type == "PartTransfer":
                        # Get the geom that was transferred as the intersection with the change cutpoly
                        change.geom = newprovgeom.intersection(change.cutpoly)
                        newprovgeom = newprovgeom.difference(change.cutpoly) # trim the geom for each time so no overlap
                        allsubparts.append(change)

                    elif change.type == "Breakaway":
                        # The newprov is a breakaway, so the whole thing used to be part of an older prov
                        # ...and so should just be unioned as it is
                        change.geom = newprovgeom
                        allsubparts.append(change)

                    # Error checking
                    if change.type != "NewInfo":
                        
                        if change.geom.is_empty:
                            import pythongis as pg
                            mapp = pg.renderer.Map(500, 500, title="Error: No intersection found (%s)" % newprov.end)
                            
                            dat = pg.VectorData(type="Polygon")
                            dat.fields = ["Text"]
                            dat.add_feature(["orig geom"], shapely.geometry.shape(newprov.geometry).__geo_interface__)
                            mapp.add_layer(dat, fillcolor=pg.renderer.Color("red"), legendoptions=dict(title="to "+newprov.ids["Name"]))

                            dat = pg.VectorData(type="Polygon")
                            dat.fields = ["Text"]
                            dat.add_feature(["cutpoly"], change.cutpoly.__geo_interface__)
                            mapp.add_layer(dat, fillcolor=pg.renderer.Color("blue"), legendoptions=dict(title="from "+change.fromprov.ids["Name"]))
                            
                            mapp.add_legend(xy=("99%w","99%h"), anchor="se")

                            mapp.zoom_bbox(*mapp.layers.bbox)
                            #mapp.zoom_auto()
                            mapp.zoom_out(2)
                            print mapp.zooms
                            mapp.view()
                        
                            raise Exception("No intersection found, cutpoly must have at least some overlap with the province")
                        
                        elif not change.geom.is_valid or change.geom.geom_type == "GeometryCollection":
                            raise Exception("Invalid intersection between %s and %s" % (newprov,change) )
                    
                # Trim the breakoffs off the receiving toprov so it can later be added as its own prov, by taking the difference from the unioned breakoffs
                # FIGURE THIS OUT BETTER, WHEN IS NEEDED AND WHEN NOT??
                breakoffs = [ch for ch in changes if ch.type != "NewInfo"]
                print "breakoffs", breakoffs
                if breakoffs:
                    if len(breakoffs) > 1:
                        allbreakoffs = shapely.ops.cascaded_union([part.geom for part in breakoffs])
                    elif len(breakoffs) == 1:
                        allbreakoffs = breakoffs[0].geom
                    trimmedgeom = newprovgeom #.difference(allbreakoffs)
                    print newprovgeom.area, allbreakoffs.area, newprov.ids
                    if trimmedgeom:
                        print "trimmedgeom", newprovgeom.area, allbreakoffs.area, breakoffs
                        newinfo = next((change for change in changes if change.type == "NewInfo"), None)
                        if newinfo:
                            prereceiving = Remainder(newinfo.fromprov, trimmedgeom)
                        else:
                            prereceiving = Remainder(toprov, trimmedgeom)
                        prereceiving = Remainder(toprov, trimmedgeom)
                        allsubparts.append(prereceiving)

                # If newinfo is the only change
                if len(changes) == 1 and changes[0].type == "NewInfo":
                    # The oldprov only changed info, so should have the same geom as the newprov
                    changes[0].geom = newprovgeom
                    allsubparts.append(changes[0])




            # 2) Group and union all geom parts by fromprov
            print "by fromprov"
            key = lambda ch: (ch.fromprov.ids["Name"],ch.fromprov.country)
            for (fromprovname,fromprovcountry),subparts in itertools.groupby(sorted(allsubparts, key=key), key=key):
                subparts = list(subparts)
                fromprov = subparts[0].fromprov

                # Add orig
                if "PartTransfer" in (p.type for p in subparts) and "NewInfo" not in (p.type for p in subparts):
                    # hmmm... 
                    oldprov = self.find_prov(fromprov)
                    oldprovgeom = shapely.geometry.shape(oldprov.geometry)
                    pregiving = Remainder(fromprov, oldprovgeom)
                    subparts.append(pregiving)
                
                # Union all parts belonging to same fromprov, ie breakaways and parttransfers
                if len(subparts) > 1:
                    print fromprov, "union", [(p,p.geom.geom_type,"Empty" if p.geom.is_empty else "OK") for p in subparts]
                    fullgeom = shapely.ops.cascaded_union([part.geom for part in subparts])
                   
                else:
                    # Only one item, so prob means there was nothing left of the giving prov, ie fulltransfers or maybe also just newinfo
                    print fromprov, "single", subparts
                    fullgeom = subparts[0].geom
                    


                                
                # 3) Add to final data
                #print fullgeom, subparts[0].type
                
                # Error checking
                if fullgeom.is_empty:
                    raise Exception("Something went wrong, output province has empty geometry")
                elif not fullgeom.is_valid or fullgeom.geom_type == "GeometryCollection":
                    raise Exception("Something went wrong, output province has invalid geometry")

                # temporary error check visualizing
                if fromprov.ids["Name"] in ("Kwara","Benue"):
                    import pythongis as pg
                    dat = pg.VectorData(type="Polygon")
                    
##                    for part in subparts:
##                        print "part", part, part.geom.is_valid, part.geom.is_empty, part.geom.geom_type
##                        if part.geom.geom_type == "GeometryCollection":
##                            print "not showing geomcollection", [g for g in part.geom.geoms]
##                        else:
##                            pg.vector.data.Feature(dat, [], part.geom.__geo_interface__).view(500,500)
                    
                    dat = pg.VectorData(type="Polygon")
                    print "ADDING:", fromprov, event.date, fullgeom.is_valid, fullgeom.is_empty, fullgeom.geom_type
                    pg.vector.data.Feature(dat, [], fullgeom.__geo_interface__).view(500,500)
                
                self.add_province(country=fromprov.country,
                                  start=None,
                                 end=event.date,
                                 ids=fromprov.ids,
                                 other={},
                                 geometry=fullgeom.__geo_interface__)






if __name__ == "__main__":

    import pythongis as pg

    CURRENTFILE = r"ne_10m_admin_1_states_provinces.shp"
    CHANGESFILE = r"pshapes_raw.csv"
    OUTFILE = r"C:\Users\kimo\Downloads\processed.geojson"
    BUILD = 1

    if BUILD:

        # Initiate results table

        results = ResultsTable(mindate=datetime.date(year=1900, month=1, day=1),
                               maxdate=datetime.date(year=2015, month=12, day=31))


        # Load contemporary table
        
        for feat in pg.VectorData(CURRENTFILE, encoding="latin1"):   
            if feat["geonunit"] not in ("Cameroon","Southern Cameroons","Northern Cameroons","Nigeria"): continue
            # correct errors
            if feat["name"] == "Federal Capital Territory":
                feat["name"] = "Abuja Capital Territory"
            # add
            results.add_province(country=feat["geonunit"],
                                 start=None,
                                 end=None,
                                 ids={"Name": feat["name"],
                                      "Alterns": feat["name_alt"].split("|"),
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
        eventstable = eventstable.exclude('fromcountry in "Ethiopia Eritrea Norway".split() or tocountry in "Ethiopia Eritrea Norway".split()')
        
        # temp hack
        #eventstable.add_row([u'http://www.statoids.com/ung.html', u'Pending', u'1976-02-03', u'NewInfo', u'Nigeria', u'Kwara', None, None, None, None, None, None, None, u'Nigeria', u'Kwara', None, None, None, None, None, None, None, None, None, None])

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
                fromprov = Province(country=row["fromcountry"],
                                    start=None,
                                    end=None,
                                    ids={"Name":row["FromName".lower()],
                                         "Alterns": [], #row["fromalterns"].split("|"),
                                        "HASC":row["FromHASC".lower()],
                                        "ISO":row["FromISO".lower()],
                                        "FIPS":row["FromFIPS".lower()]},
                                    other={},
                                    geometry=None)
                                    
                toprov = Province(country=row["tocountry"],
                                    start=None,
                                    end=None,
                                    ids={"Name":row["ToName".lower()],
                                         "Alterns": [], #row["toalterns"].split("|"),
                                         "HASC":row["ToHASC".lower()],
                                         "ISO":row["ToISO".lower()],
                                         "FIPS":row["ToFIPS".lower()]},
                                    other={},
                                    geometry=None)
                
                if row["Type".lower()] == "FullTransfer":
                    if not row["transfer_geom"]: #or not row["FromHASC"]:
                        continue
                    change = FullTransferChange(fromprov,
                                                toprov,
                                                row["transfer_geom"])
                elif row["Type".lower()] == "PartTransfer":
                    if not row["transfer_geom"]: #or not row["FromHASC"]:
                        continue
                    change = PartTransferChange(fromprov,
                                                toprov,
                                                row["transfer_geom"])
                elif row["Type".lower()] == "Breakaway":
                    change = BreakawayChange(fromprov,
                                             toprov)
                elif row["Type".lower()] == "NewInfo":
                    change = NewInfoChange(fromprov,
                                         toprov)
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
            properties["country"] = prov.country
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
    for start in sorted(set(( f["start"] for f in final)), reverse=True):
        print start
        mapp = pg.renderer.Map(width=700, title=str(start), background=(111,111,111))
        mapp.add_layer( final.select(lambda f: f["start"] <= start < f["end"]) , # not sure if this filters correct
                        text=lambda f:f["Name"],
                        textoptions=dict(textsize=4),
                        #fillcolor=pg.renderer.Color("random", opacity=155),
                        fillcolor=dict(breaks="unique", key=lambda f:f["country"]),
                        )
        mapp.zoom_auto() #zoom_bbox(-180,90,180,-90) 
        mapp.view()
        layout.add_map(mapp)
    layout.view()


        
        

