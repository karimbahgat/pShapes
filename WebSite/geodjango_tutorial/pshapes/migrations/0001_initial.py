# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='pShapes',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('changetype', models.CharField(max_length=40, choices=[(b'NewInfo', b'NewInfo'), (b'PartTransfer', b'PartTransfer'), (b'FullTransfer', b'FullTransfer'), (b'Breakaway', b'Breakaway')])),
                ('changedate', models.DateField()),
                ('country', models.CharField(max_length=40, choices=[(b'Vietnam', b'Vietnam'), (b'Tanzania', b'Tanzania')])),
                ('sourceurl', models.CharField(max_length=200)),
                ('changepart', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326, blank=True)),
                ('fromname', models.CharField(max_length=40)),
                ('fromiso', models.CharField(max_length=40)),
                ('fromfips', models.CharField(max_length=40)),
                ('fromhasc', models.CharField(max_length=40)),
                ('fromcapital', models.CharField(max_length=40, blank=True)),
                ('fromtype', models.CharField(blank=True, max_length=40, choices=[(b'Province', b'Province'), (b'Municipality', b'Municipality')])),
                ('toname', models.CharField(max_length=40)),
                ('toiso', models.CharField(max_length=40)),
                ('tofips', models.CharField(max_length=40)),
                ('tohasc', models.CharField(max_length=40)),
                ('tocapital', models.CharField(max_length=40, blank=True)),
                ('totype', models.CharField(blank=True, max_length=40, choices=[(b'Province', b'Province'), (b'Municipality', b'Municipality')])),
            ],
        ),
    ]
