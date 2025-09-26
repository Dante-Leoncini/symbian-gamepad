#!/usr/bin/env python3
import socket
import struct
from evdev import UInput, ecodes as e, AbsInfo

HOST = "0.0.0.0"
PORT = 5000

# --- Configuración ---
DEADZONE = 2000  # zona muerta en valores del stick (-32768..32767)

capabilities = {
    e.EV_KEY: [
        e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST,
        e.BTN_TL, e.BTN_TR, e.BTN_SELECT, e.BTN_START
    ],
    e.EV_ABS: [
        (e.ABS_X, AbsInfo(0, -32768, 32767, 0, 0, 0)),
        (e.ABS_Y, AbsInfo(0, -32768, 32767, 0, 0, 0)),
    ]
}

ui = UInput(events=capabilities, name="Virtual Xbox Fast", version=0x3)
print("Servidor creado, esperando cliente...")

BUTTON_ORDER = [e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST,
                e.BTN_TL, e.BTN_TR, e.BTN_SELECT, e.BTN_START]

def map_stick_x(x):
    # recorta dentro del rango físico del teléfono
    x = max(min(x, 266), -320)
    # mapeo lineal a -32768..32767
    virtual = int((x - (-320)) / (266 - (-320)) * (32767 - (-32768)) + (-32768))
    return -virtual

def apply_state(stick_x, stick_y, buttons, dpad):
    # Zona muerta
    stick_active = (abs(stick_x) < -42) or (abs(stick_x) > -22)

    if stick_active:
        #ui.write(e.EV_ABS, e.ABS_X, stick_x)
        #ui.write(e.EV_ABS, e.ABS_Y, stick_y)
        stick_virtual_x = map_stick_x(stick_x)
        ui.write(e.EV_ABS, e.ABS_X, stick_virtual_x)
        print(f"[STICK] X={stick_virtual_x} Y={stick_y}")
    else:
        x = -32768 if dpad[2] else 32767 if dpad[3] else 0
        y = -32768 if dpad[0] else 32767 if dpad[1] else 0
        ui.write(e.EV_ABS, e.ABS_X, x)
        ui.write(e.EV_ABS, e.ABS_Y, y)
        print(f"[DPAD] X={x} Y={y}")

    # Botones
    btn_states = []
    for i, btn in enumerate(BUTTON_ORDER):
        state = buttons[i]
        ui.write(e.EV_KEY, btn, state)
        btn_states.append(state)
    if any(btn_states):
        print(f"[BUTTONS] {btn_states}")

    ui.syn()

# --- Servidor ---
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(1)

try:
    while True:
        conn, addr = server.accept()
        print("Cliente conectado desde:", addr)
        try:
            while True:
                data = conn.recv(6)
                if len(data) < 6:
                    continue
                stick_x, stick_y, btn_byte, dpad_byte = struct.unpack('<hhBB', data)
                buttons = [(btn_byte >> i) & 1 for i in range(8)]
                dpad = [(dpad_byte >> i) & 1 for i in range(4)]
                apply_state(stick_x, stick_y, buttons, dpad)
        except Exception as e:
            print("Error cliente:", e)
        finally:
            conn.close()
except KeyboardInterrupt:
    print("Cerrando servidor...")
finally:
    server.close()
    ui.close()
