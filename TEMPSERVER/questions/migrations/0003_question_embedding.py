from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0002_question_is_vectorized_question_vector_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='question',
            name='vector_id',
        ),
        migrations.AddField(
            model_name='question',
            name='embedding',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
