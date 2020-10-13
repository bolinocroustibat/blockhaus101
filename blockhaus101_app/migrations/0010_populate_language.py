from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blockhaus101_app", "0009_auto_20200313_1127"),
    ]

    operations = [
        migrations.RunSQL("INSERT INTO `language` (`language`) VALUES ('fr')"),
        migrations.RunSQL("INSERT INTO `language` (`language`) VALUES ('en')"),
    ]
