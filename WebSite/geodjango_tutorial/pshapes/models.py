from django.contrib.gis.db import models

import pycountries as pc

class pShapes(models.Model):

    country = models.CharField(choices=[(c.iso3,c.name) for c in pc.all_countries()],
                                max_length=40)
    date = models.DateField()
    changetype = models.CharField(choices=[("InfoChange","InfoChange"),
                                           ("PartTransfer","PartTransfer"),
                                           ("FullTransfer","FullTransfer"), 
                                            ],
                                    max_length=40)

    # should only show if changetype requires border delimitation...
    sourceurl = models.CharField(max_length=40)
    changepart = models.MultiPolygonField()
    
    fromname = models.CharField(max_length=40)
    fromiso = models.CharField(max_length=40)
    fromfips = models.CharField(max_length=40)
    fromhasc = models.CharField(max_length=40)
    fromcapital = models.CharField(max_length=40)

    toname = models.CharField(max_length=40)
    toiso = models.CharField(max_length=40)
    tofips = models.CharField(max_length=40)
    tohasc = models.CharField(max_length=40)
    tocapital = models.CharField(max_length=40)
    
        
