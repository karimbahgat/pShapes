# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('pshapes', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pshapes',
            name='changepart',
            field=django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326, blank=True),
        ),
        migrations.AlterField(
            model_name='pshapes',
            name='fromcapital',
            field=models.CharField(max_length=40, blank=True),
        ),
        migrations.AlterField(
            model_name='pshapes',
            name='sourceurl',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='pshapes',
            name='tocapital',
            field=models.CharField(max_length=40, blank=True),
        ),
    ]
