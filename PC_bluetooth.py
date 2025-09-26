#!/usr/bin/env python3
import socket
import struct
from evdev import UInput, ecodes as e, AbsInfo

# --- Configuración Bluetooth ---
HOST = ""          # vacío = cualquier interfaz Bluetooth local
PORT = 3           # canal RFCOMM (debe coincidir con cliente)

# Deadzone
DEADZONE = 2000

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
ui = UInput(events=capabilities, name="Virtual Xbox BT", version=0x3)
print("Servidor Bluetooth creado, esperando cliente...")

def map_stick_x(x):
    x = max(min(x, 266), -320)
    virtual = int((x - (-320)) / (266 - (-320)) * (-32768 - 32767) + 32767)
    return virtual

def apply_state(stick_x, stick_y, buttons, dpad):
    stick_virtual_x = map_stick_x(stick_x)
    ui.write(e.EV_ABS, e.ABS_X, stick_virtual_x)
    print(f"[STICK] X={stick_virtual_x} Y={stick_y}")

    ui.syn()

# --- Servidor Bluetooth ---
server = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
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
        except Exception as ex:
            print("Error cliente:", ex)
        finally:
            conn.close()
except KeyboardInterrupt:
    print("Cerrando servidor...")
finally:
    server.close()
    ui.close()