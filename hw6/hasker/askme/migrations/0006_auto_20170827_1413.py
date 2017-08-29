# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-27 09:13
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('askme', '0005_question_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='answer',
            name='date',
            field=models.DateField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='answer',
            name='is_correct',
            field=models.BooleanField(default=False),
        ),
    ]