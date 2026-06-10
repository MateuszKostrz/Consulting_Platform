from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0239_create_topibtutors_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="past_paper_videos",
            name="markscheme_screenshots_url",
            field=models.TextField(
                blank=True,
                help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)",
                null=True,
            ),
        ),
    ]
