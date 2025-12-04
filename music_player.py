import pygame
import time
import customtkinter as ctk 
from tkinter import *
from tkinter import filedialog
from mutagen.mp3 import MP3
import os
import json 
import sys 

# --- Configuração do Tema ---
ctk.set_appearance_mode("Dark") 

# === PALETA MONARCA DAS SOMBRAS (SOLO LEVELING) ===
SHADOW_BG = "#050505"          # Preto Profundo
SHADOW_PURPLE = "#9747FF"      # Roxo Brilhante
SYSTEM_BLUE = "#00E0FF"        # Azul Ciano
DEATH_RED = "#C90000"          # Vermelho Sangue
ARMOR_GRAY = "#1A1A1A"         # Cinza Metálico

root = ctk.CTk()
root.title(">> SYSTEM PLAYER: SHADOW MONARCH <<") 
root.geometry("800x630")
root.configure(fg_color=SHADOW_BG)

# Ícone da Janela
try:
    if getattr(sys, 'frozen', False):
        APP_DIR = os.path.dirname(sys.executable)
    else:
        APP_DIR = os.path.dirname(os.path.abspath(__file__))
    
    icon_path = os.path.join(APP_DIR, "icon.ico")
    root.iconbitmap(icon_path)
except: pass

# --- CORREÇÃO DE FREQUÊNCIA (O SEGREDO PARA A BARRA NÃO CORRER) ---
# frequency=44100 ajusta o relógio interno para o padrão de MP3
pygame.mixer.init(frequency=44100)

# Variáveis Globais
global paused, stopped, repeat_mode, current_song_length, current_folder, song_start_time
paused = False
stopped = False
repeat_mode = False 
current_song_length = 0 
current_folder = "" 
song_start_time = 0 

CONFIG_FILE = os.path.join(APP_DIR, "system_memory.json")

# --- SISTEMA DE MEMÓRIA (SAVE/LOAD) ---
def save_config(path):
    data = {"last_folder": path}
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except: pass

def load_config():
    global current_folder
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                saved_path = data.get("last_folder")
                if saved_path and os.path.exists(saved_path):
                    current_folder = saved_path
                    load_songs_from_folder(saved_path)
        except: pass

def load_songs_from_folder(path):
    try:
        os.chdir(path)
        songs = os.listdir(path)
        playlist_box.delete(0, END) 
        for song in songs:
            if song.endswith(".mp3"):
                playlist_box.insert(END, song)
    except: pass

# --- JANELA DE COMANDOS (AJUDA) ---
def show_shortcuts():
    help_window = ctk.CTkToplevel(root)
    help_window.title(">> SYSTEM: SKILLS LIST <<")
    help_window.geometry("400x450")
    help_window.configure(fg_color=SHADOW_BG)
    help_window.attributes("-topmost", True)

    ctk.CTkLabel(help_window, text="COMANDOS DO SISTEMA", font=("Impact", 18), text_color=SYSTEM_BLUE).pack(pady=(20, 10))

    shortcuts = [
        ("ESPAÇO", "Pausar / Continuar"),
        ("ENTER", "Tocar Música Selecionada"),
        ("SETA DIR (→)", "Avançar +5 Segundos"),
        ("SETA ESQ (←)", "Voltar -5 Segundos"),
        ("SETA CIMA (↑)", "Aumentar Volume"),
        ("SETA BAIXO (↓)", "Diminuir Volume"),
        ("TECLA 'F'", "Próxima Música (Forward)"),
        ("TECLA 'B'", "Música Anterior (Back)"),
        ("TECLA 'R'", "Repetir: ON/OFF"),
        ("TECLA 'S'", "Parar Totalmente")
    ]

    for key, desc in shortcuts:
        row = ctk.CTkFrame(help_window, fg_color="transparent")
        row.pack(fill="x", padx=30, pady=2)
        ctk.CTkLabel(row, text=key, font=("Consolas", 12, "bold"), text_color=SHADOW_PURPLE, anchor="w").pack(side=LEFT)
        ctk.CTkLabel(row, text=desc, font=("Consolas", 12), text_color="gray", anchor="e").pack(side=RIGHT)

