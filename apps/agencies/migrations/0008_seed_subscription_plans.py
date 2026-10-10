from django.db import migrations


def seed_plans(apps, schema_editor):
    Plan = apps.get_model('agencies', 'SubscriptionPlan')
    for code, name, amount, cars, branches in [
        ('small', 'Small', 49, 10, 1),
        ('medium', 'Medium', 99, 30, 3),
        ('enterprise', 'Enterprise', 199, 100, 10),
    ]:
        Plan.objects.using(schema_editor.connection.alias).get_or_create(code=code, defaults={
            'name': name, 'monthly_tnd': amount, 'cars': cars, 'branches': branches,
            'description': 'Fleet, rentals, documents and business insights',
            'recommended': code == 'medium',
        })


class Migration(migrations.Migration):
    dependencies = [('agencies', '0007_subscriptionplan')]
    operations = [migrations.RunPython(seed_plans, migrations.RunPython.noop)]
