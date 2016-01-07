
from django.contrib.gis.db import models

class pShapes(models.Model):

    changetype = models.CharField(choices=[("NewInfo","NewInfo"),
                                           ("PartTransfer","PartTransfer"),
                                           ("FullTransfer","FullTransfer"),
                                           ("Breakaway","Breakaway"), 
                                            ],
                                    max_length=40)
    changedate = models.DateField()
    #import pycountries as pc
    country = models.CharField(choices=[("Vietnam","Vietnam"),("Tanzania","Tanzania")], #(c.iso3,c.name) for c in pc.all_countries()],
                                max_length=40)

    # should only show if changetype requires border delimitation...
    sourceurl = models.CharField(max_length=200)
    changepart = models.MultiPolygonField(blank=True)
    
    fromname = models.CharField(max_length=40)
    fromiso = models.CharField(max_length=40)
    fromfips = models.CharField(max_length=40)
    fromhasc = models.CharField(max_length=40)
    fromcapital = models.CharField(max_length=40, blank=True)
    fromtype = models.CharField(choices=[("Province","Province"),
                                         ("Municipality","Municipality"),
                                         ],
                                max_length=40, blank=True)

    toname = models.CharField(max_length=40)
    toiso = models.CharField(max_length=40)
    tofips = models.CharField(max_length=40)
    tohasc = models.CharField(max_length=40)
    tocapital = models.CharField(max_length=40, blank=True)
    totype = models.CharField(choices=[("Province","Province"),
                                         ("Municipality","Municipality"),
                                         ],
                                max_length=40, blank=True)
    