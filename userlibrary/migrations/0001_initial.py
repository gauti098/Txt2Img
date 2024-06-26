# Generated by Django 3.1.5 on 2021-08-25 21:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FileUpload',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('category', models.CharField(default='upload', max_length=20)),
                ('media_type', models.CharField(max_length=50)),
                ('media_file', models.FileField(upload_to='userlibrary/file/')),
                ('media_thumbnail', models.ImageField(blank=True, upload_to='userlibrary/thumbnail/')),
                ('aiGeneratedVideo', models.IntegerField(blank=True, default=0, null=True)),
                ('isPublic', models.BooleanField(default=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