# --- JANELA DO EQUALIZADOR ---
def open_equalizer():
    eq_window = ctk.CTkToplevel(root)
    eq_window.title(">> SYSTEM: AUDIO CONFIG <<")
    eq_window.geometry("500x350")
    eq_window.configure(fg_color=SHADOW_BG)
    eq_window.attributes("-topmost", True)

    ctk.CTkLabel(eq_window, text="MODULAÇÃO DE FREQUÊNCIA", font=("Impact", 20), text_color=SYSTEM_BLUE).pack(pady=10)

    sliders_frame = ctk.CTkFrame(eq_window, fg_color="transparent")
    sliders_frame.pack(pady=10, padx=10, expand=True, fill="both")

    bands = ["60Hz", "170Hz", "310Hz", "600Hz", "1kHz", "3kHz", "6kHz", "12kHz"]
    
    for i, band in enumerate(bands):
        band_frame = ctk.CTkFrame(sliders_frame, fg_color="transparent")
        band_frame.grid(row=0, column=i, padx=8, pady=5)
        slider = ctk.CTkSlider(band_frame, from_=0, to=100, orientation="vertical", height=150, width=18,
                               fg_color=ARMOR_GRAY, progress_color=SHADOW_PURPLE, 
                               button_color=SYSTEM_BLUE, button_hover_color="white")
        slider.set(50)
        slider.pack()
        ctk.CTkLabel(band_frame, text=band, font=("Consolas", 10), text_color="gray").pack(pady=5)

    msg = ctk.CTkLabel(eq_window, text="[AVISO DO SISTEMA]: Módulo DSP não carregado.", 
                       font=("Consolas", 10), text_color="gray")
    msg.pack(side=BOTTOM, pady=10)

# --- LÓGICA DO PLAYER (CALIBRADA) ---
def move_time_label(current_seconds, total_seconds):
    cur_str = time.strftime('%M:%S', time.gmtime(current_seconds))
    tot_str = time.strftime('%M:%S', time.gmtime(total_seconds))
    floating_time_label.configure(text=f"{cur_str} / {tot_str}")

    if my_slider.winfo_exists(): 
        slider_width = my_slider.winfo_width()
        slider_start_x = my_slider.winfo_x()
        percentage = current_seconds / total_seconds if total_seconds > 0 else 0
        x_pos = slider_start_x + (slider_width * percentage) - 30
        y_pos = my_slider.winfo_y() - 25 
        floating_time_label.place(x=x_pos, y=y_pos)
        floating_time_label.lift() 

def play_time():
    global current_song_length, song_start_time
    if stopped: return
    try:
        # AQUI OBTEMOS O TEMPO REAL DO MOTOR
        current_engine_pos = pygame.mixer.music.get_pos() / 1000

        if pygame.mixer.music.get_busy() and not paused:
            if current_engine_pos >= 0:
                exact_time = song_start_time + current_engine_pos
                
                # Trava de Segurança: Não deixa a barra passar do final da música
                if exact_time > current_song_length:
                    exact_time = current_song_length

                # Só atualiza se estiver tocando
                if exact_time <= current_song_length:
                    my_slider.set(exact_time)
                    move_time_label(exact_time, current_song_length)
                
                # Se a barra chegou no fim e o tempo bateu, passa a música
                if exact_time >= current_song_length:
                     move_time_label(current_song_length, current_song_length)
                     if repeat_mode: play_music()
                     else: next_music()
        
        # Caso especial: Música acabou mas o get_busy demorou pra avisar
        elif not pygame.mixer.music.get_busy() and not paused:
            move_time_label(current_song_length, current_song_length)
            if repeat_mode: play_music()
            else: next_music() 
    except: pass
    
    floating_time_label.after(500, play_time)

def add_music():
    global current_folder
    path = filedialog.askdirectory()
    if path:
        current_folder = path
        load_songs_from_folder(path)
        save_config(path) 

def play_music():
    global paused, stopped, current_song_length, song_start_time
    stopped = False
    paused = False 
    try:
        if playlist_box.curselection():
            music_name = playlist_box.get(ACTIVE)
            song_mut = MP3(music_name)
            current_song_length = song_mut.info.length 
            
            my_slider.configure(to=current_song_length)
            
            pygame.mixer.music.load(music_name)
            pygame.mixer.music.play(loops=0)
            
            song_start_time = 0 
            
            my_slider.set(0)
            play_time() 
            pygame.mixer.music.set_volume(volume_slider.get())
            pause_btn.configure(text="Pausar", fg_color=ARMOR_GRAY, text_color=SHADOW_PURPLE, hover_color="#2a2a2a")
    except: pass

def stop_music():
    global stopped
    pygame.mixer.music.stop()
    playlist_box.selection_clear(ACTIVE)
    my_slider.set(0)
    floating_time_label.place_forget() 
    stopped = True
    pause_btn.configure(text="Pausar", fg_color=ARMOR_GRAY, text_color=SHADOW_PURPLE)

