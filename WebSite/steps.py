# imports
import sys
import os

# globals
APPNAME = "geodjango_tutorial"
USERNAME = "postgres"

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
sys.argv = ["manage.py","startapp", "world", "--settings=%s.settings" %APPNAME]
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
    'world'
)""")

with open("%s/settings.py" %APPNAME, "w") as settingsfile:
    settingsfile.write(settingsnew)
                                  
# define data models
print "define data models"
modelraw = """from django.contrib.gis.db import models

class WorldBorder(models.Model):
    # Regular Django fields corresponding to the attributes in the
    # world borders shapefile.
    name = models.CharField(max_length=50)
    area = models.IntegerField()
    pop2005 = models.IntegerField('Population 2005')
    fips = models.CharField('FIPS Code', max_length=2)
    iso2 = models.CharField('2 Digit ISO', max_length=2)
    iso3 = models.CharField('3 Digit ISO', max_length=3)
    un = models.IntegerField('United Nations Code')
    region = models.IntegerField('Region Code')
    subregion = models.IntegerField('Sub-Region Code')
    lon = models.FloatField()
    lat = models.FloatField()

    # GeoDjango-specific: a geometry field (MultiPolygonField)
    mpoly = models.MultiPolygonField()

    # Returns the string representation of the model.
    def __str__(self):              # __unicode__ on Python 2
        return self.name
        """

with open("world/models.py", "w") as modelsfile:
    modelsfile.write(modelraw)


# create data tables in db (makemigration) or manually
sys.argv = ["manage.py", "makemigrations", "--settings=%s.settings" %APPNAME]
print sys.argv
os.system(" ".join(sys.argv)+" &pause")

sys.argv = ["manage.py", "sqlmigrate", "world", "0001", "--settings=%s.settings" %APPNAME]
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

# create basic admin.py for admin stuff
print "config admin.py"
adminraw = """from django.contrib.gis import admin
from models import WorldBorder

admin.site.register(WorldBorder, admin.GeoModelAdmin)"""

with open("world/admin.py", "w") as adminfile:
    adminfile.write(adminraw)

# edit urls.py
print "edit urls"
urlsraw = """from django.conf.urls import url, include
from django.contrib.gis import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
]"""

with open("%s/urls.py" %APPNAME, "w") as urlsfile:
    urlsfile.write(urlsraw)

# create website superuser
sys.argv = ["manage.py", "createsuperuser", "--settings=%s.settings" %APPNAME]
os.system(" ".join(sys.argv))

############

"""
CREATE MAP JAVASCRIPT
world/template/map.html

<!DOCTYPE html>
<html>
    <head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
        <script src="http://openlayers.org/api/OpenLayers.js"></script> 
    <style>
        html,body {
            height: 99%;
            width: 99%;
        }
        #map {
            width: 100%;
            height: 100%;
            border: 1px solid black;
        }   
    </style>

    <script type="text/javascript">
            var map;

            function init(){
        map = new OpenLayers.Map('map');
                var base_layer = new OpenLayers.Layer.WMS( "OpenLayers WMS",
               "http://vmap0.tiles.osgeo.org/wms/vmap0?", {layers: 'basic'} );
            map.addLayer(base_layer);

        var layer = new OpenLayers.Layer.Vector("layername");
        map.addLayer(layer);

        map.setCenter(new OpenLayers.LonLat(l_val,L_val),zoom_val);
        map.addControl(new OpenLayers.Control.LayerSwitcher());
       }
        </script>
    </head>
    <body onload = "init()">
    <div id="map"></div>
    </body>
</html>

CREATE MAP VIEW
view.py
def testmap(request):
    return render(request, "map.html", {})

REGISTER VIEWS TO WORLD URLS
world/urls.py

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.testmap, name='index'),
]

REGISTER WORLD URLS TO SITE URLS
geodjange_tutorial/urls.py
url(r'^world/', include("world.urls"))
"""

###########

# python manage.py runserver
sys.argv = ["manage.py", "runserver", "--settings=%s.settings" %APPNAME]
#management.execute_from_command_line(sys.argv)
os.system(" ".join(sys.argv))
