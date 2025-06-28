import os
import json
from pathlib import Path
from typing import List, Dict, Any
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import hashlib
import unicodedata

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  
SUPABASE_BUCKET = "albums"  
SUPABASE_FOLDER = "SOUR"  
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Replace this with the appropriate URL for your album
ALBUM_ART_URL = "https://lgnvhovprubrxohnhwph.supabase.co/storage/v1/object/public/picture/Album/SOUR.jpg"  

def get_file_hash(file_path: str) -> str:
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read(65536)  
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def sanitize_filename(filename: str) -> str:
    """
    "
    Generate a safe filename by:
    - Converting Vietnamese characters to ASCII
    - Removing special characters
    - Replacing spaces with hyphens
    """
    # Convert Vietnamese characters to ASCII
    normalized = unicodedata.normalize('NFKD', filename)
    ascii_name = ''
    for char in normalized:
        if unicodedata.category(char) != 'Mn':  
            if char.isalpha():
                if char in 'àáạảãâầấậẩẫăằắặẳẵ':
                    ascii_name += 'a'
                elif char in 'èéẹẻẽêềếệểễ':
                    ascii_name += 'e'
                elif char in 'ìíịỉĩ':
                    ascii_name += 'i'
                elif char in 'òóọỏõôồốộổỗơờớợởỡ':
                    ascii_name += 'o'
                elif char in 'ùúụủũưừứựửữ':
                    ascii_name += 'u'
                elif char in 'ỳýỵỷỹ':
                    ascii_name += 'y'
                elif char in 'đ':
                    ascii_name += 'd'
                elif char in 'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ':
                    ascii_name += 'A'
                elif char in 'ÈÉẸẺẼÊỀẾỆỂỄ':
                    ascii_name += 'E'
                elif char in 'ÌÍỊỈĨ':
                    ascii_name += 'I'
                elif char in 'ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ':
                    ascii_name += 'O'
                elif char in 'ÙÚỤỦŨƯỪỨỰỬỮ':
                    ascii_name += 'U'
                elif char in 'ỲÝỴỶỸ':
                    ascii_name += 'Y'
                elif char in 'Đ':
                    ascii_name += 'D'
                else:
                    ascii_name += char
            else:
                ascii_name += char
    
    safe_name = "".join(c for c in ascii_name if c.isalnum() or c in (' ', '-', '_', '.'))
    
    # Replace spaces with hyphens
    safe_name = safe_name.replace(' ', '-')
    
    while '--' in safe_name:
        safe_name = safe_name.replace('--', '-')
    
    safe_name = safe_name.strip('-')
    
    return safe_name

def upload_to_storage(file_path: str) -> str:
    """
    Upload the file to Supabase Storage and return the public URL.
    Generates a safe filename from the original file name.
    """
    try:
        original_name = Path(file_path).name
        safe_name = sanitize_filename(original_name)
        #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{SUPABASE_FOLDER}/{safe_name}"  
        
        # Upload file
        with open(file_path, 'rb') as f:
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                file_name,
                f.read(),
                {"content-type": "audio/mpeg"}
            )
        
        # Get URL public 
        file_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_name)
        file_url = file_url.rstrip('?')
        if not file_url.startswith('https://'):
            file_url = 'https://' + file_url.lstrip('http://')
        
        print(f"Uploaded: {file_path} -> {file_url}")
        return file_url
        
    except Exception as e:
        print(f"Error uploading {file_path}: {str(e)}")
        return None

def upload_picture(picture_path: str, song_name: str) -> str:
    """
     Upload album artwork to Supabase Storage.
    Generate a safe filename from the song title.
    """
    try:
        # Generate a safe filename from the song title
        safe_song_name = sanitize_filename(song_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{safe_song_name}_{timestamp}.jpg"
        
        # Upload file
        with open(picture_path, 'rb') as f:
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                file_name,
                f.read(),
                {"content-type": "image/jpeg"}
            )
        
        file_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_name)
        file_url = file_url.rstrip('?')
        if not file_url.startswith('https://'):
            file_url = 'https://' + file_url.lstrip('http://')
        
        print(f"Uploaded album art: {picture_path} -> {file_url}")
        return file_url
        
    except Exception as e:
        print(f"Error uploading album art {picture_path}: {str(e)}")
        return None

def get_next_singer_id() -> int:
   
    try:
        # Get the artist with the highest ID
        result = supabase.table("singer").select("id_singer").order("id_singer", desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]["id_singer"] + 1
        return 1
    except Exception as e:
        print(f"Error getting next singer ID: {str(e)}")
        return 1

def get_next_song_id() -> int:
   
    try:
        #  Get the song with the highest ID
        result = supabase.table("songs").select("id_song").order("id_song", desc=True).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]["id_song"] + 1
        return 1
    except Exception as e:
        print(f"Error getting next song ID: {str(e)}")
        return 1

