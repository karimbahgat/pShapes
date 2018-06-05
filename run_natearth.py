# -*- coding: utf8 -*-

# natearth example
####################

from pshapes import *

##import pythongis as pg
##curtable = pg.VectorData(r"C:\Users\kimok\OneDrive\Documents\GitHub\PythonGis\tests\data\ne_10m_admin_1_states_provinces.shp", encoding="utf8", encoding_errors="replace")
##fdsfsd

# load current data
print '# current data'
current = CurrentBoundaries(r"C:\Users\kimok\OneDrive\Documents\GitHub\PythonGis\tests\data\ne_10m_admin_1_states_provinces.shp",
                         'geonunit',
                         'name',
                         'name_alt',
                         'iso_3166_2',
                         'fips',
                         'code_hasc',
                         'type_en',
                         None, # capital
                         )

def prepare(feat):
    feat['geonunit'] = feat['admin'] if not feat['geonunit'].strip() else feat['geonunit']

current.prepare(prepare)

def standardize_countries(name):
    if name == 'United States of America': return 'United States'
    if name == 'Republic of Congo': return 'Republic of the Congo'
    if name == 'Guinea Bissau': return 'Guinea-Bissau'
    if name == 'Gambia': return 'The Gambia'
    return name

current.standardize_countries(standardize_countries)

# bugfixes and modifications to fit changedata

def fixfunc(feat):
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

current.bugfix(fixfunc)

def modify_guinea(guinea):
    for f in guinea:
        if f["code_hasc"] in "GN.BF GN.BK GN.FR GN.GA GN.KN":
            f.row = [None for _ in range(len(guinea.fields))]
            f["geonunit"] = "Guinea"
            f["name"] = "Boke"
            f["name_alt"] = "Boké".decode('utf8')
            f["iso_3166_2"] = "B"
        elif f["code_hasc"] in "GN.CO GN.DU GN.FO GN.KD GN.TE":
            f.row = [None for _ in range(len(guinea.fields))]
            f["geonunit"] = "Guinea"
            f["name"] = "Kindia"
            f["iso_3166_2"] = "D"
        elif f["code_hasc"] in "GN.DB GN.DI GN.FA GN.KS":
            f.row = [None for _ in range(len(guinea.fields))]
            f["geonunit"] = "Guinea"
            f["name"] = "Faranah"
            f["iso_3166_2"] = "F"
        elif f["code_hasc"] in "GN.KA GN.KE GN.KO GN.MD GN.SI":
            f.row = [None for _ in range(len(guinea.fields))]
            f["geonunit"] = "Guinea"
            f["name"] = "Kankan"
            f["iso_3166_2"] = "K"
        elif f["code_hasc"] in "GN.KB GN.LA GN.LE GN.ML GN.TO":
            f.row = [None for _ in range(len(guinea.fields))]
            f["geonunit"] = "Guinea"
            f["name"] = "Labe"
            f["name_alt"] = "Labé".decode('utf8')
            f["iso_3166_2"] = "L"
        elif f["code_hasc"] in "GN.DL GN.MM GN.PI":
            f.row = [None for _ in range(len(guinea.fields))]
            f["geonunit"] = "Guinea"
            f["name"] = "Mamou"
            f["iso_3166_2"] = "M"
        elif f["code_hasc"] in "GN.BE GN.GU GN.LO GN.MC GN.NZ GN.YO":
            f.row = [None for _ in range(len(guinea.fields))]
            f["geonunit"] = "Guinea"
            f["name"] = "Nzerekore"
            f["name_alt"] = "Nzérékoré".decode('utf8')
            f["iso_3166_2"] = "N"
        elif f["code_hasc"] == "GN.CK":
            f.row = [None for _ in range(len(guinea.fields))]
            f["geonunit"] = "Guinea"
            f["name"] = "Conakry"
            f["iso_3166_2"] = "C"
        else:
            print f.row
            fsfsdfsdf
    guinea = guinea.aggregate("iso_3166_2",
                              fieldmapping=[(name,name,"first") for name in guinea.fields],
                              geomfunc="union")
    return guinea

current.modify_country('Guinea', modify_guinea)

def modify_burkina(burkina):
    burkina = burkina.aggregate("region",
                              fieldmapping=[(name,name,"first") for name in burkina.fields],
                              geomfunc="union")
    burkina.compute("name", lambda f: f["region"])
    burkina.compute("iso_3166_2", lambda f: f["region_cod"])
    for f in burkina:
        f.row = [f[fl] if fl in "geonunit iso_3166_2 name name_alt".split() else None for fl in burkina.fields]
    return burkina

current.modify_country('Burkina Faso', modify_burkina)


# load change data
print '# change data'
changes = ChangeData('pshapes_raw_auto.csv')

def ignore(f):
    # temp country hacks to exclude changes that are newer than the NatEarth reference dataset
    if f['fromcountry']=='Ivory Coast' and f["date"] == "2011-09-28":
        return True
    if f['fromcountry']=='Equatorial Guinea' and f["date"] == "2015-08-03":
        return True
    
    # temp hack ones
    if (f['tocountry']=='Australia' and f["toname"] in ["Coral Sea Islands Territory","Ashmore and Cartier Islands"]):
        return True

    return False

changes.ignore_events(ignore)

# build
print '# build'
out = build(current, changes, 'pshapes_natearth.geojson')

print 'voila!'


