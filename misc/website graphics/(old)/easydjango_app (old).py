# imports
import sys
import os







############

def prereq():
    import pipy
    pipy.install("django-toolbelt")
    pipy.install("psycopg2")
    pipy.install("whitenoise")
    pipy.install("django-leaflet")
    pipy.install("django-geojson")








############

def setup():
    # TODO: maybe switch away from the heroku template,
    # instead manually write procfile, requirements.txt, runtime.txt,
    # DATABASES = dj_database_url()...
    # DATABASES["BACKEND"] = postgresgeodb...
    # also
    # STATIC ADDON
    # also
    # WSGI WITH WHITENOISE...
    # maybe also
    # add static folder
    # ...
    
    sys.argv = [r"C:\Python27\Lib\site-packages\django\bin\django-admin.py",
                "startproject",
                SITENAME,
                "&pause"]
    os.system(" ".join(sys.argv))

    # custom edit some settings
    # maybe also add some basic leaflet settings, incl installing it during setup
    # ...
    with open("%s/%s/settings.py"%(SITENAME,SITENAME), "a") as writer:
        writer.write("""

#### CUSTOMIZATIONS ####

INSTALLED_APPS = list(INSTALLED_APPS)

# geo enable
import dj_database_url
DATABASES['default'] =  dj_database_url.config()
DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'
if "NAME" not in DATABASES['default']:
    DATABASES['default']["NAME"] = os.path.split(BASE_DIR)[-1]
if "USER" not in DATABASES['default']:
    DATABASES['default']["USER"] = "postgres"
INSTALLED_APPS.append('django.contrib.gis')

# add root template
TEMPLATES[0]['DIRS'].append(os.path.join(BASE_DIR, '%s', "templates"))

# add static
STATIC_ROOT = "static"
STATIC_URL = "/static/"
## STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)
STATICFILES_STORAGE = "whitenoise.django.GzipManifestStaticFilesStorage"

# add leaflet
INSTALLED_APPS.append('leaflet')
LEAFLET_CONFIG = {
                'SPATIAL_EXTENT': (-180, -90, 180, 90),
                "TILES": [
                        ('osm', 'http://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {"noWrap":True}),
                        ('light', 'http://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', {"noWrap":True}),
                        ('dark', 'http://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', {"noWrap":True}),
                        ('watercolor', 'http://c.tile.stamen.com/watercolor/{z}/{x}/{y}.png', {"noWrap":True}),
                        ],
                }

""" % SITENAME )

    os.makedirs("%s/%s/templates/%s"%(SITENAME,SITENAME,SITENAME))
    with open("%s/%s/templates/%s/base.html"%(SITENAME,SITENAME,SITENAME), "a") as writer:
        # add default base template with topmenu...
        writer.write("""

<!DOCTYPE html>
<html>

    <head>
        <title>Welcome to the {SITENAME} site</title>
    </head>

    <body>
	<div class="page-header" style="background-color: #ff9400; margin-top: 0; padding: 20px 20px 20px 40px; font-family: comic sans relief;">
    		<h1 style="color:white">
		Welcome to the {SITENAME} site
		</h1>
    		<h2 style="color:white">
		<em>- Some subtitle...</em>
		</h2>
	</div>

	<div class="topmenu" style="background-color: black; font-family: comic sans relief;">
	<a href="/" style="color: white;">Home</a>
        <a href="/admin/" style="color: white;">Admin</a>
	</div>

	<br><br>

	<div class="content">
	{{% block content %}}
	{{% endblock %}}
	</div>

    </body>

</html>

""".format(SITENAME=SITENAME))
    
    os.mkdir("%s/%s/static"%(SITENAME,SITENAME))
    with open("%s/%s/static/dummy.txt"%(SITENAME,SITENAME), "a") as writer:
        pass

    with open("%s/%s/wsgi.py"%(SITENAME,SITENAME), "a") as writer:
        writer.write("""

from whitenoise.django import DjangoWhiteNoise
application = DjangoWhiteNoise(application)

""")

    # create default frontpage
    with open("%s/%s/urls.py"%(SITENAME,SITENAME), "a") as writer:
        writer.write("""
from django.shortcuts import render

def index(request):
    return render(request, '{SITENAME}/base.html')

urlpatterns.append(url('^$', index))

""".format(SITENAME=SITENAME))

    # prep for heroku web hosting
    with open("%s/Procfile"%SITENAME, "w") as writer:
        writer.write("web: gunicorn %s.wsgi"%SITENAME)

    with open("%s/requirements.txt"%SITENAME, "w") as writer:
        writer.write("""
Django==1.9
dj-database-url==0.3.0
dj-static==0.0.6
gunicorn==19.1.1
psycopg2==2.5.1
static==0.4
wsgiref==0.1.2
whitenoise==2.0.6
""")

    with open("%s/runtime.txt"%SITENAME, "w") as writer:
        writer.write("python-%s"%sys.version.split()[0])

    # script for testing site on local server
    with open("%s/testserver.py"%SITENAME, "w") as writer:
        writer.write("""
import sys,os

sys.argv = ["manage.py", "runserver", "&pause"]
os.system(" ".join(sys.argv))
""")





