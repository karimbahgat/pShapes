# -*- coding: utf8 -*-

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
from unidecode import unidecode




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
        names = [find.ids["Name"]] + find.ids["Alterns"]
        names += [unidecode(n) for n in names if n != unidecode(n)]
        for name in names:
            compnames = [comparison.ids["Name"]] + comparison.ids["Alterns"]
            compnames += [unidecode(n) for n in compnames if n != unidecode(n)]
            match = name in compnames
            if match:
                break
        if not match:
            match = find.ids["HASC"] and len(find.ids["HASC"]) > 3 and comparison.ids["HASC"] == find.ids["HASC"]
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
        if not geometry:
            raise Exception("ResultsTable province must have geometry")
        elif not shapely.geometry.shape(geometry).is_valid:
            try:
                geometry = shapely.geometry.shape(geometry).buffer(0).__geo_interface__
            except: 
                raise Exception("Invalid geometry: must be valid, and Polygon or MultiPolygon")
        elif "Polygon" not in shapely.geometry.shape(geometry).geom_type:
            raise Exception("Invalid geometry: must be Polygon or MultiPolygon")

        # TODO: dont set these, should be set with separate events
        #if start is None: start = self.mindate
        if end is None: end = self.maxdate
        
        prov = Province(country, start, end, ids, other, geometry)
        self.provs.append(prov)
   
    def find_prov(self, findprov, matchfunc=ids_equal, fuzzythresh=0.8):
        "Lookup id and return matching feature GeoJSON among existing registered provs"
        newprovs = sorted((prov for prov in self.provs if matchfunc(findprov, prov)), key=lambda f: f.end)
        if not newprovs:
            import difflib
            matches = sorted([(p,difflib.SequenceMatcher(None,findprov.ids["Name"],p.ids["Name"]).ratio()) for p in self.provs if p.country == findprov.country], key=lambda pair: pair[1])
            matches = ((p,r) for p,r in matches if r >= fuzzythresh)
            matches = sorted(matches, key=lambda(p,r): (p.end,-r))
            newprovs = [p for p,r in matches]
            
##        if len(newprovs) > 1:
##            end = newprovs[0].end
##            if len([p.end for p in newprovs if p.end == end]) > 1:
##                raise Exception("!!!! Found duplicate provinces with same ids existing simultaneously... %s" % [(p.country,p.ids) for p in newprovs])
            
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
                if toprov.ids["Name"] == "*":
                    continue
                print changes

                # Lookup the toprov geometry
                newprov = self.find_prov(toprov)
##                if not newprov:
##                    # maybe special case where split prov also receives a transfer
##                    # in which case transfers are coded with the old pre-split prov as the toprov, then split
##                    # but since pre-split has not yet been added (via union of breakaway geoms)
##                    # create that union now.
##                    # 1. find all toprovinfo for changes that split away from the presplit prov
##                    breakawaychanges = [p for p in event.changes if p.type == "Breakaway" and ids_equal(toprov,p.fromprov)]
##                    # 2. find their added provinces
##                    breakawayprovs = [self.find_prov(p.toprov) for p in breakawaychanges]
##                    # 3. union their geoms to recreate the presplit geom (only the geom matters)
##                    unioned = shapely.ops.cascaded_union([shapely.geometry.shape(b.geometry) for b in breakawayprovs])
##                    # 4. diff the transfers away
##                    transfers = shapely.ops.cascaded_union([shapely.geometry.shape(c.cutpoly) for c in changes if "Transfer" in c.type])
##                    diff = unioned.difference(transfers)
##                    newprov = Province("Pointless", 99, 99, {"Name":"Pointless"}, {}, diff.__geo_interface__)
##                    newprov.presplit = True
##                    print 333,newprov
##                    continue
                
                if not newprov:
                    # couldnt find provcode, need better lookup, maybe using multiple ids
                    avail = "\n".join((repr(p) for p in self.provs if p.country == toprovcountry))
                    raise Exception("Couldnt find province %s \nAvailable options: \n %s" % (toprov,avail) )
                
                if not newprov.geometry or newprov.geometry["type"] == "GeometryCollection":
                    # lookup prov has invalid geom
                    raise Exception("Lookup province %s has invalid geometry" % newprov)

                newprovgeom = shapely.geometry.shape(newprov.geometry)

                print "NEWGEOM", toprov, " = ", newprov, newprovgeom.area

                # Also change the startdate of the newer prov
                newprov.start = event.date
                print "changed date", newprov, newprov.start, newprov.end

                # testing                
