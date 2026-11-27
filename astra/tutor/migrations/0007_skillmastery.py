# Hand-written (Django not installed in this environment to run makemigrations).
# Adds the new SkillMastery model only -- does not touch Course/created_by or
# any other model from 0006.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tutor', '0006_course_created_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='SkillMastery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(db_index=True, max_length=40)),
                ('skill_name', models.CharField(max_length=200)),
                ('score', models.FloatField(default=0.5)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'unique_together': {('session_key', 'skill_name')},
            },
        ),
    ]
