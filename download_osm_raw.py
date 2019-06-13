
# Download OSM boundary data to create a new admin dataset

# TODO: some countries need to get another admin_level, eg UK, some island states, etc (see https://wiki.openstreetmap.org/wiki/Tag:boundary=administrative#10_admin_level_values_for_specific_countries)
# TODO: need to do some cleaning of names, to remove type info from the name (eg Cairo governate)
#       possibly even moving these to a separate type field...


import pycountries as pc
import pythongis as pg
import shapely
import sqlite3
import json

DIR = r'C:\Users\kimok\Desktop\pshapes OSM output\\'
DLPATH = DIR + 'download_osm_raw.db'
DOWNLOAD = False


######################################################

fields = ['country','level','tags','lines','nodes']

if DOWNLOAD:
    print 'downloading latest osm boundaries'
    import time
    import overpy
    import shapely, shapely.geometry, shapely.ops
    db = sqlite3.connect(DLPATH)
    dbwriter = db.cursor()
    #dbwriter.execute('DROP TABLE IF EXISTS current_osm_raw')
    #dbwriter.execute('''CREATE TABLE current_osm_raw (country text, level real, tags text, lines text, nodes text)''')

    existing = [(c,l) for c,l in dbwriter.execute('select distinct country,level from current_osm_raw')]
    print existing

    api = overpy.Overpass()
    for cn in pc.all_countries(): #[pc.Country(name='Norway')]        
        print repr(cn.name)
        iso2 = cn.iso2

        lvl = {'AL':6,
               'SN':3,
               'IS':3,
               'EE':6,
               'CY':6,
               'BN':6,
               'PS':5,
               'GB':6, # add later, note that very large size
               }.get(iso2, 4)

        # skip if necessary
        if (cn.name,lvl) in existing or cn.area < 500:
            continue
        
        query = """
[timeout:680][out:json];
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
            rowdict = {'country':cn.name,
                       'level':lvl,
                       'tags':rel.tags}
            print rowdict
            
            # get all ways as a multipoly w holes, or admin capital
            lines = []
            nodes = [] # should only be one capital though...
            for mem in rel.members:
                
                line = []
                if 'Way' in str(type(mem)):
                    for pt in mem.geometry:
                        x,y = float(pt.lon),float(pt.lat)
                        line.append((x,y))
                lines.append(line)
                
                if 'Node' in str(type(mem)):
                    if mem.role == u'admin_centre':
                        node = next((n for n in result.nodes if n.id==mem.ref),None) #or mem.resolve(True)
                        if node:
                            nodetags = node.tags
                            if hasattr(node,'lat') and hasattr(node,'lon'):
                                nodecoords = float(node.lon), float(node.lat)
                            else:
                                nodecoords = None
                            nodes.append((nodetags,nodecoords))
                            
            rowdict['lines'] = lines
            rowdict['nodes'] = nodes
                
            # add to data
            row = [rowdict.get(f) for f in fields]
            row = [json.dumps(v) if not isinstance(v, (basestring,int,float)) else v
                   for v in row]
            dbwriter.execute("INSERT INTO current_osm_raw VALUES (%s)" % ", ".join(("?" for _ in row)), row)
            
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

tlandmass = pg.VectorData(DIR + 'diced_coastlines.geojson')

fields = ['country','iso','subname','subaltnames','subiso','subcapital','subcapitalx','subcapitaly','wiki','wikidata']
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
cdict = dict()
for row in dbwriter.execute('SELECT * FROM current_osm_raw'):
    country,level,tags,lines,nodes = row
    tags = json.loads(tags)
    lines = json.loads(lines)
    nodes = json.loads(nodes)

    # get tag info
    rowdict = {'country':country, #rel.tags['is_in:country'],
               'iso':'',
               'subname':tags.pop('name:en', tags.pop('int_name', tags.pop('name', None))),
               'subaltnames':[tags.get(var) for var in ['name','int_name','official_name','short_name','loc_name'] if tags.get(var)],
               'subiso': tags.get('ISO3166-2','?'),
               'subcapital': '?',
               'wiki': tags.get('wikipedia','?'),
               'wikidata': tags.get('wikidata','?'),
               }
    if 'alt_name' in tags:
        rowdict['subaltnames'] += tags.get('alt_name').split(';')
    rowdict['subaltnames'] = '|'.join(rowdict['subaltnames'])

    # some provs were retrieved wrongly for neighbouring country due to partial overlap
    # try to determine and overwrite the correct country if possible.
    for cf in ['is_in:country_code', 'ISO3166-2', 'ISO3166-2']:
        if cf in tags:
            code = tags[cf][:2]
            rowdict['iso'] = code
            try:
                c = pc.Country(code=code)
                if code not in cdict:
                    cdict[code] = c.name
                realcountry = cdict.get(code)
                rowdict['country'] = realcountry
            except:
                print '!!! found real country but failed',tags[cf]
                pass

    if nodes:
        nodetags,nodecoords = nodes[0]
        capname = nodetags.get('name:en', nodetags.get('name', '?'))
        rowdict['subcapital'] = capname
        if nodecoords:
            x,y = nodecoords
            rowdict['subcapitalx'] = float(x)
            rowdict['subcapitaly'] = float(y)
    print rowdict

    # connect lines to form a polygon
    print 'polygonizing...'
    try:
        lines = [shapely.geometry.LineString(line).simplify(0.00001, preserve_topology=True)
                 for line in lines]
        polys = shapely.ops.polygonize(lines)
        mpoly = shapely.geometry.MultiPolygon(polys)
    except:
        mpoly = None
        
    if mpoly:
        geoj = mpoly.__geo_interface__
    else:
        geoj = None
    
    row = [rowdict.get(f) for f in fields]
    p = out.add_feature(row, geoj)

    if not p.geometry:
        print '!!! NULLGEOM'
        continue
    print p.row[:3]
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
out.save(DIR + 'current_osm.geojson', encoding='utf8')

# bonus, prov capital file
print 'making bonus capitals file'
caps = pg.VectorData(fields=['country','subname','subcapital'])
for feat in out:
    row = [feat['country'], feat['subname'], feat['subcapital']]
    x,y = feat['subcapitalx'],feat['subcapitaly']
    if x != None and y != None:
        geoj = {'type':'Point', 'coordinates':[x,y]}
    else:
        geoj = None
    caps.add_feature(row, geoj)
caps.save(DIR + 'current_osm_capitals.geojson', encoding='utf8')







