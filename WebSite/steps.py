# imports
import sys
import os


# globals
APPNAME = "geodjango_tutorial"
USERNAME = "postgres"


def build():

    # manually create postgis database with same name as project
    # ...but maybe actually do automatically via psycodb2?

    # start project
    from django.core import management
    os.chdir(".")
    sys.argv = [r"C:\Python27\Lib\site-packages\django\bin\django-admin.py","startproject",APPNAME]
    print sys.argv
    #management.execute_from_command_line(sys.argv)
    os.system(" ".join(sys.argv))

    # spec settings (doesnt work cus not using cmd, instead must specify for each call)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "%s.settings" %APPNAME)
    ##print os.environ

    # new application
    os.chdir(APPNAME)
    sys.argv = ["manage.py","startapp", "pshapes", "--settings=%s.settings" %APPNAME]
    print sys.argv
    #os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geodjango.settings")
    #management.execute_from_command_line(sys.argv)
    os.system(" ".join(sys.argv))

    # configure settings incl name and db
    print "config settings"
    with open("%s/settings.py" %APPNAME) as settingsfile:
        settingsraw = settingsfile.read()

    settingsnew = settingsraw.replace("""DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
""",
                                  """DATABASES = {
    'default': {
         'ENGINE': 'django.contrib.gis.db.backends.postgis',
         'NAME': '%s',
         'USER': '%s',
     }
}
    """ % (APPNAME,USERNAME)
                                      )
    # configure settings incl installed apps
    settingsnew = settingsnew.replace("""INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)""",
                                  """INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'pshapes'
)""")

    with open("%s/settings.py" %APPNAME, "w") as settingsfile:
        settingsfile.write(settingsnew)







                                    
    # define data models
    print "define data models"
    modelraw = """
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
    """

    with open("pshapes/models.py", "w") as modelsfile:
        modelsfile.write(modelraw)







    # create data tables in db (makemigration) or manually
    sys.argv = ["manage.py", "flush", "--settings=%s.settings" %APPNAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    sys.argv = ["manage.py", "syncdb", "--settings=%s.settings" %APPNAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    sys.argv = ["manage.py", "makemigrations", "--settings=%s.settings" %APPNAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    sys.argv = ["manage.py", "sqlmigrate", "pshapes", "0001", "--settings=%s.settings" %APPNAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    sys.argv = ["manage.py", "migrate", "--settings=%s.settings" %APPNAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    # if preexisting data

        # load any data into the db table using LayerMapping (load.py) or manually

    # subclass GeoModelAdmin so that user can overlay mapwarper.org maps
    # simply by setting:
    #    wms_url = "http://mapwarper.net/maps/wms/11512?request=GetMap&version=1.1.1&format=image/png"
    # see more details at: http://blog.adamfast.com/



    # NEXT UP IS HERE
    # OR NOT...

    # create addwms form
    ##print "config form.py"
    ##adminraw = """from django.contrib.gis import admin
    ##"""
    ##
    ##with open("pshapes/form.py", "w") as adminfile:
    ##    adminfile.write(adminraw)
    ##
    ### create addwms view rendering the button,
    ### sending it as get request
    ### processing it by taking the url and changing the mapwidget's wms url
    ##print "config view.py"
    ##adminraw = """from django.contrib.gis import admin
    ##"""
    ##
    ##with open("pshapes/view.py", "w") as adminfile:
    ##    adminfile.write(adminraw)

        












    # create basic admin.py for admin stuff
    print "config admin.py"
    adminraw = '''
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
            # http://mapwarper.net/maps/wms/590?request=GetMap&version=1.1.1&format=image/png
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
'''

    with open("pshapes/admin.py", "w") as adminfile:
        adminfile.write(adminraw)












    # CREATE MAP JAVASCRIPT
##    htmlraw = """
##<!DOCTYPE html>
##<html>
##    <head>
##    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
##        <script src="http://openlayers.org/api/OpenLayers.js"></script> 
##    <style>
##        html,body {
##            height: 99%;
##            width: 99%;
##        }
##        #map {
##            width: 100%;
##            height: 100%;
##            border: 1px solid black;
##        }   
##    </style>
##
##    <script type="text/javascript">
##            var map;
##
##            function init(){
##        map = new OpenLayers.Map('map');
##                var base_layer = new OpenLayers.Layer.WMS( "OpenLayers WMS",
##               "http://vmap0.tiles.osgeo.org/wms/vmap0?", {layers: 'basic'} );
##            map.addLayer(base_layer);
##
##        var layer = new OpenLayers.Layer.Vector("layername");
##        map.addLayer(layer);
##
##        map.setCenter(new OpenLayers.LonLat(l_val,L_val),zoom_val);
##        map.addControl(new OpenLayers.Control.LayerSwitcher());
##       }
##        </script>
##    </head>
##    <body onload = "init()">
##    <div id="map"></div>
##    </body>
##</html>
##"""
##    with open("%s/template/map.html" %APPNAME, "w") as mapfile:
##        mapfile.write(htmlraw)
##
##
##
##
##
##
##
##
##    # CREATE MAP VIEW
##    viewraw = """
##from django.html import render
##
##def testmap(request):
##    return render(request, "map.html", {})
##    """
##
##    with open("%s/view.py" %APPNAME, "w") as viewfile:
##        viewfile.write(viewraw)







    # REGISTER URLS
    print "edit urls"
    urlsraw = """
from django.conf.urls import url, include
from django.contrib.gis import admin
##from . import views

urlpatterns = [
                url(r'^admin/', admin.site.urls),
                ##url(r'^$', views.testmap, name='index'),
                ]

"""

    with open("%s/urls.py" %APPNAME, "w") as urlsfile:
        urlsfile.write(urlsraw)








##    # REGISTER WORLD URLS TO SITE URLS
##    urlsraw = """
##url(r'^world/', include("world.urls"))
##    """
##
##    with open("%s/urls.py" %APPNAME, "w") as urlsfile:
##        urlsfile.write(urlsraw)







    # create website superuser
    sys.argv = ["manage.py", "createsuperuser", "--settings=%s.settings" %APPNAME]
    os.system(" ".join(sys.argv))







    # prep for heroku web hosting
    with open("%s/Procfile"%APPNAME, "w") as writer:
        writer.write("web: gunicorn %s.wsgi"%APPNAME)

    with open("%s/requirements.txt"%APPNAME, "w") as writer:
        writer.write("""
Django==1.9
dj-database-url==0.3.0
dj-static==0.0.6
gunicorn==19.1.1
psycopg2==2.5.1
static==0.4
wsgiref==0.1.2
""")





    # append to settings to allow static files
    # ...
        





###########

def run():
    from django.core import management
    os.chdir(".")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "%s.settings" %APPNAME)
    
    # python manage.py runserver
    os.chdir(APPNAME)
    sys.argv = ["manage.py", "runserver", "--settings=%s.settings" %APPNAME,"&pause"]
    #management.execute_from_command_line(sys.argv)
    os.system(" ".join(sys.argv))



if __name__ == "__main__":
    #build()
    run()




