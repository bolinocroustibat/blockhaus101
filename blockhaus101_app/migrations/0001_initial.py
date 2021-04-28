from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Artist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, verbose_name="Nom de l'artiste")),
                ('gender', models.CharField(choices=[('f', 'female'), ('m', 'male')], max_length=6, verbose_name="Genre de l'artiste")),
                ('discipline', models.CharField(max_length=80, verbose_name="Discipline de l'artiste")),
                ('bio', models.TextField(max_length=2000, verbose_name="Biographie de l'artiste")),
                ('created', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Exhibition',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=80, verbose_name="Titre de l'exposition")),
                ('startdate', models.DateTimeField(blank=True, null=True, verbose_name="Date de début d'exposition")),
                ('enddate', models.DateTimeField(blank=True, null=True, verbose_name="Date de fin d'exposition")),
                ('created', models.DateTimeField(auto_now=True)),
                ('artist', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='artist_exhibition', to='blockhaus101_app.Artist')),
            ],
        ),
        migrations.CreateModel(
            name='ExpoText',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(max_length=3000, verbose_name="Texte de l'exposition")),
                ('slug', models.SlugField(blank=True, default=None, max_length=150, null=True, verbose_name='URL')),
                ('created', models.DateTimeField(auto_now=True)),
                ('exhibition', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='exhibition_expotext', to='blockhaus101_app.Exhibition', verbose_name='Exposition')),
            ],
        ),
    ]
