# pShapes

Early stages of the pShapes project. Reverse geocoding level 1 provinces backwards in time 
(for now using natural earth). Doing so by identifying mergers, splitters, info changes, and transfers
(in the case of mergers and transfers the spatial extent of the change will have to be identified). 

Statoids is the main source for most changes, and historical maps are for geotransfers. 

Record changes on the pshapes website for maximum reusability with different province datasets, 
process.py will do the backwards change tracking to the final geojson file. 

Karim Bahgat