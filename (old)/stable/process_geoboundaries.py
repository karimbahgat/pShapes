# -*- coding: utf8 -*-

"""
Pshapes-GeoBoundaries.
Reconstructing boundaries using GeoQuery's GeoBoundaries as the starting point. 
"""

##############


import itertools
import datetime
import warnings
import dateutil, dateutil.parser
import pygeoj
import shapely, shapely.ops, shapely.geometry
from unidecode import unidecode


from process import *
import pythongis as pg

CURRENTFILE = r"curfile_geoboundaries.shp"
COUNTRYFIELD = 'country'
SUBNAMEFIELD = 'name'
SUBISOFIELD = 'iso_code'

CHANGESFILE = None #r"pshapes_raw_auto.csv"

OUTFILE = r"processed.geojson"
BUILD = 1

if BUILD:

    # Initiate results table

    results = ResultsTable()



    ################################
    # Load events table

    # Maybe auto download newest
    if not CHANGESFILE:
        import urllib
        CHANGESFILE = "pshapes_raw_auto.csv"
        with open(CHANGESFILE, "wb") as writer:
            print "downloading latest..."
            raw = urllib.urlopen("http://pshapes.org/download/raw/").read()
            writer.write(raw)

    eventstable = pg.VectorData(CHANGESFILE, encoding="utf8", sniffsize=20)
    eventstable = eventstable.select(lambda f: f["status"] != "NonActive")
    eventstable.compute("fromcountry", lambda f: f["fromcountry"]) #??
    eventstable.compute("tocountry", lambda f: f["tocountry"]) #??
    skip = [] 
    eventstable = eventstable.select(lambda f: f["fromcountry"] not in skip and f["tocountry"] not in skip)

    # testing individual country
    #eventstable = eventstable.select(lambda f: 'Sierra Leone' in f["fromcountry"])

    # temp country hacks to exclude changes that are newer than the NatEarth reference dataset
    #eventstable = eventstable.select(lambda f: not (f['fromcountry']=='Ivory Coast' and f["date"] == "2011-09-28"))
    eventstable = eventstable.select(lambda f: not (f['fromcountry']=='Equatorial Guinea' and f["date"] == "2015-08-03"))

    # temp hack for problem ones
    eventstable = eventstable.select(lambda f: not (f['tocountry']=='Australia' and f["toname"] in ["Coral Sea Islands Territory","Ashmore and Cartier Islands"]))

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
            
            if row["Type".lower()] == "MergeNew":
                if not row["transfer_geom"]: #or not row["FromHASC"]:
                    continue
                change = MergeNewChange(fromprov,
                                            toprov,
                                            row["transfer_geom"])
            elif row["Type".lower()] in "MergeExisting FullTransfer":
                if not row["transfer_geom"]: #or not row["FromHASC"]:
                    continue
                change = MergeExistingChange(fromprov,
                                            toprov,
                                            row["transfer_geom"])
            elif row["Type".lower()] == "TransferNew":
                if not row["transfer_geom"]: #or not row["FromHASC"]:
                    continue
                change = TransferNewChange(fromprov,
                                            toprov,
                                            row["transfer_geom"])
            elif row["Type".lower()] in "TransferExisting PartTransfer":
                if not row["transfer_geom"]: #or not row["FromHASC"]:
                    continue
                change = TransferExistingChange(fromprov,
                                            toprov,
                                            row["transfer_geom"])
            elif row["Type".lower()] == "Breakaway":
                change = BreakawayChange(fromprov,
                                         toprov)
            elif row["Type".lower()] == "SplitPart":
                change = SplitPartChange(fromprov,
                                         toprov)
            elif row["Type".lower()] == "NewInfo":
                change = NewInfoChange(fromprov,
                                     toprov)
            elif row["Type".lower()] == "Begin":
                change = BeginChange(fromprov,
                                     toprov)
            else:
                continue
            print row["Type".lower()]
            event.changes.append(change)
        results.add_event(event)




    ##############################
    # Load contemporary table

    # Get relevant countries from the change data
    countries = set()
    for f in eventstable:
        countries.add(f["fromcountry"])
        countries.add(f["tocountry"])

    # Maybe auto download newest
    if not CURRENTFILE:
        import urllib
        import json
        from zipfile import ZipFile
        from StringIO import StringIO
        CURRENTFILE = "curfile_geoboundaries.shp"
        print "downloading and building current province data"
        
        def countryfiles():
            import pycountries as pc
            eventisos = []
            for name in countries:
                try:
                    iso = pc.Country(name=name).iso3
                    eventisos.append(iso)
                except:
                    print 'no iso for ' + name
            print eventisos
            for c in pc.all_countries():
                iso = c.iso3
                print iso
                name = c.name
                if not iso in eventisos:
                    continue
                url = 'http://www.geoboundaries.org/data/GeoBoundaries1.3.0/geojson/{iso}/{iso}_ADM1.zip'.format(iso=iso)
                try:
                    zipobj = ZipFile(StringIO(urllib.urlopen(url).read()))
                except:
                    print 'not found'
                    continue
                jdict = json.loads(zipobj.read('{iso}_ADM1.geojson'.format(iso=iso)))
                fields = [COUNTRYFIELD,SUBNAMEFIELD,SUBISOFIELD]
                vecfile = pg.VectorData(fields=fields)
                for f in jdict['features']:
                    rowdict = dict([(k.lower(),f['properties'][k]) for k in f['properties'].keys() if k.lower() in fields])
                    rowdict['country'] = name
                    print rowdict
                    vecfile.add_feature(rowdict, f['geometry'])
                print vecfile
                yield vecfile

        merged = pg.vector.manager.merge(*countryfiles())
        merged.save(CURRENTFILE, encoding="utf8")
        print 'current data built!'

    curtable = pg.VectorData(CURRENTFILE, encoding="utf8", encoding_errors="replace")
    print 'current data loaded'
    
    curtable.compute(COUNTRYFIELD, lambda f: 'United States' if f[COUNTRYFIELD]=='United States of America' else f[COUNTRYFIELD])
    curtable.compute(COUNTRYFIELD, lambda f: 'Republic of the Congo' if f[COUNTRYFIELD]=='Republic of Congo' else f[COUNTRYFIELD])
    curtable.compute(COUNTRYFIELD, lambda f: 'Guinea-Bissau' if f[COUNTRYFIELD]=='Guinea Bissau' else f[COUNTRYFIELD])
    curtable.compute(COUNTRYFIELD, lambda f: 'The Gambia' if f[COUNTRYFIELD]=='Gambia' else f[COUNTRYFIELD])
    
    curtable = curtable.select(lambda f: f[COUNTRYFIELD] in countries)


    

    # add it
    print 'adding current to results'
    for feat in curtable:
        # add
        results.add_province(country=feat[COUNTRYFIELD],
                             start=None,
                             end=None,
                             ids={"Name": feat[SUBNAMEFIELD],
                                  "Alterns": [], #feat["name_alt"].strip().split("|"),
                                  "HASC": None, #feat["code_hasc"],
                                  "ISO": feat[SUBISOFIELD].split('-')[-1],
                                  "FIPS": None, #feat["fips"]s
                                  },
                             other={},
                             geometry=feat.geometry)



    # Process and create final provs
