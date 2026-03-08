import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pyshop.settings')
django.setup()

from products.models import County, Town

# List of (County, Town) pairs
data = [
    ("Nairobi", "Nairobi City"), ("Mombasa", "Mombasa"), ("Kisumu", "Kisumu"),
    ("Nakuru", "Nakuru"), ("Nakuru", "Naivasha"), ("Kiambu", "Thika"),
    ("Kiambu", "Kikuyu"), ("Kirinyaga", "Kerugoya"), ("Kirinyaga", "Kutus"),
    ("Kirinyaga", "Baricho"), ("Uasin Gishu", "Eldoret"), ("Kakamega", "Kakamega"),
    ("Machakos", "Machakos Town"), ("Machakos", "Athi River"), ("Kisii", "Kisii"),
    ("Bungoma", "Bungoma"), ("Bungoma", "Webuye"), ("Kericho", "Kericho"),
    ("Nyeri", "Nyeri"), ("Embu", "Embu"), ("Meru", "Meru"), ("Busia", "Busia"),
    ("Narok", "Narok"), ("Kajiado", "Kitengela"), ("Kajiado", "Ngong"), ("Meru", "Maua")
]


def run_seed():
    print("Starting data seeding...")
    for county_name, town_name in data:
        county, _ = County.objects.get_or_create(name=county_name)
        town, created = Town.objects.get_or_create(name=town_name, county=county)

        if created:
            print(f"✅ Added: {town_name} in {county_name}")
        else:
            print(f"ℹ️  Skipped: {town_name} already exists")


if __name__ == "__main__":
    run_seed()