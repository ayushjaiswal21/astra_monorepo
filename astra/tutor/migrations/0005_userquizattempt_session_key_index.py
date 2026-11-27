# Hand-written (Django not installed in this environment to run makemigrations).
# Adds the missing index on UserQuizAttempt.session_key, which is filtered on
# directly in tutor/views.py:analytics (count + aggregate), matching the
# session_key indexes already present on UserProgress/ModuleProgress/
# CourseTestSession/CourseTestAttempt.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tutor', '0004_coursetestsession_coursetestquestion_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userquizattempt',
            name='session_key',
            field=models.CharField(db_index=True, default='', max_length=40),
        ),
    ]