##                if newprov.ids["Name"] == "Adamaoua":
##                    import pythongis as pg
##                    dat = pg.VectorData(type="Polygon")
##                    pg.vector.data.Feature(dat, [], newprovgeom.__geo_interface__).view(500,500)

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
                            mapp.add_layer(dat, fillcolor=pg.renderer.rgb("red"), legendoptions=dict(title="to "+newprov.ids["Name"]))

                            dat = pg.VectorData(type="Polygon")
                            dat.fields = ["Text"]
                            dat.add_feature(["cutpoly"], change.cutpoly.__geo_interface__)
                            mapp.add_layer(dat, fillcolor=pg.renderer.rgb("blue"), legendoptions=dict(title="from "+change.fromprov.ids["Name"]))
                            
                            mapp.add_legend(xy=("99%w","99%h"), anchor="se")

                            mapp.zoom_bbox(*mapp.layers.bbox)
                            #mapp.zoom_auto()
                            mapp.zoom_out(2)
                            print mapp.zooms
                            mapp.view()
                        
                            raise Exception("No intersection found, cutpoly must have at least some overlap with the province")
                        
                        elif not change.geom.is_valid or "Polygon" not in change.geom.geom_type:
                            print change.geom.geom_type
                            invalid = True
                            if change.geom.geom_type == "GeometryCollection":
                                # some linestrings likely crept in, we only care about the polys
                                for g in change.geom.geoms:
                                    if g.geom_type in ("Polygon","MultiPolygon"):
                                        change.geom = g
                                        invalid = False
                                        break

                            if invalid:
                                import pythongis as pg
                                mapp = pg.renderer.Map(500, 500, title="Error: Invalid intersection (%s)" % newprov.end)
                                
                                dat = pg.VectorData(type="Polygon")
                                dat.fields = ["Text"]
                                dat.add_feature(["orig geom"], shapely.geometry.shape(newprov.geometry).__geo_interface__)
                                mapp.add_layer(dat, fillcolor=pg.renderer.rgb("red"), legendoptions=dict(title="to "+newprov.ids["Name"]))

                                dat = pg.VectorData(type="Polygon")
                                dat.fields = ["Text"]
                                dat.add_feature(["cutpoly"], change.cutpoly.__geo_interface__)
                                mapp.add_layer(dat, fillcolor=pg.renderer.rgb("blue"), legendoptions=dict(title="from "+change.fromprov.ids["Name"]))
                                
                                mapp.add_legend(xy=("99%w","99%h"), anchor="se")

                                mapp.zoom_bbox(*mapp.layers.bbox)
                                #mapp.zoom_auto()
                                mapp.zoom_out(2)
                                print mapp.zooms
                                mapp.view()

                                raise Exception("Invalid intersection between %s and %s" % (newprov,change) )

                # If newinfo is the only change
                if len(changes) == 1 and changes[0].type == "NewInfo":
                    # The oldprov only changed info, so should have the same geom as the newprov
                    changes[0].geom = newprovgeom
                    allsubparts.append(changes[0])

                elif "Breakaway" in (ch.type for ch in changes):
                    pass

                else:
                    # part or full transfer
                    # Trim the breakoffs off the receiving toprov
                    # If anything left, means it already existed, so add own prov how it looked before
                    # Otherwise, this was its first creation
                    trimmedgeom = newprovgeom
                    if not trimmedgeom.is_empty:
                        print "trimmedgeom", trimmedgeom.area
                        newinfo = next((change for change in changes if change.type == "NewInfo"), None)
                        if newinfo:
                            prereceiving = Remainder(newinfo.fromprov, trimmedgeom)
                        else:
                            prereceiving = Remainder(toprov, trimmedgeom)
                        allsubparts.append(prereceiving)




            # 2) Group and union all geom parts by fromprov
            print "by fromprov"
            def groupsimilar(allsubparts):
                key = lambda ch: ch.fromprov.country
                for fromprovcountry,subparts in itertools.groupby(sorted(allsubparts, key=key), key=key):
                    subparts = list(subparts)
                    grp = []
                    while subparts:
                        frst = subparts.pop(0)
                        grp.append(frst)
                        for nxt in reversed(subparts):
                            if ids_equal(frst.fromprov,nxt.fromprov):
                                grp.append(nxt)
                                subparts.remove(nxt)
                        yield fromprovcountry, grp
                        grp = []
            for fromprovcountry,subparts in groupsimilar(allsubparts):
                subparts = list(subparts)
                fromprov = subparts[0].fromprov
                if fromprov.ids["Name"] == "*":
                    continue

                # Add what remains of giving province (if anything left/didn't dissolve)
                if "FullTransfer" not in (p.type for p in subparts) and "NewInfo" not in (p.type for p in subparts):
                    oldprov = self.find_prov(fromprov)
                    if oldprov and oldprov.start is None:
                        print "REMAAAAAAAAINS:",fromprov,oldprov
                        oldprov.start = event.date
                        oldprovgeom = shapely.geometry.shape(oldprov.geometry)
                        pregiving = Remainder(fromprov, oldprovgeom)
                        subparts.append(pregiving)
                    elif oldprov and oldprov.start:
                        print "NOT REMAINS:",oldprov
                
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
                try: fullgeom = fullgeom.buffer(0) 
                except: pass

                # Beautification! WARNING: SLOW! 
                fixed = fullgeom.buffer(0.0000001).buffer(-0.0000001) # fill in hole slivers
                fixed = fixed.buffer(-0.0000001).buffer(0.0000001) # strip away island slivers
                if fixed.is_valid and not fixed.is_empty:
                    fullgeom = fixed
                
                if fullgeom.is_empty:
                    raise Exception("Something went wrong, output province %s has empty geometry" % fromprov)
                elif not fullgeom.is_valid or "Polygon" not in fullgeom.geom_type:
                    print "!!!!!!!!!!!!!!!!!!!! skipping invalid leftover geom"
                    #global fullgeom
                    #fullgeom = fullgeom # so can check it after error
                    #raise Exception("Something went wrong, output province %s has invalid geometry" % fromprov)
                    continue