############

def new_db():
    # create the db
    import psycopg2
    print("To create a new database for your project, login as a valid user")
    user = raw_input("username:\n")
    password = raw_input("password:\n")
    con = psycopg2.connect(dbname="postgres",
                           user=user,
                           password=password)
    con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    
    curs = con.cursor()
    curs.execute('CREATE DATABASE %s;' % SITENAME)

    curs.close()
    con.close()

    # add postgis extension
    con = psycopg2.connect(dbname=SITENAME,
                           user=user,
                           password=password)
    con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    
    curs = con.cursor()
    curs.execute('CREATE EXTENSION POSTGIS;')

    curs.close()
    con.close()
    
    # create data tables in db (makemigration) or manually
    sys.argv = ["manage.py", "makemigrations"]#, "--settings=%s.settings" %SITENAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    sys.argv = ["manage.py", "migrate"]#, "--settings=%s.settings" %SITENAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    # create website superuser
    sys.argv = ["manage.py", "createsuperuser"]#, "--settings=%s.settings" %SITENAME]
    os.system(" ".join(sys.argv))





###########

def update_db():
    # create data tables in db (makemigration) or manually
    sys.argv = ["manage.py", "flush"]#, "--settings=%s.settings" %SITENAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    sys.argv = ["manage.py", "makemigrations"]#, "--settings=%s.settings" %SITENAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    sys.argv = ["manage.py", "migrate"]#, "--settings=%s.settings" %SITENAME]
    print sys.argv
    os.system(" ".join(sys.argv)+" &pause")

    # create website superuser
    sys.argv = ["manage.py", "createsuperuser"]#, "--settings=%s.settings" %SITENAME]
    os.system(" ".join(sys.argv))







###########

def new_app(name):
    
    # python manage.py runserver
    sys.argv = ["manage.py", "startapp", name, #"--settings=%s.settings" %SITENAME,
                "&pause"]
    #management.execute_from_command_line(sys.argv)
    os.system(" ".join(sys.argv))

    # add app specific templates
    os.makedirs("%s/templates/%s"%(name,name))
    with open("%s/templates/%s/%s.html"%(name,name,name), "a") as writer:
        writer.write("""
{{% extends '{SITENAME}/base.html' %}}

{{% block content %}}

	<div>
        Insert html or template content here...
        </div>
        
{{% endblock %}}
""".format(SITENAME=SITENAME))

    # add app specific static folder
    os.mkdir("%s/static"%name)
    with open("%s/static/dummy.txt"%name, "a") as writer:
        pass

    # register app to site
    with open("%s/settings.py"%SITENAME, "a") as writer:
        writer.write("""

INSTALLED_APPS.append('%s')

""" % name)
        






###########

def testserver():
    
    # python manage.py runserver
    sys.argv = ["manage.py", "runserver", #"--settings=%s.settings" %SITENAME,
                "&pause"]
    #management.execute_from_command_line(sys.argv)
    os.system(" ".join(sys.argv))





###########

import tk2

class App(object):

    # FOR NOW JUST MANAGING EXISTING SITE

    def __init__(self):

        # settings
        self.SITENAME = os.path.split(__file__)[1]
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "%s.settings" %SITENAME)

        # main
        self.gui = tk2.Tk2()

        # buttons
        self.newappname = tk2.Entry()
        self.newappname.pack(side="left")
        self.newappbut = tk2.Button(text="New App",
                                    command=lambda: new_app(self.newappname.get())
                                    )
        self.newappbut.pack(side="right")

        def sync_serve():
            update_db()
            testserver()            

        self.testbut = tk2.Button(text="Sync db and test server",
                                  command=sync_serve)
        self.testbut.pack()








###########

if __name__ == "__main__":
    App().run()

