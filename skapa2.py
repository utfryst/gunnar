import json
import os
from datetime import datetime

# Definiera mapp för animefiler
anime_folder = 'anime'

# Ladda befintlig indexfil om den finns
index_file_path = 'anime_index.json'
if os.path.exists(index_file_path):
    with open(index_file_path, 'r', encoding='utf-8') as index_file:
        index_data = json.load(index_file)
else:
    index_data = []

# Ladda blacklist-filen om den finns
blacklist_path = 'blacklist.json'
if os.path.exists(blacklist_path):
    with open(blacklist_path, 'r', encoding='utf-8') as blacklist_file:
        blacklist = set(json.load(blacklist_file))
else:
    blacklist = set()

# Skapa en uppsättning med befintliga seriefiler för att undvika dubletter
existing_files = {entry['file'] for entry in index_data}

def extract_date(aired):
    try:
        return datetime.strptime(aired.split(' to ')[0], "%b %d, %Y")
    except (ValueError, IndexError):
        return datetime.min

# Iterera genom alla JSON-filer i anime-mappen
for filename in os.listdir(anime_folder):
    if filename.endswith('.json'):
        file_path = os.path.join(anime_folder, filename)
        file_ref = f'anime/{filename}'
        file_id = filename.replace('.json', '')

        if file_id in blacklist:
            print(f"Svartlistad: {filename} - Hoppar över")
            continue

        if file_ref in existing_files:
            print(f"Hoppar över: {filename} - Redan i indexfilen")
            continue  # Hoppa över om serien redan finns i indexfilen

        with open(file_path, 'r', encoding='utf-8') as file:
            series = json.load(file)
            series_info = series['info']
            series_id = filename.replace('.json', '')
            series_name = series_info.get('name', 'Unknown')
            genres = series.get('moreInfo', {}).get('genres', ['Unknown'])
            poster = series_info.get('poster', 'Unknown')
            aired = series.get('moreInfo', {}).get('aired', 'Unknown')
            status = series.get('moreInfo', {}).get('status', 'Unknown')

            # Lägg till serien i indexfilen
            index_data.append({
                'name': series_name,
                'genres': genres,
                'poster': poster,
                'aired': aired,
                'status': status,
                'file': file_ref
            })
            print(f"Lagt till: {filename} - {series_name}")

# Sortera indexfilen efter datum (senaste först)
index_data.sort(key=lambda x: extract_date(x['aired']), reverse=True)

# Skapa eller uppdatera indexfilen
with open(index_file_path, 'w', encoding='utf-8') as index_file:
    json.dump(index_data, index_file, ensure_ascii=False, indent=4)

print("Indexfilen är uppdaterad och sorterad baserat på datum.")
