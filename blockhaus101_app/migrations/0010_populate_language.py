from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blockhaus101_app", "0008_language"),
    ]

    operations = [
        migrations.RunSQL("INSERT INTO `language` (`language`) VALUES ('fr')"),
        migrations.RunSQL("INSERT INTO `language` (`language`) VALUES ('en')"),
    ]
