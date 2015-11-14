

import pygeoj
import sys
sys.path.append(r"C:\Users\kimo\Documents\GitHub\Tably")
import tably
import shapefile



natearthorig = shapefile.Reader("ne_10m_admin_1_states_provinces.shp", encoding="latin")
shaperecords = zip(natearthorig.iterRecords(),natearthorig.iterShapes())
fieldnames = [f[0] for f in natearthorig.fields[1:]]
codeupdates = tably.load("natearthprovs_codeupdates.xlsx")
output = pygeoj.GeojsonFile()
for (nerow,neshp),xlrow in zip(sorted(shaperecords, key=lambda x: x[0]),sorted(codeupdates,key=lambda x: x["adm1_code"])):
    assert nerow[0] == xlrow["adm1_code"]
    # remove missing obj
    xlrow["code_hasc"] = xlrow["code_hasc"] or ""
    xlrow["oldiso2"] = xlrow["oldiso2"] or ""
    xlrow["newiso2"] = xlrow["newiso2"] or ""
    xlrow["fips"] = xlrow["fips"] or ""
    xlrow["type"] = xlrow["type"] or ""
    xlrow["type_en"] = xlrow["type_en"] or ""
    
    rowdict = dict(zip(fieldnames,nerow))
    rowdict["code_hasc"] = xlrow["code_hasc"]
    rowdict["iso_3166_2"] = xlrow["oldiso2"][:2] + xlrow["newiso2"].zfill(2)
    rowdict["fips"] = xlrow["fips"]
    rowdict["type"] = xlrow["type"]
    rowdict["type_en"] = xlrow["type_en"]

    output.add_feature(properties=rowdict, geometry=neshp)

import json
open("natearthprovs_codeupdates.geojson","w").write(json.dumps(output.__geo_interface__, indent=4, encoding="latin"))
#output.save("natearthprovs_codeupdates.geojson", encoding="latin")