def get_audio_metadata(file_path: str) -> Dict[str, Any]:
    """
     Extract metadata from the music file
    """
    try:
        audio = mutagen.File(file_path)
        if audio is None:
            return None

        # Get basic information
        duration = int(audio.info.length) if hasattr(audio.info, 'length') else 0
        
        # Get ID3 tags if available
        tags = {}
        if hasattr(audio, 'tags') and audio.tags:
            if isinstance(audio.tags, ID3):
                # MP3 with ID3 tags
                tags = {
                    'title': str(audio.tags.get('TIT2', [''])[0]) if 'TIT2' in audio.tags else '',
                    'artist': str(audio.tags.get('TPE1', [''])[0]) if 'TPE1' in audio.tags else '',
                    'album': str(audio.tags.get('TALB', [''])[0]) if 'TALB' in audio.tags else '',
                    'genre': str(audio.tags.get('TCON', [''])[0]) if 'TCON' in audio.tags else '',
                    'picture': None
                }
                
                # Extract album cover if available
                if 'APIC:' in audio.tags:
                    picture = audio.tags['APIC:'].data
                    #Save image to the pictures directory
                    picture_dir = Path('pictures')
                    picture_dir.mkdir(exist_ok=True)
                    picture_path = picture_dir / f"{Path(file_path).stem}.jpg"
                    with open(picture_path, 'wb') as f:
                        f.write(picture)
                    tags['picture'] = str(picture_path)
            else:
                # Other audio formats
                tags = {
                    'title': str(audio.tags.get('title', [''])[0]) if 'title' in audio.tags else '',
                    'artist': str(audio.tags.get('artist', [''])[0]) if 'artist' in audio.tags else '',
                    'album': str(audio.tags.get('album', [''])[0]) if 'album' in audio.tags else '',
                    'genre': str(audio.tags.get('genre', [''])[0]) if 'genre' in audio.tags else '',
                    'picture': None
                }

        # Use filename as fallback for missing title
        if not tags.get('title'):
            tags['title'] = Path(file_path).stem

        return {
            'name_song': tags.get('title', ''),
            'picture_song': tags.get('picture'),
            'the_loai': tags.get('genre', ''),
            'duration': duration,
            'file_path': file_path,
            'artist': tags.get('artist', '')
        }
    except Exception as e:
        print(f"Error reading metadata from {file_path}: {str(e)}")
        return None

def generate_sql_inserts(folder_path: str) -> None:
    """
    Generate SQL INSERT statements for songs in the given folder.
    """
    #  Get the next available IDs for singer, song, and album
    next_singer_id = get_next_singer_id()
    next_song_id = get_next_song_id()
    next_album_id = get_next_album_id()  # Get next id album
    
    # Create the output SQL file
    with open('insert_songs.sql', 'w', encoding='utf-8') as f:
        f.write(f"-- sua lai singer name trong table singer , sua lai link avatar singer , them description trong table album \n")
        # Insert statement for the singer
        singer_name = Path(folder_path).name
        f.write(f"-- Insert singer\n")
        f.write(f"INSERT INTO singer (id_singer, name_singer, picture_singer) VALUES ({next_singer_id}, '{singer_name}', '{ALBUM_ART_URL}');\n\n")
        
        # Thêm lệnh INSERT cho album
        album_name = singer_name
        f.write(f"-- Insert album\n")
        f.write(f"INSERT INTO albums (id_album, name_album, picture_album, description) VALUES ({next_album_id}, '{album_name}', '{ALBUM_ART_URL}', 'Album {album_name}');\n\n")
        
        # Insert statement for each song 
        f.write(f"-- Insert songs\n")
        for file_path in Path(folder_path).glob('*.mp3'):
            try:
                # Read metadata form file MP3
                audio = mutagen.File(file_path)
                if audio is None:
                    print(f"Could not read metadata from {file_path}")
                    continue
                
                # Get title from file name
           
                filename = Path(file_path).stem
                # Nếu tên file có dạng "nghệ sĩ - tên bài hát", chỉ lấy phần tên bài hát
                if '-' in filename:
                    title = filename.split('-', 1)[1].strip()
                else:
                    title = filename.strip()
            
                duration = int(audio.info.length) if hasattr(audio.info, 'length') else 0
                
                # Upload file to Supabase Storage
                file_url = upload_to_storage(file_path)
                if not file_url:
                    print(f"Skipping {file_path} due to upload error")
                    continue
                
                # Generate SQL INSERT statement
                f.write(f"""INSERT INTO songs (
                    id_song, 
                    picture_song, 
                    name_song, 
                    id_singer, 
                    the_loai, 
                    am_thanh, 
                    duration, 
                    luot_nghe, 
                    danh_gia, 
                    volume
                ) VALUES (
                    {next_song_id}, 
                    '{ALBUM_ART_URL}', 
                    '{title}', 
                    {next_singer_id}, 
                    'Pop', 
                    '{file_url}', 
                    {duration}, 
                    0, 
                    1, 
                    100
                );\n\n""")
                
                # Optional: Insert into album_songs mapping table 
                f.write(f"INSERT INTO album_songs (id_album, id_song) VALUES ({next_album_id}, {next_song_id});\n\n")
                
                next_song_id += 1
                
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
                continue

def get_next_album_id() -> int:
    """
    Get the next available album ID from the database.
    """
    try:
        response = supabase.table('albums').select('id_album').order('id_album', desc=True).limit(1).execute()
        if response.data:
            return response.data[0]['id_album'] + 1
        return 1
    except Exception as e:
        print(f"Error getting next album ID: {str(e)}")
        return 1

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Validate Supabase credentials
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")
        print("Please check your .env file and make sure it contains:")
        print("SUPABASE_URL=your_supabase_url")
        print("SUPABASE_SERVICE_KEY=your_service_role_key")
        exit(1)
    
    # Get music folder path from input 
    folder_path = input("Enter the path to your music folder: ").strip()
    if not os.path.exists(folder_path):
        print(f"Error: Folder {folder_path} does not exist")
        exit(1)
    
    # Generate SQL
    generate_sql_inserts(folder_path)
    print("\nSQL commands have been generated in insert_songs.sql")
    print("Please review and modify ALBUM_ART_URL in the script before running it again") 