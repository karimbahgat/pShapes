
import itertools
import datetime
import warnings
import dateutil, dateutil.parser
import pygeoj
import shapely, shapely.ops, shapely.geometry
from unidecode import unidecode

from .process import *
from .prep import *

import pythongis as pg

########################

def build(currentboundaries, changedata, outfile):
    curtable = currentboundaries
    eventstable = changedata

    # initiate results with events from changedata
    results = ResultsTable()
    for date,changetable in eventstable.data.manage.split("date"):
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
                                ids={"Name":row["fromname"].strip(),
                                     "Alterns":[alt.strip() for alt in row["fromalterns"].split("|")] if row["fromalterns"] else [],
                                    "HASC":row["fromhasc"],
                                    "ISO":row["fromiso"],
                                    "FIPS":row["fromfips"]},
                                other={"Type":row["fromtype"],
                                       "Capital":row["fromcapital"]},
                                geometry=None)
                                
            toprov = Province(country=row["tocountry"],
                                start=None,
                                end=None,
                                ids={"Name":row["toname"].strip(),
                                     "Alterns":[alt.strip() for alt in row["toalterns"].split("|")] if row["toalterns"] else [],
                                     "HASC":row["tohasc"],
                                     "ISO":row["toiso"],
                                     "FIPS":row["tofips"]},
                                other={"Type":row["totype"],
                                       "Capital":row["tocapital"]},
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
    
    # get relevant countries from the change data
    countries = set()
    for f in eventstable.data:
        countries.add(f["fromcountry"])
        countries.add(f["tocountry"])

    # limit to only those countries
    curtable.data = curtable.data.select(lambda f: f[curtable.countryfield] in countries)

    # add current to results
    print 'adding current to results'
    for feat in curtable.data:
        # add
        results.add_province(country=feat[curtable.countryfield],
                             start=None,
                             end=None,
                             ids={"Name": feat[curtable.subnamefield].strip(),
                                  "Alterns": [alt.strip() for alt in feat[curtable.subalternsfield].strip().split("|")] if curtable.subalternsfield and feat[curtable.subalternsfield] else [],
                                  "ISO": feat[curtable.subisofield] if curtable.subisofield else None, #.split('-')[-1] if curtable.subisofield and feat[curtable.subisofield] else None,
                                  "FIPS": feat[curtable.subfipsfield] if curtable.subfipsfield else None, #[2:] if curtable.subfipsfield and feat[curtable.subfipsfield] else None,
                                  "HASC": feat[curtable.subhascfield] if curtable.subhascfield else None, #.split('-')[-1] if curtable.subhascfield and feat[curtable.subhascfield] else None,
                                  },
                             other={"Type": feat[curtable.subtypefield] if curtable.subtypefield and feat[curtable.subtypefield] else None,
                                    "Capital": feat[curtable.subcapitalfield] if curtable.subcapitalfield and feat[curtable.subcapitalfield] else None},
                             geometry=feat.geometry)

    # begin backtracking
    print 'beginning backtracking'
    results.begin_backtracking()

    # Save final geojson table
    # TODO: do via pg instead
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
    finaldata.save(outfile)

    return finaldata
