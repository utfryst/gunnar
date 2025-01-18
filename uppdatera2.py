import json
import os
from datetime import datetime
import requests
import time

# Lista på serie-IDs som alltid ska uppdateras
ALWAYS_UPDATE = [
    "100",  # One Piece
]

def parse_air_date(air_date_str):
    if air_date_str == "?" or "," not in air_date_str:
        return None
    
    try:
        first_air_date = air_date_str.split("to")[0].strip()
        return datetime.strptime(first_air_date, "%b %d, %Y")
    except Exception as e:
        print(f"Kunde inte parsa datum: {air_date_str}")
        return None

def make_request_with_retry(url, error_message):
    for attempt in range(15):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data
            print(f"Försök {attempt + 1}: Väntar 2 sekunder...")
            time.sleep(5)
        except Exception as e:
            print(f"Försök {attempt + 1}: {error_message} - {str(e)}")
            time.sleep(5)
    return None

def update_anime_episodes(anime_id, existing_episodes):
    base_url = "http://localhost:4000/api/v2/hianime/anime/"
    episodes_url = f"{base_url}{anime_id}/episodes"
    server_info_url = "http://localhost:4000/api/v2/hianime/episode/servers?animeEpisodeId="
    sources_info_url = "http://localhost:4000/api/v2/hianime/episode/sources?animeEpisodeId="

    # Skapa set med befintliga episodnummer
    existing_episode_numbers = {ep['number'] for ep in existing_episodes}
    
    # Hämta alla tillgängliga episoder från API
    episodes_data = make_request_with_retry(
        episodes_url,
        f"Kunde inte hämta avsnittsdata för: {anime_id}"
    )
    if not episodes_data:
        return None

    new_episodes = []
    for episode in episodes_data['data']['episodes']:
        if episode['number'] in existing_episode_numbers:
            continue

        print(f"Hämtar nytt avsnitt {episode['number']}")
        episode_id = episode['episodeId']

        server_data = make_request_with_retry(
            f"{server_info_url}{episode_id}",
            f"Kunde inte hämta serverdata för avsnitt {episode['number']}"
        )
        if not server_data:
            continue

        episode['servers'] = []
        for server in server_data['data']['sub']:
            server_name = server['serverName']
            sources_url = f"{sources_info_url}{episode_id}&server={server_name}&category=sub"
            
            sources_data = make_request_with_retry(
                sources_url,
                f"Kunde inte hämta streamingdata för server {server_name}"
            )
            if not sources_data or not sources_data['data'].get('sources'):
                continue

            subtitle_track = next((
                track['file'] for track in sources_data['data'].get('tracks', [])
                if track.get('kind') != 'thumbnails' and track.get('label') == 'English'
            ), None)

            episode['servers'].append({
                'serverName': server_name,
                'streamingLink': sources_data['data']['sources'][0]['url'],
                'englishSubtitle': subtitle_track
            })

        new_episodes.append(episode)

    return new_episodes if new_episodes else None

def update_anime(file_path, anime_data):
    try:
        # Hämta bara nya avsnitt
        new_episodes = update_anime_episodes(anime_data['info']['id'], anime_data.get('episodes', []))
        
        if new_episodes:
            # Lägg till nya avsnitt i existerande lista
            anime_data['episodes'].extend(new_episodes)
            # Sortera alla avsnitt efter nummer
            anime_data['episodes'].sort(key=lambda x: x['number'])
            
            # Uppdatera antalet avsnitt i stats
            anime_data['info']['stats']['episodes']['sub'] = len(anime_data['episodes'])
            
            # Spara uppdaterad data
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(anime_data, file, ensure_ascii=False, indent=4)
            print(f"Uppdaterade med {len(new_episodes)} nya avsnitt")
            return True
        else:
            print("Inga nya avsnitt tillgängliga")
            return False
    except Exception as e:
        print(f"Fel vid uppdatering: {e}")
        return False

def check_and_update_recent_anime():
    current_date = datetime.now()
    updated_count = 0
    updated_series = []  # Ny lista för att spåra uppdaterade serier
    
    for filename in os.listdir('anime'):
        if not filename.endswith('.json'):
            continue
            
        file_path = os.path.join('anime', filename)
        try:
            series_id = filename[:-5]
            
            with open(file_path, 'r', encoding='utf-8') as file:
                print(f"\nProcessar {filename}")
                anime_data = json.load(file)
                
                if series_id in ALWAYS_UPDATE:
                    print(f"Uppdaterar {filename} (På always update-listan)")
                    if update_anime(file_path, anime_data):
                        updated_count += 1
                        updated_series.append((anime_data['info']['name'], "Always update"))  # Spara seriens namn och anledning
                    continue
                
                aired = anime_data['moreInfo'].get('aired')
                if not aired or aired == "?":
                    print(f"Skippar {filename} - ingen giltig aired information")
                    continue
                
                air_date = parse_air_date(aired)
                if not air_date:
                    continue
                
                days_since_aired = (current_date - air_date).days
                print(f"Aired datum: {aired}")
                print(f"Dagar sedan aired: {days_since_aired}")
                
                if days_since_aired <= 120:
                    print(f"Uppdaterar {filename} (Började sändas: {aired})")
                    if update_anime(file_path, anime_data):
                        updated_count += 1
                        updated_series.append((anime_data['info']['name'], f"Ny serie ({days_since_aired} dagar)"))  # Spara seriens namn och anledning
                else:
                    print(f"Skippar {filename} - för gammal ({days_since_aired} dagar)")
                
        except Exception as e:
            print(f"Fel vid processning av {filename}: {e}")
            import traceback
            print(traceback.format_exc())
    
    return updated_count, updated_series  # Returnera både antal och lista

if __name__ == "__main__":
    print("Startar uppdatering av nyliga anime-serier...")
    updated_count, updated_series = check_and_update_recent_anime()
    print(f"\nUppdaterade {updated_count} serier framgångsrikt")
    
    if updated_series:
        print("\nUppdaterade följande serier:")
        for name, reason in updated_series:
            print(f"- {name} ({reason})")
    else:
        print("\nInga serier behövde uppdateras")