# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-02 04:49
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('askme', '0013_uservote_rel_null'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='answeruservote',
            name='answer',
        ),
        migrations.RemoveField(
            model_name='answeruservote',
            name='user',
        ),
        migrations.DeleteModel(
            name='AnswerUserVote',
        ),
    ]