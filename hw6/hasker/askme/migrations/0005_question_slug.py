# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-26 18:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('askme', '0004_auto_20170820_1413'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='slug',
            field=models.SlugField(default=None, unique=True),
            preserve_default=False,
        ),
    ]
