from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_user_profile_picture_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to='profile_pictures/'),
        ),
    ]