##                # temporary error check visualizing
##                if fromprov.ids["Name"] == "Benue-Plateau": #in ("Nord","Adamaoua"): #("Kwara","Benue"):
##                    import pythongis as pg
##                    dat = pg.VectorData(type="Polygon")
##                    
##                    for part in subparts:
##                        print "part", part, part.geom.is_valid, part.geom.is_empty, part.geom.geom_type
##                        if part.geom.geom_type == "GeometryCollection":
##                            print "not showing geomcollection", [g for g in part.geom.geoms]
##                        else:
##                            pg.vector.data.Feature(dat, [], part.geom.__geo_interface__).view(500,500)
##                    
##                    dat = pg.VectorData(type="Polygon")
##                    print "ADDING:", fromprov, "end=", event.date, fullgeom.is_valid, fullgeom.is_empty, fullgeom.geom_type
##                    pg.vector.data.Feature(dat, [], fullgeom.__geo_interface__).view(500,500)
##                    ###

                print "added", fromprov, fromprov.start, fromprov.end
                
                self.add_province(country=fromprov.country,
                                  start=None,
                                 end=event.date,
                                 ids=fromprov.ids,
                                 other={},
                                 geometry=fullgeom.__geo_interface__)

            # 4) Maybe change all remaining provs via *
            key = lambda ch: ch.toprov.country
            for toprovcountry,countrychanges in itertools.groupby(sorted(event.changes, key=key), key=key):
                countrychanges = list(countrychanges)
                rest = next((ch for ch in countrychanges if ch.toprov.ids["Name"] == "*"), None)
                if rest:
                    addprovs = []
                    for prov in self.provs:
                        # get all country provs valid at the current date that have not
                        # already been changed, ie only those with startdate yet to be set (None)
                        # TODO: ONLY WORKS FOR NEWINFO...?
                        if prov.country == toprovcountry and prov.start == None:
                            addprovs.append(prov)
                    for prov in addprovs:
                        # finalize the newer
                        prov.start = event.date
                        # add the older
                        self.add_province(country=rest.fromprov.country,
                                          start=None,
                                         end=event.date,
                                         ids=prov.ids,
                                         other={},
                                         geometry=prov.geometry)

        # finally set mindate for all (TODO: replace this with special firstdate events)
        for prov in self.provs:
            if prov.start is None:
                prov.start = self.mindate





