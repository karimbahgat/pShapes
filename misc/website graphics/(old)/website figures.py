
import pythongis as pg

DATAPATH = r'C:\Users\kimok\OneDrive\Documents\GitHub\pshapes\pshapes_natearth.geojson'

# FRONT IMG
##d = pg.VectorData(DATAPATH)
##d = d.select(lambda f: f['start'] <= '1988-01-01' < f['end'])
##
##m = pg.renderer.Map(3000,2000,background=(141,168,198))
##m.add_layer(d, fillcolor=(178,170,159), outlinecolor='gray', outlinewidth=0.3)
##m.add_layer(d.select(lambda f: 's' in f['Name']), fillcolor=(62,95,146), outlinecolor='white',
##            outlinewidth=0.3)
##m.zoom_bbox(*d.bbox)
##m.zoom_in(3.5)
##m.render_all(antialias=True)
##import pyagg
##m.drawer.paste(pyagg.load('pencil-190586_640.png').resize(1000,1000), xy=('105%w','-5%h'), anchor='ne')
##m.drawer.save('webfrontimg.png')
##
### DOWNLOAD IMG
##d = pg.VectorData(DATAPATH)
##d = d.select(lambda f: f['start'] <= '1999-01-01' < f['end'])
##
##countries = pg.VectorData(r"C:\Users\kimok\Downloads\natearth\ne_110m_admin_0_countries.shp",
##                          select=lambda f: f['GEOUNIT']!='Antarctica')
##countries.crs = d.crs
##
##m = pg.renderer.Map(2000,1000,background='white')
##m.add_layer(countries.manage.reproject('+proj=robin'), fillcolor=(192,192,192), outlinecolor='white', outlinewidth=0.05)
##provlyr = m.add_layer(d.manage.reproject('+proj=robin'), fillcolor=(62,95,146), outlinecolor='white', outlinewidth=0.05)
###provlyr.add_effect('glow', color=[(62,95,146,255),(255,255,255,0)], size=20)
##m.zoom_auto()
##m.zoom_in(1.07)
##m.offset(-36*2, 0)
##m.save('webdownloadimg.png')

# DOWNLOAD IMG 2
d = pg.VectorData(DATAPATH)
d = d.select(lambda f: f['start'] <= '1988-01-01' < f['end'])

m = pg.renderer.Map(3000,2000,background=(141,168,198))
m.add_layer(d, fillcolor=(178,170,159), outlinecolor='gray', outlinewidth=0.3)
m.add_layer(d.select(lambda f: 's' in f['name']), fillcolor=(62,95,146), outlinecolor='white',
            outlinewidth=0.3)
#m.zoom_bbox(*d.bbox)
m.offset(12,64)
m.zoom_in(20)
m.render_all(antialias=True)
import pyagg
m.drawer.paste(pyagg.load('handclick.png').resize(1200,1200), xy=('105%w','80%h'), anchor='se')
m.drawer.save('webdownloadimg.png')

# SPLIT
##d = pg.VectorData('../processed.geojson')
##before = d.select(lambda f: f['start'] <= '1980-01-01' < f['end'] and f['Name']=='Upper')
##after = d.select(lambda f: f['start'] <= '2002-01-01' < f['end'] and 'pper' in f['Name'])
##
##lyt = pg.renderer.Layout(2000,1000, background=None)
##m = pg.renderer.Map(1000,1000)
##m.add_layer(before, fillcolor=(62,95,146), outlinecolor=(62-40,95-40,146-40), outlinewidth=1)
##m.zoom_auto()
##lyt.add_map(m)
##m = pg.renderer.Map(1000,1000)
##m.add_layer(after, fillcolor=dict(breaks='unique',key=lambda f: f['Name']), outlinecolor=(62-40,95-40,146-40), outlinewidth=1)
##m.zoom_auto()
##lyt.add_map(m)
##lyt.save('websplit.png')

# MERGE
##d = pg.VectorData('../processed.geojson')
##after = d.select(lambda f: f['start'] <= '2002-01-01' < f['end'] and 'Nzer' in f['Name'])
##before = d.select(lambda f: f['start'] <= '1988-01-01' < f['end']).manage.where(after.manage.buffer(-0.1), 'intersects')
##
##lyt = pg.renderer.Layout(2000,1000, background=None)
##m = pg.renderer.Map(1000,1000)
##m.add_layer(before, fillcolor=dict(breaks='unique',key=lambda f: f['Name']), outlinecolor=(62-40,95-40,146-40), outlinewidth=1)
##m.zoom_auto()
##lyt.add_map(m)
##m = pg.renderer.Map(1000,1000)
##m.add_layer(after, fillcolor=(62,95,146), outlinecolor=(62-40,95-40,146-40), outlinewidth=1)
##m.zoom_auto()
##lyt.add_map(m)
##lyt.save('webmerge.png')

# TRANSFER
##d = pg.VectorData('../processed.geojson')
##after = d.select(lambda f: f['start'] <= '1997-01-01' < f['end'] and f['country']=='Burkina Faso' and ('dougou' in f['Name'] or 'ouet' in f['Name']) )
##before = d.select(lambda f: f['start'] <= '1991-01-01' < f['end'] and f['country']=='Burkina Faso' and ('dougou' in f['Name'] or 'ouet' in f['Name']) )
##
##lyt = pg.renderer.Layout(2000,1000, background=None)
##m = pg.renderer.Map(1000,1000)
##m.add_layer(before, fillcolor=dict(breaks='unique',key=lambda f: f['Name'], colors=[(62,95,146),'yellow']), outlinecolor=(62-40,95-40,146-40), outlinewidth=1)
##m.zoom_auto()
##lyt.add_map(m)
##m = pg.renderer.Map(1000,1000)
##m.add_layer(after, fillcolor=dict(breaks='unique',key=lambda f: f['Name'], colors=[(62,95,146),'yellow']), outlinecolor=(62-40,95-40,146-40), outlinewidth=1)
##m.zoom_auto()
##lyt.add_map(m)
##lyt.save('webtransfer.png')

# NEWINFO
##d = pg.VectorData('../processed.geojson')
##after = d.select(lambda f: f['start'] <= '1991-01-01' < f['end'] and 'Komoe' in f['Name'] )
##before = after
##
##lyt = pg.renderer.Layout(2000,1000, background=None)
##m = pg.renderer.Map(1000,1000)
##m.add_layer(before, fillcolor=dict(breaks='unique',key=lambda f: f['Name']), outlinecolor=(62-40,95-40,146-40), outlinewidth=1)
##m.zoom_auto()
##lyt.add_map(m)
##m = pg.renderer.Map(1000,1000)
##m.add_layer(after, fillcolor=dict(breaks='unique',key=lambda f: f['Name'], colors=[(62,95,146)]), outlinecolor=(62-40,95-40,146-40), outlinewidth=1)
##m.zoom_auto()
##lyt.add_map(m)
##lyt.save('webnewinfo.png')

# BEGIN
##d = pg.VectorData('../processed.geojson')
##after = d.select(lambda f: f['start'] <= '2001-01-01' < f['end'] and 'Ekiti' in f['Name'] )
##
##lyt = pg.renderer.Layout(2000,1000, background=None)
##m = pg.renderer.Map(1000,1000)
##lyt.add_map(m)
##m = pg.renderer.Map(1000,1000)
##m.add_layer(after, fillcolor=(62,95,146), outlinecolor=(62-40,95-40,146-40), outlinewidth=1)
##m.zoom_auto()
##lyt.add_map(m)
##lyt.save('webbegin.png')