def pause_music():
    global paused
    if paused:
        pygame.mixer.music.unpause()
        paused = False
        pause_btn.configure(text="Pausar", fg_color=ARMOR_GRAY, text_color=SHADOW_PURPLE) 
    else:
        pygame.mixer.music.pause()
        paused = True
        pause_btn.configure(text="Continuar", fg_color=ARMOR_GRAY, text_color=SYSTEM_BLUE) 

def next_music():
    my_slider.set(0)
    try:
        current_selection = playlist_box.curselection()
        if current_selection:
            next_one = current_selection[0] + 1
            if next_one >= playlist_box.size(): next_one = 0 
            song = playlist_box.get(next_one)
            song_mut = MP3(song)
            global current_song_length, song_start_time
            current_song_length = song_mut.info.length
            my_slider.configure(to=current_song_length)
            
            pygame.mixer.music.load(song)
            pygame.mixer.music.play(loops=0)
            
            song_start_time = 0 
            
            playlist_box.selection_clear(0, END)
            playlist_box.activate(next_one)
            playlist_box.selection_set(next_one)
    except: pass

def prev_music():
    my_slider.set(0)
    try:
        current_selection = playlist_box.curselection()
        if current_selection:
            prev_one = current_selection[0] - 1
            if prev_one >= 0:
                song = playlist_box.get(prev_one)
                song_mut = MP3(song)
                global current_song_length, song_start_time
                current_song_length = song_mut.info.length
                my_slider.configure(to=current_song_length)
                
                pygame.mixer.music.load(song)
                pygame.mixer.music.play(loops=0)
                
                song_start_time = 0 
                
                playlist_box.selection_clear(0, END)
                playlist_box.activate(prev_one)
                playlist_box.selection_set(prev_one)
    except: pass

def toggle_repeat():
    global repeat_mode
    repeat_mode = not repeat_mode
    if repeat_mode: repeat_btn.configure(text="REPETIR: LIGADO", fg_color=SHADOW_PURPLE, text_color="white")
    else: repeat_btn.configure(text="REPETIR: DESLIGADO", fg_color=ARMOR_GRAY, text_color=SHADOW_PURPLE)

def vol_up(event=None):
    current_vol = volume_slider.get()
    new_vol = current_vol + 0.1
    if new_vol > 1: new_vol = 1
    volume_slider.set(new_vol)
    set_volume(new_vol)
    return "break" 

def vol_down(event=None):
    current_vol = volume_slider.get()
    new_vol = current_vol - 0.1
    if new_vol < 0: new_vol = 0
    volume_slider.set(new_vol)
    set_volume(new_vol)
    return "break" 

def slide(val):
    global song_start_time
    try:
        if playlist_box.curselection():
            music_name = playlist_box.get(ACTIVE)
            pygame.mixer.music.load(music_name)
            pygame.mixer.music.play(loops=0, start=float(val)) 
            song_start_time = val 
            move_time_label(val, current_song_length)
    except: pass

def set_volume(val):
    pygame.mixer.music.set_volume(val)

def skip_forward():
    try:
        val = my_slider.get() + 5
        if val < current_song_length: 
            my_slider.set(val)
            slide(val)
        else: stop_music()
    except: pass

def skip_backward():
    val = my_slider.get() - 5
    if val > 0:
        my_slider.set(val)
        slide(val)
    else:
        my_slider.set(0)
        slide(0)

# --- INTERFACE VISUAL ---
title_label = ctk.CTkLabel(root, text="⚡ ERGA-SE ⚡", font=("Impact", 32), text_color=SHADOW_PURPLE)
title_label.pack(pady=(20, 5))
subtitle_label = ctk.CTkLabel(root, text="O Sistema de Música do Monarca das Sombras", font=("Consolas", 12), text_color=SYSTEM_BLUE)
subtitle_label.pack(pady=(0, 15))

playlist_box = Listbox(root, bg=SHADOW_BG, fg=SHADOW_PURPLE, width=80, height=12, 
                       selectbackground=SYSTEM_BLUE, selectforeground="black", 
                       font=("Consolas", 10, "bold"), borderwidth=1, highlightthickness=0, relief="flat")
playlist_box.pack(pady=10, padx=20)

floating_time_label = ctk.CTkLabel(root, text="00:00 / 00:00", text_color=SYSTEM_BLUE, font=("Consolas", 12, "bold"))

my_slider = ctk.CTkSlider(root, from_=0, to=100, command=slide, width=600, height=18, border_width=0,
                          fg_color=ARMOR_GRAY, progress_color=SHADOW_PURPLE, 
                          button_color=SHADOW_PURPLE, button_hover_color=SYSTEM_BLUE)   
my_slider.set(0)
my_slider.pack(pady=(30, 10))

