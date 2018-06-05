# -*- coding: utf8 -*-

# OpenStreetMap example
####################

from pshapes import *



# load current data
print '# current data'
current = CurrentBoundaries('current_osm.geojson',
                         'country',
                         'subname',
                         'subaltnames',
                         'subiso',
                         None,#'fips',
                         None,#'code_hasc',
                         None,#'type_en',
                         'subcapital',
                         )

def prepare(feat):
    # remove prov type from name
    # TODO: maybe move to separate type field
    name = feat['subname'] or ''
    for typ in ['Province','District','County','State','Region','Prefecture','Governate','Governorate','Division']:
        if typ in name:
            feat['subname'] = name.replace(typ,'').strip()
            break

current.prepare(prepare)

def standardize_countries(name):
    if name == 'United States of America': return 'United States'
    if name == 'Republic of Congo': return 'Republic of the Congo'
    if name == 'Guinea Bissau': return 'Guinea-Bissau'
    if name == 'Gambia': return 'The Gambia'
    return name

current.standardize_countries(standardize_countries)



# bugfixes and modifications to fit changedata

#current.bugfix(fixfunc)
#current.modify_country('Guinea', modify_guinea)
#current.modify_country('Burkina Faso', modify_burkina)



# load change data
print '# change data'
changes = ChangeData('pshapes_raw_auto.csv')

def ignore(f):
    # temp country hacks to exclude changes that are newer than the reference dataset
    if f['fromcountry']=='Equatorial Guinea' and f["date"] == "2015-08-03":
        return True

    return False

changes.ignore_events(ignore)



# build
print '# build'
out = build(current, changes, 'pshapes_osm.geojson')

print 'voila!'


