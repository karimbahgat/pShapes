
from django.contrib.gis import admin
from django import forms

from .models import pShapes

##def getbox(c):
##    try:
##        geoj = c.__geo_interface__
##        if geoj["type"] == "Polygon":
##            xs,ys = zip(*(xy for xy in geoj["coordinates"][0]))
##            return min(xs),min(ys),max(xs),max(ys)
##        elif geoj["type"] == "MultiPolygon":
##            xs,ys = zip(*(xy for poly in geoj["coordinates"] for xy in poly[0]))
##            return min(xs),min(ys),max(xs),max(ys)
##    except:
##        return False

class pShapesForm(forms.ModelForm):

    class Meta:
        model = pShapes
        exclude = []
        
    def __init__(self, *args, **kwargs):
        super(pShapesForm, self).__init__(*args, **kwargs)

        # autozoom map to country depending on country
##        import pycountries as pc
##        self.fields['country'].widget.attrs.update({
##            'onchange': "".join(["var cntr = document.getElementById('id_country').value;",
##                                 #"alert(cntr);",
##                                 "var bbox = [0,0,180,90];", #%s[cntr];" % dict([(c.iso3,getbox(c)) for c in pc.all_countries() if getbox(c)]),
##                                 #"alert(bbox);",
##                                 "geodjango_changepart.map.zoomToExtent(bbox);",
##                                ])
##            })

        # TODO: Also alter required status dynamically

##        # hide map widgets on startup
##        self.fields['sourceurl'].widget.attrs.update({"style":"display:none"})
##        self.fields['changepart'].widget.attrs.update({"style":"display:none"}) # grabbing wrong widget so not yet working
##
##        # show/hide map widget depending on changetype
##        self.fields['changetype'].widget.attrs.update({
##            'onchange': "".join(["var changetype = document.getElementById('id_changetype').value;",
##                                "if (changetype == 'PartTransfer') ",
##                                "{",
##                                "document.getElementById('id_changepart_admin_map').style.display = 'block';",
##                                "document.getElementById('id_sourceurl').style.display = 'block';",
##                                "} ",
##                                "else {",
##                                "document.getElementById('id_changepart_admin_map').style.display = 'none';",
##                                "document.getElementById('id_sourceurl').style.display = 'none';",
##                                "};",
##                                ])
##            })

        # make wms auto add/update on sourceurl input
        self.fields['sourceurl'].widget.attrs.update({
            'oninput': "".join(["var wmsurl = document.getElementById('id_sourceurl').value;",
                                "var layerlist = geodjango_changepart.map.getLayersByName('Custom WMS');",
                                "if (layerlist.length >= 1) ",
                                "{",
                                "layerlist[0].url = wmsurl;",
                                "} ",
                                "else {",
                                """customwms = new OpenLayers.Layer.WMS("Custom WMS", wmsurl, {layers: 'basic'} );""",
                                """customwms.isBaseLayer = false;""",
                                """geodjango_changepart.map.addLayer(customwms);""",
                                "};",
                                ])

            # http://mapwarper.net/maps/wms/11512?request=GetMap&version=1.1.1&format=image/png
            #'onclick': """geodjango_changepart.map.layers.sourceurl = new OpenLayers.Layer.WMS("Custom WMS","http://mapwarper.net/maps/wms/11512?request=GetMap&version=1.1.1&format=image/png", {layers: 'basic'} ); geodjango_changepart.map.addLayer(geodjango_changepart.map.layers.sourceurl);"""
            #'onclick': """window.open ("http://www.javascript-coder.com","mywindow","menubar=1,resizable=1,width=350,height=250");"""
            #'onclick': """alert(geodjango_changepart.map)"""
            #'onclick': """alert(Object.getOwnPropertyNames(geodjango_changepart.map))"""
            
        })

class pShapesAdmin(admin.GeoModelAdmin):
    default_zoom = 1
    fieldsets = (
                    (None, {
                        'fields': ('changetype', 'changedate', 'country')
                    }),
                    ('Map', {
                        'classes': ('collapse',),
                        'fields': ('sourceurl', 'changepart'),
                    }),
                    ("From Province", {
                        'fields': tuple('fromname fromiso fromfips fromhasc fromcapital fromtype'.split())
                    }),
                    ("To Province", {
                        'fields': tuple('toname toiso tofips tohasc tocapital totype'.split())
                    }),
                )
    form = pShapesForm

admin.site.register(pShapes, pShapesAdmin)
