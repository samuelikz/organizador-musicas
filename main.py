import os
import shutil
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import threading
import requests
import time
from dotenv import load_dotenv
import sys

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurar a API do Gemini
api_key = os.getenv('API_KEY', '')  # Carrega a chave da API do arquivo .env
retry_delay = int(os.getenv('RETRY_DELAY', '5'))  # Carrega o tempo de espera do arquivo .env

api_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=' + api_key

cancel_flag = threading.Event()

class ConsoleOutput:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')

    def flush(self):
        pass

def save_config(api_key, retry_delay):
    with open('.env', 'w') as f:
        f.write(f'API_KEY={api_key}\n')
        f.write(f'RETRY_DELAY={retry_delay}\n')
    messagebox.showinfo("Configuração", "Configuração salva com sucesso!")

def configure():
    global api_key, retry_delay, api_url
    api_key = simpledialog.askstring("Configuração", "Digite sua chave da API:", initialvalue=api_key)
    retry_delay = simpledialog.askinteger("Configuração", "Digite o tempo limite de espera (segundos):", initialvalue=retry_delay)
    
    if api_key and retry_delay:
        api_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=' + api_key
        save_config(api_key, retry_delay)

def organize_music_folder(src_folder_path, dst_folder_path, progress_var, root):
    try:
        files = [f for f in os.listdir(src_folder_path) if os.path.isfile(os.path.join(src_folder_path, f))]
        total_files = len(files)
        if total_files == 0:
            root.after(0, lambda: messagebox.showwarning("Aviso", "Nenhum arquivo encontrado na pasta de origem."))
            return

        batch_size = 200
        for batch_start in range(0, total_files, batch_size):
            if cancel_flag.is_set():
                root.after(0, lambda: messagebox.showinfo("Concluído", "Processo cancelado pelo usuário."))
                return
            
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

                    progress = (batch_start + index + 1) / total_files * 100
                    root.after(0, lambda p=progress: progress_var.set(p))
                except Exception as e:
                    root.after(0, lambda e=e, file=file: messagebox.showerror("Erro", f"Ocorreu um erro ao processar o arquivo {file}: {e}"))

        root.after(0, lambda: messagebox.showinfo("Concluído", "Processo concluído com sucesso."))
    except Exception as e:
        root.after(0, lambda e=e: messagebox.showerror("Erro", f"Ocorreu um erro ao acessar a pasta de origem: {e}"))

def standardize_filename(file_name):
    name, extension = os.path.splitext(file_name)
    name = re.sub(r'[^a-zA-Z0-9\s_\-ãõáéíóúâêîôûàèìòùäëïöüç]', '', name).strip()
    name = re.sub(r'^\d+\s*', '', name)

    match = re.match(r"(\d+)?\s*([\w\sãõáéíóúâêîôûàèìòùäëïöüç]+)", name)
    if match:
        _, title = match.groups()
        title = title.strip().title()
    else:
        title = name.title()

    artist = "Desconhecido"
    genre, year = get_genre_and_year(title)

    return f"{artist} - {title}{extension}", genre, year

def get_genre_and_year(title):
    headers = {'Content-Type': 'application/json'}
    data = {'contents': [{'parts': [{'text': (
        f"Você é um especialista em música com profundo conhecimento sobre diferentes gêneros e períodos de lançamento de músicas. "
        f"Eu preciso da sua ajuda para classificar a música com o título '{title}'. "
        f"Por favor, identifique o gênero musical mais provável e o ano de lançamento da música. "
        f"Forneça sua resposta em um formato simples e claro, separado por vírgulas. "
        f"Por exemplo, se a música for do gênero rock e lançada em 1990, a resposta deve ser 'Rock, 1990'. "
        f"Se a música for do gênero pop e lançada em 2005, a resposta deve ser 'Pop, 2005'. "
        f"Certifique-se de fornecer apenas o gênero e o ano, separados por uma vírgula, sem informações adicionais. "
        f"Se não tiver certeza sobre o ano exato, forneça sua melhor estimativa. "
        f"Além disso, siga as regras ortográficas e gramaticais do português do Brasil ao fornecer o gênero e o ano. "
        f"Use acentuação correta, letras maiúsculas e minúsculas conforme necessário."
    )}]}]}
    max_retries = 5

    for attempt in range(max_retries):
        if cancel_flag.is_set():
            print("Processo cancelado pelo usuário.")
            return "Desconhecido", "Desconhecido"
        
        response = requests.post(api_url, headers=headers, json=data)
        if response.status_code == 200:
            response_json = response.json()
            print("Resposta da API:", response_json)

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
            root.after(0, lambda: messagebox.showerror("Erro", f"Ocorreu um erro ao acessar a API: {response.status_code} - {response.text}"))
            return "Desconhecido", "Desconhecido"

    root.after(0, lambda: messagebox.showerror("Erro", "Todas as tentativas de acessar a API falharam devido ao limite de cota."))
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
    global cancel_flag
    cancel_flag.clear()
    src = src_folder_path.get()
    dst = dst_folder_path.get()
    if not src or not dst:
        messagebox.showwarning("Aviso", "Selecione as pastas de origem e destino.")
        return
    progress_var.set(0)
    threading.Thread(target=organize_music_folder, args=(src, dst, progress_var, root)).start()

def cancel_organizing():
    cancel_flag.set()

root = tk.Tk()
root.title("Organizador de Músicas")
root.configure(bg='white')

frame = tk.Frame(root, padx=20, pady=20, bg='white')
frame.pack(padx=10, pady=10)

label = tk.Label(frame, text="Organizador de Músicas", font=("Arial", 16), bg='white')
label.pack(pady=10)

src_folder_path = tk.StringVar()
dst_folder_path = tk.StringVar()

style = ttk.Style()
style.configure("TButton", padding=6, relief="flat", background="#000", foreground="#fff", font=("Arial", 12), borderwidth=0)
style.map("TButton", background=[("active", "#333")])
style.configure("TButton.Cancel.TButton", background="red", foreground="white", relief="flat", borderwidth=0)

src_button = ttk.Button(frame, text="Selecionar Pasta de Origem", command=select_src_folder, style="TButton")
src_button.pack(pady=5)

src_label = tk.Label(frame, textvariable=src_folder_path, font=("Arial", 10), wraplength=400, bg='white')
src_label.pack(pady=5)

dst_button = ttk.Button(frame, text="Selecionar Pasta de Destino", command=select_dst_folder, style="TButton")
dst_button.pack(pady=5)

dst_label = tk.Label(frame, textvariable=dst_folder_path, font=("Arial", 10), wraplength=400, bg='white')
dst_label.pack(pady=5)

start_button = ttk.Button(frame, text="Organizar Músicas", command=start_organizing, style="TButton")
start_button.pack(pady=20)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
progress_bar.pack(pady=10, fill=tk.X)

log_text = tk.Text(frame, height=5, width=50, bg='#f0f0f0', state='disabled')
log_text.pack(pady=10)

config_frame = tk.Frame(frame, bg='white')
config_frame.pack(pady=10)

config_button = ttk.Button(config_frame, text="Configurações", command=configure, style="TButton")
config_button.pack(side=tk.LEFT, padx=5)

cancel_button = ttk.Button(config_frame, text="Cancelar", command=cancel_organizing, style="TButton.Cancel.TButton")
cancel_button.pack(side=tk.LEFT, padx=5)

# Redirecionar stdout e stderr para a caixa de texto
console_output = ConsoleOutput(log_text)
sys.stdout = console_output
sys.stderr = console_output

root.mainloop()
