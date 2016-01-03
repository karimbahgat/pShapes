from django.contrib.gis import admin

from .models import pShapes

class pShapesAdmin(admin.GeoModelAdmin):
    fieldsets = (
                    (None, {
                        'fields': ('country', 'date', 'changetype')
                    }),
                    ("From Province", {
                        'fields': tuple('fromname fromiso fromfips fromhasc fromcapital'.split())
                    }),
                    ('Map', {
                        ##'classes': ('collapse',),
                        'fields': ('sourceurl', 'changepart'),
                    }),
                    ("To Province", {
                        'fields': tuple('toname toiso tofips tohasc tocapital'.split())
                    }),
                )

    @property
    def wms_url(self):
        ## "http://mapwarper.net/maps/wms/11512?request=GetMap&version=1.1.1&format=image/png"
        ## print pShapes.cleaned_data['sourceurl']
        print "calling wms_url"
        return "http://mapwarper.net/maps/wms/11512?request=GetMap&version=1.1.1&format=image/png"

        # PROB HAVE TO USE DYNAMIC VIEW.PY INSTEAD WHICH ADDS A WMS SUBMIT BUTTON
        # AND UPDATES MAP UPON RECEIVING IT.

admin.site.register(pShapes, pShapesAdmin)