# Hand-written (Django not installed in this environment to run makemigrations).
# Adds Course.created_by, a nullable FK to the real Django auth User, now that
# tutor/views.py records ownership on create_course and enforces it on
# delete_course. Nullable so existing/anonymously-created courses are left
# untouched (created_by=NULL) by this migration.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tutor', '0005_userquizattempt_session_key_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='courses', to=settings.AUTH_USER_MODEL),
        ),
    ]
