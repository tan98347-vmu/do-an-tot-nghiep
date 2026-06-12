from django.db import migrations, models


# class Migration là bước migration thay đổi cấu trúc CSDL (theo tên file: chatsession assistant state).
# vd: chạy "python manage.py migrate" để áp dụng thay đổi schema này vào database.
class Migration(migrations.Migration):

    dependencies = [
        ('ai_engine', '0008_alter_chatsession_options'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE ai_engine_chatsession "
                        "ADD COLUMN IF NOT EXISTS assistant_state jsonb; "
                        "UPDATE ai_engine_chatsession "
                        "SET assistant_state = '{}'::jsonb "
                        "WHERE assistant_state IS NULL; "
                        "ALTER TABLE ai_engine_chatsession "
                        "ALTER COLUMN assistant_state SET DEFAULT '{}'::jsonb; "
                        "ALTER TABLE ai_engine_chatsession "
                        "ALTER COLUMN assistant_state SET NOT NULL;"
                    ),
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='chatsession',
                    name='assistant_state',
                    field=models.JSONField(blank=True, default=dict),
                ),
            ],
        ),
    ]
