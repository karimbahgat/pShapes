
import pythongis as pg
import pycountries as pc

# TODO: make much smaller size

def region(f):
    if f['country'] == 'Greenland':
        return 'North America'
    elif f['country'] == 'Russia':
        return 'Asia'
    elif f['country'] == 'Mexico':
        return 'Central America'
    elif 'Sudan' in f['country']:
        return 'Africa'
    elif f['country'] in 'Georgia Azerbaijan Armenia':
        return 'Asia'

    if 'Western Asia' in f['region']:
        return 'Middle East'
    elif 'Northern Africa' in f['region']:
        return 'Middle East'
    elif f['country'] in 'Iran':
        return 'Middle East'
    
    if 'Europe' in f['region']:
        return 'Europe'
    if 'Northern America' in f['region']:
        return 'North America'
    elif 'Africa' in f['region']:
        return 'Africa'
    elif 'Asia' in f['region']:
        return 'Asia'
    elif 'Caribbean' in f['region']:
        return 'Central America'
    elif 'esia' in f['region'] or 'Australia' in f['region']:
        return 'Oceania'
    else:
        return f['region']

# save our own country file
contrs = pg.VectorData(r"C:\Users\kimok\Downloads\ne_10m_admin_0_map_units\ne_10m_admin_0_map_units.shp", encoding='latin') #r"C:\Users\kimok\Downloads\ne_10m_admin_0_countries\ne_10m_admin_0_countries.shp")

contrs.rename_field('ADM0_A3_IS', 'iso3')
contrs.compute('iso3', lambda f: f['ADM0_A3'] if f['SOVEREIGNT'] == 'United Kingdom' else f['iso3'])

contrs = contrs.select(lambda f: f['iso3']!='ATA') # antarctica
contrs.compute('iso3', lambda f: 'SOM' if f['SOVEREIGNT']=='Somaliland' else f['iso3'])
contrs.compute('iso3', lambda f: 'ESH' if f['SOVEREIGNT']=='Western Sahara' else f['iso3'])
contrs.compute('iso3', lambda f: 'KOS' if f['SOVEREIGNT']=='Kosovo' else f['iso3'])
contrs = contrs.aggregate(['iso3'], 'union')
def tryiso(f):
    try: return pc.Country(code=f['iso3']).name
    except Exception as err:
        print 'FAILED:',f['iso3'],err
        return ''
def tryreg(f):
    try: return pc.Country(code=f['iso3']).region.name
    except Exception as err:
        print 'FAILED:',f['iso3'],err
        return ''
contrs.compute('country', tryiso)
contrs.compute('region', tryreg)
contrs.compute('region', region)

contrs = contrs.select(lambda f: f['country']) # exclude special small island that couldnt find country name

contrs.save('countries.geojson')

##for f in contrs:
##    try: f.geometry = f.get_shapely().simplify(0.05, preserve_topology=True).__geo_interface__
##    except: print 'FAILED CLEANING:',f.row
##print contrs
##contrs.save('countries_semisimple.geojson')
##
##fdsfsdf

for f in contrs:
    try: f.geometry = f.get_shapely().simplify(0.2, preserve_topology=True).__geo_interface__
    except: print 'FAILED CLEANING:',f.row
print contrs
contrs.save('countries_simple.geojson')


# load regional countries
allco = contrs

# group and collapse
def concat(vals):
    return '|'.join(vals)
regs = pg.VectorData(fields='region countries'.split())
for regname,reg in allco.manage.split('region'):
    if not regname: continue
    print regname
    for n in reg.field_values('country'):
        print n
    print 'collapsing'
    agg = reg.manage.buffer(0.1).aggregate(lambda f: 1, 'union', fieldmapping=[('countries','country',concat)]).manage.clean(0.01, preserve_topology=True).manage.buffer(-0.3)
    geoj = list(agg)[0].geometry
    row = [regname, list(agg)[0]['countries']]
    print row
    regs.add_feature(row, geoj)

regs.view(text=lambda f: f['region'])
regs.save('regions.geojson')

regdict = {}
for f in regs:
    regdict[f['region']] = f['countries']

import json
json.dump(regdict, open('regions.json','wb'))


