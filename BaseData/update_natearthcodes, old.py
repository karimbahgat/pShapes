
# Updates provcodes of the natural earth province data with those found on statoids
# WORKS!
# TODO: Note that some will still not match due to (these will have to be manually input later):
#       - minor differences in names (maybe implement difflib match?)
#       - statoids including newer additions or dropouts than naturalearth or vice versa (no solution)
#       - for some countries natural earth uses what statoids considers level2 districts instead of level1 (hardcode which these are)
# TODO: Maybe also update provtype and capital

import sys
import itertools
import shapefile
import pygeoj

natearthorig = shapefile.Reader("ne_10m_admin_1_states_provinces.shp", encoding="latin")
fieldnames = [f[0] for f in natearthorig.fields[1:]]
recs = natearthorig.iterRecords()
recs = ([v.decode("latin") if isinstance(v,bytes) else v for v in r] for r in recs)
recs = (dict(zip(fieldnames,r)) for r in recs)
shapes = natearthorig.iterShapes()
shaperecords = zip(recs,shapes)

import urllib2

##def scrapestatoids():
##    raw = urllib2.urlopen('http://www.statoids.com/wab.html').read()
##    from bs4 import BeautifulSoup as bs
##    soup = bs(raw)
##    codes = soup.find('table')
##
##    for tr in codes.find_all('tr'):
##        row = [td.string for td in tr.find_all('td')]
##        if len(row) < 2: continue
##        print row
##        iso2 = row[1]
##        print repr(iso2)
##        #scrapecodes("http://www.statoids.com/u%s.html"%iso2)
        
def scrapecodes(url):
    try:
        raw = urllib2.urlopen(url).read()
    except:
        raw = None
        print "FAIL:",url
        
    if raw:
        from bs4 import BeautifulSoup as bs
        soup = bs(raw.decode("latin")) # bs4 will take the latin unicode and convert to utf8 unicode
        codes = soup.find('table', class_='st')

        fields = [th.string for th in codes.find('tr', class_='hd')]
        fields[0] = "Name" # standardize the name field header
        for tr in codes.find_all('tr'):
            row = [td.string or "".decode("utf8") for td in tr.find_all('td')]
            if len(row) != len(fields): continue
            rowdict = dict(zip(fields,row))
            yield rowdict

# update the geofile
output = pygeoj.GeojsonFile()
for iso2,items in itertools.groupby(sorted(shaperecords, key=lambda x: x[0]["iso_a2"]), key=lambda x: x[0]["iso_a2"]):
    if not len(iso2) == 2 or not iso2.isalnum(): continue
    print iso2
    strows = list(scrapecodes("http://www.statoids.com/u%s.html"%iso2.lower()))
    if not strows: continue
    for nerow,neshp in items:
        nenames = [nerow["name"].strip()] + nerow["name_alt"].strip().split("|")
        print nenames

        necodes = [nerow["code_hasc"],nerow["iso_3166_2"],nerow["fips"]]

        match = next((strow for strow in strows if strow["Name"].strip() in nenames), None)

        if not match:
            match = next((strow for strow in strows if strow.get("HASC") and strow["HASC"] == nerow["code_hasc"]), None)

        if not match:
            match = next((strow for strow in strows if strow.get("FIPS") and strow["FIPS"] == nerow["fips"]), None)

        if not match:
            match = next((strow for strow in strows if strow.get("ISO") and strow["ISO"] == nerow["iso_3166_2"]), None)
        
        if match:

            # match found, so override codes and stop looking
            nerow["code_hasc"] = match.get("HASC", nerow["code_hasc"])
            nerow["iso_3166_2"] = iso2 + "-" + match.get("ISO", nerow["iso_3166_2"])
            nerow["fips"] = match.get("FIPS", nerow["fips"])
            print "updated",repr(match),repr((nerow["code_hasc"],nerow["iso_3166_2"],nerow["fips"]))
        
        output.add_feature(properties=nerow, geometry=neshp)

import json
open("natearthprovs_codeupdates.geojson","w").write(json.dumps(output.__geo_interface__, indent=4, encoding="latin"))
#output.save("natearthprovs_codeupdates.geojson", encoding="latin")

