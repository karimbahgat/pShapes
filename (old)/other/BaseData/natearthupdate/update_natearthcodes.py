
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
import csv

natearthorig = shapefile.Reader("old/ne_10m_admin_1_states_provinces.shp") #, encoding="latin")
print natearthorig.numRecords
fieldnames = [f[0] for f in natearthorig.fields[1:]]
recs = natearthorig.iterRecords()
recs = ([v.decode("utf8","ignore") if isinstance(v,bytes) else v for v in r] for r in recs)
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
        #print "FAILED TO SCRAPE:",url
        
    if raw:
        from bs4 import BeautifulSoup as bs
        soup = bs(raw.decode("latin")) # bs4 will take the latin unicode and convert to utf8 unicode
        codes = soup.find('table', class_='st')
        if codes:
            fields = [th.string for th in codes.find('tr', class_='hd')]
            fields[0] = "Name" # standardize the name field header
            fields = [f.replace("GEC","FIPS") for f in fields] # interpret GEC codes same as FIPS
            fields = [f.strip() for f in fields]
            for tr in codes.find_all('tr'):
                row = [td.string or "".decode("utf8") for td in tr.find_all('td')]
                row = [v.strip() for v in row]
                if len(row) != len(fields): continue
                rowdict = dict(zip(fields,row))
                yield rowdict

# update the geofile
changes_obj = open("new/changes.csv","wb")
changes = csv.writer(changes_obj, delimiter=";")
changes.writerow(["country","fromname","fromhasc","fromiso","fromfips","toname","tohasc","toiso","tofips"])

nonmatches_obj = open("new/nonmatches.csv","wb")
nonmatches = csv.writer(nonmatches_obj, delimiter=";")
nonmatches.writerow(["country","name"])

WENCODING = "utf8"

writer = shapefile.Writer()
writer.fields = list(natearthorig.fields)
for iso2,items in itertools.groupby(sorted(shaperecords, key=lambda x: x[0]["iso_a2"]), key=lambda x: x[0]["iso_a2"]):
    items = list(items)
    
    if not len(iso2) == 2 or not iso2.isalnum():
        print "INVALID COUNTRY ISO",iso2
        for nerow,neshp in items:
            nerow = dict([(f,v.encode(WENCODING) if isinstance(v,unicode) else v)
                          for f,v in nerow.items()])
            writer.record(**nerow)
            writer._shapes.append(neshp)
        continue

    if any((nerow["region"].strip() for nerow,neshp in items)) \
       and iso2.lower() not in ['ba','be','bt','ca','cn','cv','gb','gn','gr','gw',
                                'hr','in','it','jp','la','lk','np','nz','pt','rs','sd',
                                'ss','th','tj','ug','vn']:
        strows = list(scrapecodes("http://www.statoids.com/y%s.html"%iso2.lower()))
        if strows:
            print "level 2"
        else:
            print "level 1"
            strows = list(scrapecodes("http://www.statoids.com/u%s.html"%iso2.lower()))
    else:
        print "level 1"
        strows = list(scrapecodes("http://www.statoids.com/u%s.html"%iso2.lower()))
        
    if not strows:
        print "FAILED TO SCRAPE",iso2
        for nerow,neshp in items:
            nerow = dict([(f,v.encode(WENCODING) if isinstance(v,unicode) else v)
                          for f,v in nerow.items()])
            writer.record(**nerow)
            writer._shapes.append(neshp)
        continue
    
    print "SCRAPED",iso2
    for nerow,neshp in items:
        nenames = [nerow["name"].strip()] + nerow["name_alt"].strip().split("|")
        # TODO: for Italy, do not consider altern names, since they refer to region above and are duplicate
        # ...
        #print nenames

        necodes = [nerow["code_hasc"],nerow["iso_3166_2"],nerow["fips"]]

        match = next((strow for strow in strows if strow["Name"].strip() and strow["Name"].strip() in nenames), None)

##        if not match:
##            match = next((strow for strow in strows if strow.get("HASC") and strow["HASC"] == nerow["code_hasc"]), None)
##
##        if not match:
##            match = next((strow for strow in strows if strow.get("FIPS") and strow["FIPS"] == nerow["fips"]), None)
##
##        if not match:
##            match = next((strow for strow in strows if strow.get("ISO") and strow["ISO"] == nerow["iso_3166_2"]), None)
        
        if match:

            # match found, so override codes and stop looking
            nerow["code_hasc"] = match.get("HASC", nerow["code_hasc"])
            nerow["iso_3166_2"] = iso2 + "-" + match.get("ISO") if match.get("ISO") else nerow["iso_3166_2"]
            nerow["fips"] = match.get("FIPS", nerow["fips"])
            if [nerow["code_hasc"],nerow["iso_3166_2"],nerow["fips"]] != necodes:
                #print "changed",repr(nenames[0]),necodes,"-->",repr(match["Name"]),[nerow["code_hasc"],nerow["iso_3166_2"],nerow["fips"]]
                wrow = [iso2, nenames[0]] + list(necodes) + [match["Name"],nerow["code_hasc"],nerow["iso_3166_2"],nerow["fips"]]
                changes.writerow([v.encode(WENCODING) if isinstance(v,unicode) else v for v in wrow])

        else:
            nonmatches.writerow([iso2, nenames[0].encode(WENCODING)])

        nerow = dict([(f,v.encode(WENCODING) if isinstance(v,unicode) else v)
                      for f,v in nerow.items()])

        writer.record(**nerow)
        writer._shapes.append(neshp)

writer.save("new/ne_10m_admin_1_states_provinces.shp")
changes_obj.close()
nonmatches_obj.close()

#import json
#open("natearthprovs_codeupdates.geojson","w").write(json.dumps(output.__geo_interface__, indent=4, encoding="latin"))
#output.save("natearthprovs_codeupdates.geojson", encoding="latin")

