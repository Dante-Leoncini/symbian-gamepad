# -*- coding: utf-8 -*-
# pys60_client_multi_reconnect_safe.py
# Cliente PyS60 refactorizado y seguro
# Mantiene interfaz original

import socket
import struct
import appuifw
import e32
import graphics
import sensor
import thread

# === Configuración ===
PROXY_HOST = '192.168.0.4:5000'
FPS = 120  # frames por segundo de envío
MIN_FPS = 30
KEEPALIVE = True

# === Rutas imágenes ===
BASE_PATH = u"E:\\python\\control\\base.png"
A_PATH = u"E:\\python\\control\\A.png"
B_PATH = u"E:\\python\\control\\B.png"
X_PATH = u"E:\\python\\control\\X.png"
Y_PATH = u"E:\\python\\control\\Y.png"
A_PRESS_PATH = u"E:\\python\\control\\A_press.png"
B_PRESS_PATH = u"E:\\python\\control\\B_press.png"
X_PRESS_PATH = u"E:\\python\\control\\X_press.png"
Y_PRESS_PATH = u"E:\\python\\control\\Y_press.png"
LOGO_PATH = u"E:\\python\\control\\logo.png"

# === Estado global ===
sock = None
host = None
port = None
pressed = {}
sensor_acc = None
volante_activado = False
ultimo_analog = {'X': 0, 'Y': 0}
canvas = None
texto_actual = u""
_sending = False
_running = True
_lock = thread.allocate_lock()

# === Cargar imágenes ===
try:
    base_img = graphics.Image.open(BASE_PATH)
    logo_img = graphics.Image.open(LOGO_PATH)
    A_img = graphics.Image.open(A_PATH)
    B_img = graphics.Image.open(B_PATH)
    X_img = graphics.Image.open(X_PATH)
    Y_img = graphics.Image.open(Y_PATH)
    A_press_img = graphics.Image.open(A_PRESS_PATH)
    B_press_img = graphics.Image.open(B_PRESS_PATH)
    X_press_img = graphics.Image.open(X_PRESS_PATH)
    Y_press_img = graphics.Image.open(Y_PRESS_PATH)
except:
    base_img = logo_img = A_img = B_img = X_img = Y_img = None
    A_press_img = B_press_img = X_press_img = Y_press_img = None

# === Mapas ===
KEY_MAP = {
    16: 'up', 17: 'down', 14: 'left', 15: 'right',
    165: 'start',
    167: '1',
    49: '1', 50: '2', 51: '3',
    52: '4', 53: '5', 54: '6',
    55: '7', 56: '8', 57: '9'
}
NAME_TO_BUTTON = {
    '1': 'A', '2': 'B', '3': 'X', '4': 'Y',
    '5': 'SELECT', '6': 'LT', '7': 'RT', '8': 'LB', '9': 'RB',
    'start': 'START',
    'up': 'UP', 'down': 'DOWN', 'left': 'LEFT', 'right': 'RIGHT'
}

# === Funciones de red ===
def _parse_proxy():
    global host, port
    try:
        raw = PROXY_HOST.strip()
        host_s, port_s = raw.rsplit(':', 1)
        host = host_s
        port = int(port_s)
    except:
        host = None
        port = None

def _make_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except: pass
    try:
        if KEEPALIVE:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except: pass
    return s

def connect_once(timeout=1.0):
    global host, port
    if host is None or port is None:
        _parse_proxy()
    if host is None:
        return None
    s = _make_socket()
    try:
        s.settimeout(timeout)
        s.connect((host, port))
        s.settimeout(None)
        return s
    except:
        try: s.close()
        except: pass
        return None

def connect_background():
    """Hilo de reconexión automática"""
    global sock, _running
    backoff = 0.2
    connected_shown = False
    while _running:
        _lock.acquire()
        have = sock is not None
        _lock.release()
        if not have:
            s = connect_once()
            if s:
                _lock.acquire()
                sock = s
                _lock.release()
                if not connected_shown:
                    try: appuifw.note(u"Conectado a %s:%d" % (host, port))
                    except: pass
                    connected_shown = True
                backoff = 0.2
            else:
                connected_shown = False
                e32.ao_sleep(backoff)
                backoff = min(backoff*1.5,2.0)
        else:
            e32.ao_sleep(0.5)

def close_sock():
    global sock
    _lock.acquire()
    try:
        s = sock
        sock = None
    finally: _lock.release()
    try:
        if s: s.close()
    except: pass

