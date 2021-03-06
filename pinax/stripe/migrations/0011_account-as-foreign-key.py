# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-10-19 12:10
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pinax_stripe', '0010_connect'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customer',
            name='stripe_account',
        ),
        migrations.RemoveField(
            model_name='event',
            name='stripe_account',
        ),
        migrations.RemoveField(
            model_name='plan',
            name='stripe_account'
        ),
        migrations.RemoveField(
            model_name='transfer',
            name='stripe_account',
        ),
        migrations.AddField(
            model_name='customer',
            name='stripe_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pinax_stripe.Account'),
        ),
        migrations.AddField(
            model_name='event',
            name='stripe_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pinax_stripe.Account'),
        ),
        migrations.AddField(
            model_name='plan',
            name='stripe_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pinax_stripe.Account'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='stripe_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pinax_stripe.Account'),
        ),
    ]