##    from unidecode import unidecode
##    def ids_equal(find, comparison):
##        # find is just the dict, comparison is the prov obj
##        def validid(val):
##            if val:
##                if isinstance(val, str): return len(val) > 3
##                else: return True
##        match = False
##        
##        if find.country == comparison.country:
##            #match = any((validid(otherid) and otherid in find.ids.values()
##            #             for otherid in comparison.ids.values() ))
##            names = [find.ids["Name"]] + find.ids["Alterns"]
##            names += [unidecode(n) for n in names if n != unidecode(n)]
##            for name in names:
##                compnames = [comparison.ids["Name"]] + comparison.ids["Alterns"]
##                compnames += [unidecode(n) for n in compnames if n != unidecode(n)]
##                match = name in compnames
##                if match:
##                    break
##            if not match:
##                match = find.ids["ISO"] and comparison.ids["ISO"] == find.ids["ISO"]
##        else:
##            # country not matched
##            pass
##        return match
##    
##    import process
##    process.ids_equal = ids_equal

    print 'beginning backtracking'
    results.begin_backtracking()


    # Save final geojson table
    import pygeoj
    finaldata = pygeoj.GeojsonFile()
    for prov in results.provs:
        properties = {}
        properties["country"] = prov.country
        properties.update(dict([(k.lower(),v) for k,v in prov.ids.items()]))
        properties.update(dict([(k.lower(),v) for k,v in prov.other.items()]))
        properties["start"] = str(prov.start)
        properties["end"] = str(prov.end)
        geometry = prov.geometry
        finaldata.add_feature(properties=properties, geometry=geometry)
    finaldata.save(OUTFILE)

##    # Test time animation    
##    
##    final = pg.VectorData(OUTFILE, encoding="latin")
##    #print final.inspect()
##
##    lyr = pg.renderer.VectorLayer( final,
##                                    text=lambda f: f["name"], #.encode("latin").decode("utf8"), #"{prov} ({start}-{end})".format(prov=f["Name"].encode("utf8"),start=f["start"][:4],end=f["end"][:4]),
##                                    textoptions=dict(textsize=4), #, bbox=lambda f:f.bbox),
##                                    fillcolor=(155,155,155,155) #pg.renderer.rgb("random", opacity=155),
##                                    #fillcolor=dict(breaks="unique", key=lambda f:f["country"]),
##                                    )
##    
##    #layout = pg.renderer.Layout(width=500, height=500, background=(111,111,111))
##    for start in sorted(set(( f["start"] for f in final)), reverse=True):
##        print start
##        mapp = pg.renderer.Map(width=1500, title=str(start)) #, background=(111,111,111))
##        lyr.datafilter = lambda f: f["start"] <= start < f["end"]
##        mapp.add_layer(lyr)
##        mapp.zoom_bbox(*final.bbox) #zoom_bbox(-180,90,180,-90)
##        #mapp.zoom_auto()
##        #mapp.view()
##        mapp.save("Visualized/%s.png"%str(start))
##        #layout.add_map(mapp)
##    #layout.view()

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


        
        

