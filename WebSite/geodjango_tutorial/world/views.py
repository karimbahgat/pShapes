from django.shortcuts import render, redirect
from vectorformats.Formats import Django, GeoJSON

#from .models import MyLayer

def testmap(request):
    return render(request, "map.html", {})
