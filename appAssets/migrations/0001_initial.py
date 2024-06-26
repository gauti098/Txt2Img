# Generated by Django 3.1.5 on 2021-08-25 20:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AvatarImages',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('gender', models.IntegerField(choices=[(1, 'Male'), (2, 'Female')], default=1)),
                ('img', models.ImageField(blank=True, null=True, upload_to='avatars/image/')),
                ('largeImg', models.ImageField(blank=True, null=True, upload_to='avatars/image/')),
                ('transparentImage', models.ImageField(blank=True, null=True, upload_to='avatars/image/')),
                ('avatarConfig', models.CharField(blank=True, max_length=10000, null=True)),
                ('faceSwapPositionX', models.IntegerField(default=0)),
                ('faceSwapPositionY', models.IntegerField(default=0)),
                ('faceSwapAnchorPointX', models.IntegerField(default=0)),
                ('faceSwapAnchorPointY', models.IntegerField(default=0)),
                ('faceSwapScale', models.FloatField(default=0)),
                ('totalFrames', models.IntegerField(default=0)),
                ('height', models.IntegerField(default=0)),
                ('width', models.IntegerField(default=0)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='AvatarSounds',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('gender', models.IntegerField(choices=[(1, 'Male'), (2, 'Female')], default=1)),
                ('provider', models.CharField(max_length=50)),
                ('provider_id', models.CharField(max_length=200)),
                ('samples', models.FileField(upload_to='avatar_sounds/')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='AvatarSoundCombination',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video', models.FileField(upload_to='avatarCombination/')),
                ('sound', models.FileField(upload_to='avatarCombination/')),
                ('image', models.FileField(blank=True, null=True, upload_to='avatarCombination/')),
                ('previewVideo', models.FileField(blank=True, null=True, upload_to='avatarCombination/')),
                ('avatarImg', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='appAssets.avatarimages')),
                ('avatarSound', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='appAssets.avatarsounds')),
            ],
            options={
                'unique_together': {('avatarImg', 'avatarSound')},
            },
        ),
    ]
