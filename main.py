import os
import shutil
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import requests
import time

# Configurar a API do Gemini
api_key = 'KEY_API'  # Substitua pela sua chave de API real
api_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=' + api_key

def organize_music_folder(src_folder_path, dst_folder_path, progress_var, root):
    try:
        files = [f for f in os.listdir(src_folder_path) if os.path.isfile(os.path.join(src_folder_path, f))]
        total_files = len(files)
        if total_files == 0:
            messagebox.showwarning("Aviso", "Nenhum arquivo encontrado na pasta de origem.")
            return

        batch_size = 200
        for batch_start in range(0, total_files, batch_size):
            batch_files = files[batch_start:batch_start + batch_size]
            for index, file in enumerate(batch_files):
                try:
                    new_file_name, genre, year = standardize_filename(file)
                    genre_folder = os.path.join(dst_folder_path, genre)
                    year_folder = os.path.join(genre_folder, year)

                    if not os.path.exists(year_folder):
                        os.makedirs(year_folder)

                    src_file_path = os.path.join(src_folder_path, file)
                    dst_file_path = os.path.join(year_folder, new_file_name)

                    print(f"Movendo arquivo: {file} para {dst_file_path}")
                    shutil.move(src_file_path, dst_file_path)

                    progress_var.set((batch_start + index + 1) / total_files * 100)
                    root.update_idletasks()
                except Exception as e:
                    messagebox.showerror("Erro", f"Ocorreu um erro ao processar o arquivo {file}: {e}")
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao acessar a pasta de origem: {e}")

def standardize_filename(file_name):
    name, extension = os.path.splitext(file_name)
    # Remover caracteres indesejados, mas manter espaços, hífens e números
    name = re.sub(r'[^a-zA-Z0-9\s_\-]', '', name).strip()
    
    # Remover números iniciais que não fazem parte do título
    name = re.sub(r'^\d+\s*', '', name)

    # Verificar se o nome começa com um número e separar o número do nome da música
    match = re.match(r"(\d+)?\s*([\w\s]+)", name)
    if match:
        _, title = match.groups()
        title = title.strip().title()
    else:
        title = name.title()

    # Assumir que o artista é desconhecido se não estiver no formato esperado
    artist = "Desconhecido"

    # Use Gemini API to classify genre and year
    genre, year = get_genre_and_year(title)

    return f"{artist} - {title}{extension}", genre, year

def get_genre_and_year(title):
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'contents': [{'parts': [{'text': (
            f"Você é um especialista em música com profundo conhecimento sobre diferentes gêneros e períodos de lançamento de músicas. "
            f"Eu preciso da sua ajuda para classificar a música com o título '{title}'. "
            f"Por favor, identifique o gênero musical mais provável e o ano de lançamento da música. "
            f"Forneça sua resposta em um formato simples e claro, separado por vírgulas. "
            f"Por exemplo, se a música for do gênero rock e lançada em 1990, a resposta deve ser 'Rock, 1990'. "
            f"Se a música for do gênero pop e lançada em 2005, a resposta deve ser 'Pop, 2005'. "
            f"Certifique-se de fornecer apenas o gênero e o ano, separados por uma vírgula, sem informações adicionais. "
            f"Se não tiver certeza sobre o ano exato, forneça sua melhor estimativa."
        )}]}]
    }
    max_retries = 5
    retry_delay = 5  # segundos

    for attempt in range(max_retries):
        response = requests.post(api_url, headers=headers, json=data)
        if response.status_code == 200:
            response_json = response.json()
            print("Resposta da API:", response_json)  # Adicionar saída de depuração

            contents = response_json.get('contents', [])
            if contents:
                parts = contents[0].get('parts', [])
                if parts:
                    text = parts[0].get('text', '').strip()
                    if text:
                        classification = text.split(',')
                        genre = classification[0].strip() if len(classification) > 0 else "Desconhecido"
                        year = classification[1].strip() if len(classification) > 1 else "Desconhecido"
                        return genre, year

            return "Desconhecido", "Desconhecido"
        elif response.status_code == 429:
            print(f"Limite de cota atingido. Tentativa {attempt + 1} de {max_retries}. Aguardando {retry_delay} segundos antes de tentar novamente.")
            time.sleep(retry_delay)
        else:
            messagebox.showerror("Erro", f"Ocorreu um erro ao acessar a API: {response.status_code} - {response.text}")
            return "Desconhecido", "Desconhecido"

    messagebox.showerror("Erro", "Todas as tentativas de acessar a API falharam devido ao limite de cota.")
    return "Desconhecido", "Desconhecido"

def select_src_folder():
    folder_path = filedialog.askdirectory(title="Selecione a pasta de origem")
    if folder_path:
        src_folder_path.set(folder_path)
    else:
        messagebox.showwarning("Aviso", "Nenhuma pasta de origem selecionada.")

def select_dst_folder():
    folder_path = filedialog.askdirectory(title="Selecione a pasta de destino")
    if folder_path:
        dst_folder_path.set(folder_path)
    else:
        messagebox.showwarning("Aviso", "Nenhuma pasta de destino selecionada.")

def start_organizing():
    src = src_folder_path.get()
    dst = dst_folder_path.get()
    if not src or not dst:
        messagebox.showwarning("Aviso", "Selecione as pastas de origem e destino.")
        return
    progress_var.set(0)
    threading.Thread(target=organize_music_folder, args=(src, dst, progress_var, root)).start()

root = tk.Tk()
root.title("Organizador de Músicas")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(padx=10, pady=10)

label = tk.Label(frame, text="Organizador de Músicas", font=("Arial", 16))
label.pack(pady=10)

src_folder_path = tk.StringVar()
dst_folder_path = tk.StringVar()

src_button = tk.Button(frame, text="Selecionar Pasta de Origem", command=select_src_folder, font=("Arial", 12))
src_button.pack(pady=5)

src_label = tk.Label(frame, textvariable=src_folder_path, font=("Arial", 10), wraplength=400)
src_label.pack(pady=5)

dst_button = tk.Button(frame, text="Selecionar Pasta de Destino", command=select_dst_folder, font=("Arial", 12))
dst_button.pack(pady=5)

dst_label = tk.Label(frame, textvariable=dst_folder_path, font=("Arial", 10), wraplength=400)
dst_label.pack(pady=5)

start_button = tk.Button(frame, text="Organizar Músicas", command=start_organizing, font=("Arial", 12))
start_button.pack(pady=20)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
progress_bar.pack(pady=10, fill=tk.X)

root.mainloop()
