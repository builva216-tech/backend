from django.db import models


class Governorate(models.Model):
    code = models.CharField(max_length=5, primary_key=True)
    name_ar = models.CharField(max_length=80)
    name_fr = models.CharField(max_length=80)
    name_en = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "code")

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.code} — {self.name_en}"