utils_frame = ctk.CTkFrame(root, fg_color="transparent")
utils_frame.pack(pady=(0, 5))

repeat_btn = ctk.CTkButton(utils_frame, text="REPETIR: DESLIGADO", command=toggle_repeat,
                            width=150, height=20, font=("Consolas", 10, "bold"),
                            fg_color=ARMOR_GRAY, text_color=SHADOW_PURPLE,
                            hover_color="#2a2a2a")
repeat_btn.pack()

control_frame = ctk.CTkFrame(root, fg_color="transparent") 
control_frame.pack(pady=10)

btn_css = { "width": 60, "height": 40, "corner_radius": 0, "font": ("Consolas", 12, "bold"),
            "fg_color": ARMOR_GRAY, "hover_color": "#2a2a2a", "text_color": SHADOW_PURPLE,
            "border_width": 1, "border_color": ARMOR_GRAY }

ctk.CTkButton(control_frame, text="<<", command=prev_music, **btn_css).grid(row=0, column=0, padx=5)
ctk.CTkButton(control_frame, text="-5s", command=skip_backward, **btn_css).grid(row=0, column=1, padx=5)
pause_btn = ctk.CTkButton(control_frame, text="Pausar", command=pause_music, **btn_css)
pause_btn.grid(row=0, column=2, padx=5)
ctk.CTkButton(control_frame, text="TOCAR", command=play_music, width=90, height=45, corner_radius=0, border_width=0,
              fg_color=SHADOW_PURPLE, hover_color="#7a2be0", font=("Impact", 14), text_color="white").grid(row=0, column=3, padx=15)
ctk.CTkButton(control_frame, text="PARAR", command=stop_music, width=90, height=45, corner_radius=0, border_width=0,
              fg_color=DEATH_RED, hover_color="#a30000", font=("Impact", 14), text_color="white").grid(row=0, column=4, padx=15)
ctk.CTkButton(control_frame, text="+5s", command=skip_forward, **btn_css).grid(row=0, column=5, padx=5)
ctk.CTkButton(control_frame, text=">>", command=next_music, **btn_css).grid(row=0, column=6, padx=5)

vol_frame = ctk.CTkFrame(root, fg_color="transparent")
vol_frame.pack(pady=10)

ctk.CTkLabel(vol_frame, text="Volume", font=("Consolas", 12, "bold"), text_color=SYSTEM_BLUE).pack(side=LEFT, padx=10)
volume_slider = ctk.CTkSlider(vol_frame, from_=0, to=1, command=set_volume, width=150, 
                              fg_color=ARMOR_GRAY, progress_color=SYSTEM_BLUE, 
                              button_color=SYSTEM_BLUE, button_hover_color="white")
volume_slider.set(0.5)
volume_slider.pack(side=LEFT)

ctk.CTkButton(vol_frame, text="EQ ılılı", command=open_equalizer, width=80, height=25,
              fg_color=ARMOR_GRAY, text_color=SHADOW_PURPLE, font=("Consolas", 10, "bold"),
              hover_color="#2a2a2a").pack(side=LEFT, padx=(20, 10))

ctk.CTkButton(vol_frame, text="AJUDA ⌨️", command=show_shortcuts, width=80, height=25,
              fg_color=ARMOR_GRAY, text_color=SYSTEM_BLUE, font=("Consolas", 10, "bold"),
              hover_color="#2a2a2a").pack(side=LEFT, padx=5)

my_menu = Menu(root, bg=ARMOR_GRAY, fg=SHADOW_PURPLE) 
root.config(menu=my_menu)
add_song_menu = Menu(my_menu, tearoff=0, bg=ARMOR_GRAY, fg=SHADOW_PURPLE)
my_menu.add_cascade(label="Arquivo 📂", menu=add_song_menu)
add_song_menu.add_command(label="Adicionar Pasta...", command=add_music) 
add_song_menu.add_separator()
add_song_menu.add_command(label="Sair", command=root.quit)

root.bind('<Return>', lambda event: play_music()) 
root.bind('<space>', lambda event: pause_music())  
root.bind('<Up>', vol_up)                          
root.bind('<Down>', vol_down)                      
root.bind('s', lambda event: stop_music())         
root.bind('<Right>', lambda event: skip_forward()) 
root.bind('<Left>', lambda event: skip_backward()) 
root.bind('f', lambda event: next_music())         
root.bind('b', lambda event: prev_music())         
root.bind('r', lambda event: toggle_repeat())

playlist_box.bind('<Up>', vol_up)
playlist_box.bind('<Down>', vol_down)

load_config() 
root.mainloop()