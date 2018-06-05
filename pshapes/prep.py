# -*- coding: cp1252 -*-

import itertools
import datetime
import warnings
import urllib
import dateutil, dateutil.parser
import pygeoj
import shapely, shapely.ops, shapely.geometry
from unidecode import unidecode

from .process import *
import pythongis as pg


##############################

class CurrentBoundaries():

    def __init__(self, filename, countryfield, subnamefield, subalternsfield, subisofield, subfipsfield='', subhascfield='', subtypefield='', subcapitalfield=''): 
        self.data = pg.VectorData(filename, encoding="utf8", encoding_errors="replace",
                                  )
        self.data = self.data.select(lambda f: f.geometry) #f.get_shapely().is_valid)
        self.countryfield = countryfield
        self.subnamefield = subnamefield
        self.subalternsfield = subalternsfield
        self.subisofield = subisofield
        self.subfipsfield = subfipsfield
        self.subhascfield = subhascfield
        self.subtypefield = subtypefield
        self.subcapitalfield = subcapitalfield
        print 'current data loaded'

    def prepare(self, func):
        for feat in self.data:
            func(feat)

    def standardize_countries(self, renamefunc):
        for f in self.data:
            name = f[self.countryfield]
            f[self.countryfield] = renamefunc(name)

    def bugfix(self, fixfunc):
        for feat in self.data:
            fixfunc(feat)

    def modify_country(self, country, modfunc):
        # extract
        countrydata = self.data.select(lambda f: f[self.countryfield]==country)
        # remove
        self.data = self.data.select(lambda f: not f[self.countryfield]==country)
        # mod
        modded = modfunc(countrydata)
        # add
        for f in modded:
            f = self.data.add_feature(f.row, f.geometry)
    

class ChangeData():

    def __init__(self, filename=None, skip=None):
        # Maybe auto download newest
        if not filename:
            filename = "pshapes_raw_auto.csv"
            with open(filename, "wb") as writer:
                print "downloading latest..."
                raw = urllib.urlopen("http://pshapes.org/download/raw/").read()
                writer.write(raw)

        # load event data
        skip = skip or []
        self.data = pg.VectorData(filename, encoding="utf8", sniffsize=20,
                                    select=lambda f: f["status"] != "NonActive" and (f["fromcountry"] not in skip and f["tocountry"] not in skip) )
        
    def ignore_events(self, ignorefunc):
        def wrap(f):
            return not ignorefunc(f)
        self.data = self.data.select(wrap)
        


