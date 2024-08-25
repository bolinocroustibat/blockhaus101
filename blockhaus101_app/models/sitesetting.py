from django.db import models

from base_data_app.models.language import Language


class SiteSetting(models.Model):
    language = models.ForeignKey(Language, related_name="languages", on_delete=models.PROTECT)
    description = models.TextField("site header text", max_length=1000, default="")
    period = models.IntegerField("period between two exhibitions, in days", default=7)

    gpt_reformulate_system_prompt = models.TextField(
        "GPT systemt prompt for re-formulation", max_length=1000, default=""
    )
    gpt_reformulate_user_prompt = models.TextField(
        "GPT prompt for re-formulation", max_length=10000, default=""
    )

    img_gen_system_prompt = models.TextField(
        "Image generation system prompt", max_length=1000, default=""
    )
    img_gen_user_prompt = models.TextField(
        "Image generation user prompt", max_length=10000, default=""
    )

    class Meta:
        db_table = "blockhaus101_settings"
        verbose_name = "General setting"

    def __str__(self) -> str:
        return "Settings {}".format(self.language)
