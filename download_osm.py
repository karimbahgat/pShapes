
# Download OSM boundary data to create a new admin dataset

# TODO: some countries need to get another admin_level, eg UK, some island states, etc (see https://wiki.openstreetmap.org/wiki/Tag:boundary=administrative#10_admin_level_values_for_specific_countries)
# TODO: need to do some cleaning of names, to remove type info from the name (eg Cairo governate)
#       possibly even moving these to a separate type field...


import pythongis as pg
import sqlite3
import json

DLPATH = 'download_osm.db'
fields = ['country','subname','subaltnames','subiso','subcapital','subcapitalx','subcapitaly','wiki','wikidata']

DOWNLOAD = False
if DOWNLOAD:
    print 'downloading latest osm boundaries'
    import time
    import overpy
    import pycountries as pc
    import shapely, shapely.geometry, shapely.ops
    db = sqlite3.connect(DLPATH)
    dbwriter = db.cursor()
    #dbwriter.execute('DROP TABLE IF EXISTS current_osm')
    #dbwriter.execute('''CREATE TABLE current_osm (country text, subname text, subaltnames text, subiso text, subcapital text, subcapitalx real, subcapitaly real, wiki text, wikidata text, geoj text)''')

    existing = [r[0] for r in dbwriter.execute('select distinct country from current_osm')]
    print existing

    api = overpy.Overpass()
    for cn in pc.all_countries(): #[pc.Country(name='Norway')]
        # skip if necessary
        if cn.name in existing or cn.area < 500:
            continue
        
        print repr(cn.name)
        iso2 = cn.iso2

        lvl = {'AL':6,
               'SN':3,
               'IS':3,
               'EE':6,
               'CY':6,
               'BN':6,
               'PS':5,
               #'GB':6, # add later, note that very large size
               }.get(iso2, 4)
        query = """
[timeout:380][out:json];
(area["ISO3166-1"="{iso2}"][admin_level=2];)->.a;
(
  relation["type"="boundary"]["boundary"="administrative"]["admin_level"="{lvl}"](area.a);
  node(r:"admin_centre")(area.a); 
);
out geom;
                """.format(iso2=iso2, lvl=lvl)
        result = api.query(query)
        for rel in result.relations:
            # get tag info
            rowdict = {'country':cn.name, #rel.tags['is_in:country'],
                       'subname':rel.tags.pop('name:en', rel.tags.pop('int_name', rel.tags.pop('name', None))),
                       'subaltnames':[rel.tags.get(var) for var in ['name','int_name','official_name','short_name','loc_name'] if rel.tags.get(var)],
                       'subiso': rel.tags.get('ISO3166-2','?'),
                       'subcapital': '?',
                       'wiki': rel.tags.get('wikipedia','?'),
                       'wikidata': rel.tags.get('wikidata','?'),
                       }
            if 'alt_name' in rel.tags:
                rowdict['subaltnames'] += rel.tags.get('alt_name').split(';')
            rowdict['subaltnames'] = '|'.join(rowdict['subaltnames'])
            print rowdict
            
            # get all ways as a multipoly w holes, or admin capital
            lines = []
            for mem in rel.members:
                line = []
                if 'Way' in str(type(mem)):
                    for pt in mem.geometry:
                        x,y = float(pt.lon),float(pt.lat)
                        line.append((x,y))
                elif 'Node' in str(type(mem)):
                    if mem.role == u'admin_centre':
                        node = next((n for n in result.nodes if n.id==mem.ref),None) #or mem.resolve(True)
                        if node:
                            capname = node.tags.get('name:en', node.tags.get('name', '?'))
                            rowdict['subcapital'] = capname
                            if hasattr(node,'lat') and hasattr(node,'lon'):
                                rowdict['subcapitalx'] = float(node.lon)
                                rowdict['subcapitaly'] = float(node.lat)
                line = shapely.geometry.LineString(line).simplify(0.0001, preserve_topology=True)
                lines.append(line)
                
            # connect lines to form a polygon
            print 'polygonizing...'
            
            try:
                polys = shapely.ops.polygonize(lines)
                mpoly = shapely.geometry.MultiPolygon(polys)
            except:
                mpoly = None
                
            if mpoly:
                geoj = mpoly.__geo_interface__
            else:
                geoj = None
                
            # add to data
            row = [rowdict.get(f) for f in fields] + [unicode(geoj)]
            dbwriter.execute("INSERT INTO current_osm VALUES (%s)" % ", ".join(("?" for _ in row)), row)
            
        db.commit()
        time.sleep(2)

    db.commit()
    db.close()


# clip by coastline since boundaries extend into ocean
# use natearth since osm coastline is too detailed and big size
##print 'loading landmass'
##landmass = pg.VectorData(r"C:\Users\kimok\Downloads\ne_10m_land\ne_10m_land.shp")
##print landmass
##print 'dicing landmass for better speed'
##tlandmass = pg.VectorData(fields=landmass.fields)
##for tile in pg.vector.manager.tiled(landmass, tiles=(10,10)):
##    print tile
##    for f in tile:
##        tlandmass.add_feature(f.row, f.geometry)
##tlandmass.save('diced_coastlines.geojson')
##print 'diced!', tlandmass

tlandmass = pg.VectorData('diced_coastlines.geojson')

out = pg.VectorData(fields=fields)
print 'clipping admins to coastline...'

##clipped = curtable.manage.spatial_join(tlandmass, 'intersects', clip='intersection')
##
##print 'unioning the diced admin results...'
##clipunion = clipped.aggregate(['country','subname'], 'union',
##                              fieldmapping=[(f,f,'first') for f in clipped.fields if f not in 'country subname'])

tlandmass.create_spatial_index()
db = sqlite3.connect(DLPATH)
dbwriter = db.cursor()
for row in dbwriter.execute('SELECT * FROM current_osm'):
    row = list(row)
    geoj = row.pop(-1)
    if geoj: geoj = geoj.replace("'", '"').replace('(','[').replace(')',']').replace('],]',']]').replace('None','null')
    geoj = json.loads(geoj)
    p = out.add_feature(row, geoj)

    if not p.geometry:
        print '!!! NULLGEOM'
        continue
    print p.row[:2]
    pgeom = p.get_shapely()
    if not pgeom.is_valid:
        print '!!! INVALID'
        continue
    
    #print 'finding matches...'
    matches = [t for t in tlandmass.quick_overlap(p.bbox) if t.get_shapely().intersects(pgeom)]
    if not matches:
        print '!!! NO LANDMASS??'
        continue
    matchdat = pg.VectorData(fields=tlandmass.fields, features=matches)
    
    #print 'collapsing...'
    matchagg = matchdat.aggregate(lambda f: 1, 'union')
    mgeom = list(matchagg)[0].get_shapely()

    #print 'intersecting...'
    isec = pgeom.intersection(mgeom)
    p.geometry = isec.__geo_interface__

# save
print 'saving'
out.save('current_osm.geojson', encoding='utf8')

# bonus, prov capital file
print 'making bonus capitals file'
caps = pg.VectorData(fields=['country','subname','subcapital'])
for row in dbwriter.execute('SELECT country,subname,subcapital,subcapitalx,subcapitaly FROM current_osm'):
    row = list(row)
    y,x = row.pop(-1),row.pop(-1)
    if x != None and y != None:
        geoj = {'type':'Point', 'coordinates':[x,y]}
    else:
        geoj = None
    caps.add_feature(row, geoj)
caps.save('current_osm_capitals.geojson', encoding='utf8')







