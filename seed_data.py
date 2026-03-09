import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pyshop.settings')
django.setup()

from products.models import County, Town

# List of (County, [Towns]) pairs - All 47 Kenyan Counties with major towns
county_town_data = {
    "Mombasa": ["Mombasa", "Kilifi", "Malindi", "Lamu", "Kwale"],
    "Kwale": ["Kwale", "Msambweni", "Lungalunga", "Matuga"],
    "Kilifi": ["Kilifi", "Malindi", "Kaloleni", "Rabai", "Ganze"],
    "Tana River": ["Hola", "Garsen", "Bura"],
    "Lamu": ["Lamu", "Mokowe"],
    "Taita-Taveta": ["Voi", "Taveta", "Wundanyi", "Mwatate"],
    "Garissa": ["Garissa", "Ijara", "Dadaab", "Fafi"],
    "Wajir": ["Wajir", "Moyale", "Habaswein", "Griftu"],
    "Mandera": ["Mandera", "Elwak", "Takaba", "Lafey"],
    "Marsabit": ["Marsabit", "Moyale", "Sololo", "Laisamis"],
    "Isiolo": ["Isiolo", "Moyale", "Merti"],
    "Meru": ["Meru", "Maua", "Nkubu", "Chuka", "Igembe"],
    "Tharaka-Nithi": ["Chuka", "Maua", "Tharaka"],
    "Embu": ["Embu", "Runyenjes", "Manyatta"],
    "Kitui": ["Kitui", "Mwingi", "Mutomo", "Ikutha"],
    "Machakos": ["Machakos", "Athi River", "Kangundo", "Tala"],
    "Makueni": ["Wote", "Makueni", "Kibwezi", "Makindu"],
    "Nyandarua": ["Ol Kalou", "Ndaragwa", "Engineer", "Nyahururu"],
    "Nyeri": ["Nyeri", "Othaya", "Chinga", "Karatina"],
    "Kirinyaga": ["Kerugoya", "Kutus", "Wanguru", "Sagana"],
    "Murang'a": ["Murang'a", "Kangema", "Kiharu", "Maragua"],
    "Kiambu": ["Kiambu", "Thika", "Limuru", "Ruiru", "Kikuyu"],
    "Turkana": ["Lodwar", "Kakuma", "Lokichoggio", "Lokitaung"],
    "West Pokot": ["Kapenguria", "Sigor", "Ortum"],
    "Samburu": ["Maralal", "Baragoi", "Wamba"],
    "Trans Nzoia": ["Kitale", "Kiminini", "Endebess"],
    "Uasin Gishu": ["Eldoret", "Turbo", "Moiben", "Soy"],
    "Elgeyo-Marakwet": ["Iten", "Kapsowar", "Marakwet"],
    "Nandi": ["Kapsabet", "Mosoriot", "Nandi Hills"],
    "Baringo": ["Kabarnet", "Eldama Ravine", "Marigat"],
    "Laikipia": ["Nanyuki", "Rumuruti", "Dol Dol"],
    "Nakuru": ["Nakuru", "Naivasha", "Gilgil", "Molo", "Njoro"],
    "Narok": ["Narok", "Kilgoris", "Ololulunga"],
    "Kajiado": ["Kajiado", "Kitengela", "Ngong", "Ongata Rongai"],
    "Kericho": ["Kericho", "Litein", "Kipkelion"],
    "Bomet": ["Bomet", "Sotik", "Chepalungu"],
    "Kakamega": ["Kakamega", "Mumias", "Lugari", "Butere"],
    "Vihiga": ["Vihiga", "Hamisi", "Luanda"],
    "Bungoma": ["Bungoma", "Webuye", "Malakisi", "Sirisia"],
    "Busia": ["Busia", "Malaba", "Port Victoria"],
    "Siaya": ["Siaya", "Bondo", "Ugunja", "Ukwala"],
    "Kisumu": ["Kisumu", "Kisumu Ndogo", "Ahero", "Muhoroni"],
    "Homa Bay": ["Homa Bay", "Ndhiwa", "Mbita", "Rachuonyo"],
    "Migori": ["Migori", "Awendo", "Rongo", "Uriri"],
    "Kisii": ["Kisii", "Ogembo", "Nyamache", "Masimba"],
    "Nyamira": ["Nyamira", "Keroka", "Manga"],
    "Nairobi": ["Nairobi", "Westlands", "Karen", "Kilimani", "Langata", "Parklands", "River Road", "CBD"]
}

# Convert to list of (county, town) pairs
data = []
for county, towns in county_town_data.items():
    for town in towns:
        data.append((county, town))


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