import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("onboarding", "0008_assistantconversation_assistantmessage")]
    operations = [
        migrations.CreateModel(
            name="AssistantSiteBuild",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("ready", "Ready")], default="ready", max_length=16)),
                ("category", models.CharField(blank=True, max_length=80)),
                ("business_name", models.CharField(blank=True, max_length=255)),
                ("business_type", models.CharField(max_length=160)),
                ("location", models.CharField(blank=True, max_length=160)),
                ("content", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("conversation", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="site_build", to="onboarding.assistantconversation", verbose_name="Assistant conversation")),
            ],
            options={"ordering": ["-created_at"]},
        )
    ]
