import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pyshop.settings')
django.setup()

from products.models import County, Town

def run_seed():
    # 1. Define Pricing Zones
    # Format: "County Name": (Base Fee, Estimated Days)
    zones = {
        "Nairobi": (120, 1),
        "Kiambu": (150, 1),
        "Kajiado": (170, 2),
        "Machakos": (170, 2),
        "Mombasa": (250, 3),
        "Kisumu": (250, 3),
        "Nakuru": (200, 2),
        "Uasin Gishu": (220, 2),
        # Remote/Far areas
        "Mandera": (450, 6),
        "Turkana": (450, 5),
        "Marsabit": (400, 5),
        "Wajir": (400, 5),
        "Lamu": (350, 4),
    }

    # 2. Your provided Town Data
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

    print("🚀 Starting Kenyan Logistics Seeding...")

    for county_name, towns in county_town_data.items():
        # Get fee and days for this county. Default to 220 KSh and 3 days if not in zones.
        fee, days = zones.get(county_name, (220, 3))
        
        county, _ = County.objects.get_or_create(name=county_name)
        
        for town_name in towns:
            # We use update_or_create so you can run this script multiple times 
            # to update prices if they change.
            town, created = Town.objects.update_or_create(
                name=town_name,
                county=county,
                defaults={
                    'base_delivery_fee': fee,
                    'estimated_days': days
                }
            )
            
            status = "✅ Added" if created else "🔄 Updated"
            print(f"{status}: {town_name} ({county_name}) - KSh {fee}, {days} days")

    print("\n✨ Seeding Complete! Kenyan Logistics are ready.")

if __name__ == "__main__":
    run_seed()