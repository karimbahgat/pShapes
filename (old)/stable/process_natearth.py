# -*- coding: utf8 -*-

"""
Pshapes-Natural Earth.
Reconstructing boundaries using Natural Earth as the starting point. 
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

CURRENTFILE = r"C:\Users\kimok\OneDrive\Documents\GitHub\PythonGis\tests\data\ne_10m_admin_1_states_provinces.shp"
CHANGESFILE = None #r"pshapes_raw_auto.csv"
OUTFILE = r"processed.geojson"
BUILD = 1

if BUILD:

    # Initiate results table

    results = ResultsTable()


    # Load events table

    # Maybe auto download newest
    if not CHANGESFILE:
        import urllib
        CHANGESFILE = "pshapes_raw_auto.csv"
        with open(CHANGESFILE, "wb") as writer:
            print "downloading latest..."
            raw = urllib.urlopen("http://pshapes.org/download/raw/").read()
            writer.write(raw)

    #import sys
    #sys.path.append(r"C:\Users\kimo\Documents\GitHub\Tably")
    #import tably

##        import csv
##        for row in csv.reader(open(CHANGESFILE,'rU')):
##            print len(row)

    eventstable = pg.VectorData(CHANGESFILE, encoding="utf8", sniffsize=20)
    eventstable = eventstable.select(lambda f: f["status"] != "NonActive")
    #eventstable = tably.load(CHANGESFILE, encoding="utf8") # CSV EXPORT FROM WEBSITE DATABASE
    #eventstable = eventstable.exclude('status == "NonActive"')
    #eventstable = eventstable.exclude('fromcountry in "Dahomey Ethiopia Eritrea Norway".split() or tocountry in "Ethiopia Eritrea Norway".split()')
    eventstable.compute("fromcountry", lambda f: f["fromcountry"])
    eventstable.compute("tocountry", lambda f: f["tocountry"])
    skip = [] #,"Ivory Coast"] #,"Burkina Faso"] #,"Guinea"] #,"Sierra Leone","Sierra Leone Protectorate","Sierra Leone Colony"]
    eventstable = eventstable.select(lambda f: f["fromcountry"] not in skip and f["tocountry"] not in skip)

    # testing individual country
    #eventstable = eventstable.select(lambda f: 'Sierra Leone' in f["fromcountry"])

    # temp country hacks to exclude changes that are newer than the NatEarth reference dataset
    eventstable = eventstable.select(lambda f: not (f['fromcountry']=='Ivory Coast' and f["date"] == "2011-09-28"))
    eventstable = eventstable.select(lambda f: not (f['fromcountry']=='Equatorial Guinea' and f["date"] == "2015-08-03"))
    #eventstable = eventstable.select(lambda f: not (f['fromcountry']=='Egypt' and f["date"] == "2008-04-17"))

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



    # Load contemporary table

    countries = set()
    for f in eventstable:
        countries.add(f["fromcountry"])
        countries.add(f["tocountry"])

    curtable = pg.VectorData(CURRENTFILE, encoding="utf8", encoding_errors="replace")

    curtable.compute('geonunit', lambda f: f['admin'] if not f['geonunit'].strip() else f['geonunit'])
    
    curtable.compute('geonunit', lambda f: 'United States' if f['geonunit']=='United States of America' else f['geonunit'])
    curtable.compute('geonunit', lambda f: 'Republic of the Congo' if f['geonunit']=='Republic of Congo' else f['geonunit'])
    curtable.compute('geonunit', lambda f: 'Guinea-Bissau' if f['geonunit']=='Guinea Bissau' else f['geonunit'])
    curtable.compute('geonunit', lambda f: 'The Gambia' if f['geonunit']=='Gambia' else f['geonunit'])
    
    curtable = curtable.select(lambda f: f["geonunit"] in countries)

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


        
        

