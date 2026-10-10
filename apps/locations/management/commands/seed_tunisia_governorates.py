from django.core.management.base import BaseCommand

from apps.locations.models import Governorate


GOVERNORATES = (
    ("TN-11", "تونس", "Tunis", "Tunis"),
    ("TN-12", "أريانة", "Ariana", "Ariana"),
    ("TN-13", "بن عروس", "Ben Arous", "Ben Arous"),
    ("TN-14", "منوبة", "Manouba", "Manouba"),
    ("TN-21", "نابل", "Nabeul", "Nabeul"),
    ("TN-22", "زغوان", "Zaghouan", "Zaghouan"),
    ("TN-23", "بنزرت", "Bizerte", "Bizerte"),
    ("TN-31", "باجة", "Béja", "Beja"),
    ("TN-32", "جندوبة", "Jendouba", "Jendouba"),
    ("TN-33", "الكاف", "Le Kef", "Kef"),
    ("TN-34", "سليانة", "Siliana", "Siliana"),
    ("TN-41", "القيروان", "Kairouan", "Kairouan"),
    ("TN-42", "القصرين", "Kasserine", "Kasserine"),
    ("TN-43", "سيدي بوزيد", "Sidi Bouzid", "Sidi Bouzid"),
    ("TN-51", "سوسة", "Sousse", "Sousse"),
    ("TN-52", "المنستير", "Monastir", "Monastir"),
    ("TN-53", "المهدية", "Mahdia", "Mahdia"),
    ("TN-61", "صفاقس", "Sfax", "Sfax"),
    ("TN-71", "قفصة", "Gafsa", "Gafsa"),
    ("TN-72", "توزر", "Tozeur", "Tozeur"),
    ("TN-73", "قبلي", "Kébili", "Kebili"),
    ("TN-81", "قابس", "Gabès", "Gabes"),
    ("TN-82", "مدنين", "Médenine", "Medenine"),
    ("TN-83", "تطاوين", "Tataouine", "Tataouine"),
)


class Command(BaseCommand):
    help = "Create or update the 24 Tunisian governorates used by CarRent TN."

    def handle(self, *args, **options):
        for index, (code, name_ar, name_fr, name_en) in enumerate(
            GOVERNORATES,
            start=1,
        ):
            Governorate.objects.update_or_create(
                code=code,
                defaults={
                    "name_ar": name_ar,
                    "name_fr": name_fr,
                    "name_en": name_en,
                    "is_active": True,
                    "display_order": index,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(GOVERNORATES)} Tunisian governorates."
            )
        )