# === Empaquetado y envío ===
def pack_and_send_state(current_fps):
    global _sending, texto_actual
    _lock.acquire()
    s = sock
    _lock.release()
    if s is None:
        texto_actual = u"Desconectado"
        return
    if _sending: return
    _sending = True
    try:
        if volante_activado:
            x = int(ultimo_analog['X'])
            y = int(ultimo_analog['Y'])
        else:
            x = -32768 if pressed.get('LEFT',False) else (32767 if pressed.get('RIGHT',False) else 0)
            y = -32768 if pressed.get('UP',False) else (32767 if pressed.get('DOWN',False) else 0)
        x = max(-32768,min(32767,x))
        y = max(-32768,min(32767,y))
        btn_names = ['A','B','X','Y','LB','RB','SELECT','START']
        btn_bits = 0
        for i,name in enumerate(btn_names):
            if pressed.get(name,False):
                btn_bits |= (1<<i)
        dpad_names = ['UP','DOWN','LEFT','RIGHT']
        dpad_bits = 0
        for i,name in enumerate(dpad_names):
            if pressed.get(name,False):
                dpad_bits |= (1<<i)
        data = struct.pack('<hhBB', x, y, btn_bits & 0xFF, dpad_bits & 0xFF)
        total_sent = 0
        try: s.setblocking(False)
        except: pass
        while total_sent < len(data):
            try:
                sent = s.send(data[total_sent:])
                if sent == 0:
                    close_sock()
                    texto_actual = u"Socket cerrado por peer"
                    return
                total_sent += sent
            except:
                close_sock()
                texto_actual = u"Error al enviar"
                return
        texto_actual = u"Enviando FPS: %d" % int(current_fps)
    finally:
        _sending = False
        try: s.setblocking(True)
        except: pass

# === Eventos teclado ===
def handle_key_event(event):
    t = event.get('type')
    sc = event.get('scancode')
    name = KEY_MAP.get(sc,None)
    if name is None: return
    if t==appuifw.EEventKeyDown:
        _on_key(name,True)
    elif t==appuifw.EEventKeyUp:
        _on_key(name,False)

def _on_key(name,pressed_state):
    btn = NAME_TO_BUTTON.get(name,None)
    if btn is None: return
    pressed[btn] = pressed_state
    actualizar_boton(btn)

# === UI ===
def actualizar_boton(btn):
    if canvas is None: return
    try:
        if btn=='A': canvas.blit(A_press_img if pressed.get('A',False) else A_img,target=(225,128))
        elif btn=='B': canvas.blit(B_press_img if pressed.get('B',False) else B_img,target=(246,111))
        elif btn=='X': canvas.blit(X_press_img if pressed.get('X',False) else X_img,target=(206,113))
        elif btn=='Y': canvas.blit(Y_press_img if pressed.get('Y',False) else Y_img,target=(227,96))
    except: pass

def dibujar():
    global canvas,texto_actual
    try:
        canvas.clear(0x000000)
        if base_img: canvas.blit(base_img,target=(38,45))
        if logo_img: canvas.blit(logo_img,target=(5,5))
        if A_img: canvas.blit(A_img,target=(225,128))
        if B_img: canvas.blit(B_img,target=(246,111))
        if X_img: canvas.blit(X_img,target=(206,113))
        if Y_img: canvas.blit(Y_img,target=(227,96))
        if texto_actual: canvas.text((45,20),texto_actual,0xFFFFFF)
    except: pass

# === Acelerómetro ===
def sensor_handler(data):
    global ultimo_analog
    if not volante_activado: return
    try:
        ultimo_analog['X'] = data.get('data_2',ultimo_analog['X'])
        ultimo_analog['Y'] = data.get('data_1',ultimo_analog['Y'])
    except: pass

# === Menú ===
def toggle_volante():
    global volante_activado
    volante_activado = not volante_activado
    try: appuifw.note(u"Volante %s"%(u"activado" if volante_activado else u"desactivado"))
    except: pass

def salir():
    global _running
    _running=False
    cleanup()
    try: app_lock.signal()
    except: pass

appuifw.app.menu=[
    (u"Activar/Desactivar volante",toggle_volante),
    (u"Salir",salir)
]

# === Limpieza ===
def cleanup():
    global sensor_acc
    try:
        if sensor_acc: sensor_acc.disconnect()
    except: pass
    close_sock()

# === Hilo de envío ===
def sender_loop():
    current_fps=float(FPS)
    min_fps=float(MIN_FPS)
    while _running:
        pack_and_send_state(current_fps)
        if texto_actual and u"Error" in texto_actual:
            current_fps = max(min_fps,current_fps*0.95)
        else:
            current_fps = min(float(FPS),current_fps*1.02)
        e32.ao_sleep(1.0/max(1.0,current_fps))

# === Main ===
def main():
    global sensor_acc,canvas
    _parse_proxy()
    thread.start_new_thread(connect_background,())
    try:
        sensores = sensor.sensors()
        if 'AccSensor' in sensores:
            sdata=sensores['AccSensor']
            sensor_acc = sensor.Sensor(sdata['id'],sdata['category'])
            sensor_acc.set_event_filter(sensor.EventFilter())
            sensor_acc.connect(sensor_handler)
    except: pass
    appuifw.app.screen='full'
    appuifw.app.exit_key_handler=lambda: None
    canvas=appuifw.Canvas(redraw_callback=lambda r: dibujar(),
                          event_callback=handle_key_event)
    appuifw.app.body=canvas
    dibujar()
    thread.start_new_thread(sender_loop,())
    app_lock.wait()
    cleanup()

if __name__=='__main__':
    app_lock=e32.Ao_lock()
    main()