if __name__ == "__main__":

    import pythongis as pg

    CURRENTFILE = r"C:\Users\kimo\Downloads\ne_10m_admin_1_states_provinces\ne_10m_admin_1_states_provinces.shp"
    CHANGESFILE = None #r"pshapes_raw_auto.csv"
    OUTFILE = r"processed.geojson"
    BUILD = 1

    if BUILD:

        # Initiate results table

        results = ResultsTable(mindate=datetime.date(year=1900, month=1, day=1),
                               maxdate=datetime.date(year=2015, month=12, day=31))


        # Load events table

        # Maybe auto download newest
        if not CHANGESFILE:
            import urllib
            CHANGESFILE = "pshapes_raw_auto.csv"
            with open(CHANGESFILE, "wb") as writer:
                print "downloading latest..."
                raw = urllib.urlopen("http://pshapes.herokuapp.com/download/raw/").read()
                writer.write(raw)

        import sys
        sys.path.append(r"C:\Users\kimo\Documents\GitHub\Tably")
        import tably

        eventstable = pg.VectorData(CHANGESFILE, encoding="utf8")
        eventstable = eventstable.select(lambda f: f["status"] != "NonActive")
        #eventstable = tably.load(CHANGESFILE, encoding="utf8") # CSV EXPORT FROM WEBSITE DATABASE
        #eventstable = eventstable.exclude('status == "NonActive"')
        #eventstable = eventstable.exclude('fromcountry in "Dahomey Ethiopia Eritrea Norway".split() or tocountry in "Ethiopia Eritrea Norway".split()')
        eventstable.compute("fromcountry", lambda f: f["fromcountry"].replace("-"," "))
        eventstable.compute("tocountry", lambda f: f["tocountry"].replace("-"," "))
        skip = ["Norway"] #,"Ivory Coast"] #,"Burkina Faso"] #,"Guinea"] #,"Sierra Leone","Sierra Leone Protectorate","Sierra Leone Colony"]
        eventstable = eventstable.select(lambda f: f["fromcountry"] not in skip and f["tocountry"] not in skip)
        
        # temp nigeria hack
        eventstable.add_feature([u'http://www.statoids.com/ung.html', u'Pending', u'1976-02-03', u'NewInfo', u'Nigeria', u'Kwara', None, None, None, None, None, None, None, u'Nigeria', u'Kwara', None, None, None, None, None, None, None, None, None, None],
                                None)

        # temp ivory coast hack
        eventstable = eventstable.select(lambda f: f["date"] != "2011-09-28")

        for date,changetable in eventstable.manage.split("date"):
            event = Event()

            # parse date correctly
            date = dateutil.parser.parse(date)
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
                                         "Alterns":row["fromalterns"].split("|") if row["fromalterns"] else [],
                                        "HASC":row["FromHASC".lower()],
                                        "ISO":row["FromISO".lower()],
                                        "FIPS":row["FromFIPS".lower()]},
                                    other={},
                                    geometry=None)
                                    
                toprov = Province(country=row["tocountry"],
                                    start=None,
                                    end=None,
                                    ids={"Name":row["ToName".lower()],
                                         "Alterns":row["toalterns"].split("|") if row["toalterns"] else [],
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



        # Load contemporary table

        countries = set()
        for f in eventstable:
            countries.add(f["fromcountry"])
            countries.add(f["tocountry"])

        curtable = pg.VectorData(CURRENTFILE, encoding="utf8", encoding_errors="replace",
                                select=lambda f: f["geonunit"] in countries)

        # modify guinea wrong level
        guinea = curtable.select(lambda f: f["geonunit"]=="Guinea")
        curtable = curtable.select(lambda f: f["geonunit"]!="Guinea")
        for f in guinea:
            if f["code_hasc"] in "GN.BF GN.BK GN.FR GN.GA GN.KN":
                f.row = [None for _ in range(len(curtable.fields))]
                f["geonunit"] = "Guinea"
                f["name"] = "Boke"
                f["name_alt"] = "Boké".decode('utf8')
                f["iso_3166_2"] = "B"
            elif f["code_hasc"] in "GN.CO GN.DU GN.FO GN.KD GN.TE":
                f.row = [None for _ in range(len(curtable.fields))]
                f["geonunit"] = "Guinea"
                f["name"] = "Kindia"
                f["iso_3166_2"] = "D"
            elif f["code_hasc"] in "GN.DB GN.DI GN.FA GN.KS":
                f.row = [None for _ in range(len(curtable.fields))]
                f["geonunit"] = "Guinea"
                f["name"] = "Faranah"
                f["iso_3166_2"] = "F"
            elif f["code_hasc"] in "GN.KA GN.KE GN.KO GN.MD GN.SI":
                f.row = [None for _ in range(len(curtable.fields))]
                f["geonunit"] = "Guinea"
                f["name"] = "Kankan"
                f["iso_3166_2"] = "K"
            elif f["code_hasc"] in "GN.KB GN.LA GN.LE GN.ML GN.TO":
                f.row = [None for _ in range(len(curtable.fields))]
                f["geonunit"] = "Guinea"
                f["name"] = "Labe"
                f["name_alt"] = "Labé".decode('utf8')
                f["iso_3166_2"] = "L"
            elif f["code_hasc"] in "GN.DL GN.MM GN.PI":
                f.row = [None for _ in range(len(curtable.fields))]
                f["geonunit"] = "Guinea"
                f["name"] = "Mamou"
                f["iso_3166_2"] = "M"
            elif f["code_hasc"] in "GN.BE GN.GU GN.LO GN.MC GN.NZ GN.YO":
                f.row = [None for _ in range(len(curtable.fields))]
                f["geonunit"] = "Guinea"
                f["name"] = "Nzerekore"
                f["name_alt"] = "Nzérékoré".decode('utf8')
                f["iso_3166_2"] = "N"
            elif f["code_hasc"] == "GN.CK":
                f.row = [None for _ in range(len(curtable.fields))]
                f["geonunit"] = "Guinea"
                f["name"] = "Conakry"
                f["iso_3166_2"] = "C"
            else:
                print f.row
                fsfsdfsdf

        guinea = guinea.aggregate("iso_3166_2",
                                  fieldmapping=[(name,name,"first") for name in curtable.fields],
                                  geomfunc="union")
        #guinea.view(fillcolor=dict(breaks="unique"), text=lambda f: f["name"])
        for f in guinea:
            f = curtable.add_feature(f.row, f.geometry)

        # modify burkina faso wrong level
        burkina = curtable.select(lambda f: f["geonunit"]=="Burkina Faso")
        curtable = curtable.select(lambda f: f["geonunit"]!="Burkina Faso")
        burkina = burkina.aggregate("region",
                                  fieldmapping=[(name,name,"first") for name in curtable.fields],
                                  geomfunc="union")
        burkina.compute("name", lambda f: f["region"])
        burkina.compute("iso_3166_2", lambda f: f["region_cod"])
        for f in burkina:
            f.row = [f[fl] if fl in "geonunit iso_3166_2 name name_alt".split() else None for fl in curtable.fields]
        #burkina.view(fillcolor=dict(breaks="unique"), text=lambda f: f["name"])
        for f in burkina:
            f = curtable.add_feature(f.row, f.geometry)

        # modify ivory coast wrong level
        # needs full set of new provs, natearth is outdated
        # ...

        # add it
        for feat in curtable:
            #if feat["geonunit"] not in ("Benin", "Senegal", "Cameroon","Southern Cameroons","Northern Cameroons","Nigeria","Ivory Coast"): continue
            # correct errors
            if feat["name"] == "Federal Capital Territory":
                feat["name"] = "Abuja Capital Territory"
            elif feat["adm1_code"] == "SEN-5514":
                feat["code_hasc"] = "SN.SD"
            elif feat["adm1_code"] == "SEN-5515":
                feat["code_hasc"] = "SN.KG"
            elif feat["adm1_code"] == "BEN-2180":
                feat["code_hasc"] = "BJ.MO"
            elif feat["adm1_code"] == "SEN-767":
                feat["code_hasc"] = "SN.MT"
            # add
            results.add_province(country=feat["geonunit"],
                                 start=None,
                                 end=None,
                                 ids={"Name": feat["name"],
                                      "Alterns": feat["name_alt"].strip().split("|"),
                                      "HASC": feat["code_hasc"],
                                      "ISO": feat["iso_3166_2"],
                                      "FIPS": feat["fips"]
                                      },
                                 other={},
                                 geometry=feat.geometry)



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
    #print final.inspect()

    lyr = pg.renderer.VectorLayer( final,
                                    text=lambda f: f["Name"], #.encode("latin").decode("utf8"), #"{prov} ({start}-{end})".format(prov=f["Name"].encode("utf8"),start=f["start"][:4],end=f["end"][:4]),
                                    textoptions=dict(textsize=4), #, bbox=lambda f:f.bbox),
                                    fillcolor=(155,155,155,155) #pg.renderer.rgb("random", opacity=155),
                                    #fillcolor=dict(breaks="unique", key=lambda f:f["country"]),
                                    )
    
    #layout = pg.renderer.Layout(width=500, height=500, background=(111,111,111))
    for start in sorted(set(( f["start"] for f in final)), reverse=True):
        print start
        mapp = pg.renderer.Map(width=1500, title=str(start)) #, background=(111,111,111))
        lyr.datafilter = lambda f: f["start"] <= start < f["end"]
        mapp.add_layer(lyr)
        mapp.zoom_bbox(*final.bbox) #zoom_bbox(-180,90,180,-90)
        #mapp.zoom_auto()
        #mapp.view()
        mapp.save("C:/Users/kimo/Downloads/pshapes_visualized_transp/%s.png"%str(start))
        #layout.add_map(mapp)
    #layout.view()

    # THINGS TO CHECK IF BUILD ERROR

    # Make sure province name spelling is consistent with its next iteration,
    # since in some cases the name can change back again at a much later date,
    # and that way an old province can find a match with a much later version
    # of the same province just due to back-and-forth spelling variation. 

    # A province cant be involved in a transfer and split event at same time.
    # Some sources might use confusing language on this, saying first split, then transfers... 
    # Split is only if no other changes occured to the new province.
    # If another change occured, then the split becomes a full or parttransfer,
    # followed by one or more full or parttransfers for the other changes.
    # I.e. if a breakaway province also received a small area from another province
    # then it is registered with two transfers instead of a breakaway and a transfer. 


        
        

