# -*- coding: utf-8 -*-
# pys60_random_client_safe.py
# Cliente PyS60 simple para enviar paquetes random a un servidor TCP

import socket
import struct
import random
import e32
import time

HOST = "192.168.0.4"  # IP de tu PC en LAN
PORT = 5000
FPS = 120  # paquetes por segundo

def random_packet():
    stick_x = random.randint(-32768, 32767)
    stick_y = random.randint(-32768, 32767)
    btn_byte = sum((random.randint(0,1) << i) for i in range(8))
    dpad_byte = sum((random.randint(0,1) << i) for i in range(4))
    return struct.pack('<hhBB', stick_x, stick_y, btn_byte, dpad_byte)

def main():
    paquete_count = 0
    while True:
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.connect((HOST, PORT))
            print("Conectado al servidor %s:%d" % (HOST, PORT))
            period = 1.0 / FPS
            while True:
                data = random_packet()
                try:
                    s.send(data)
                    paquete_count += 1
                    if paquete_count % 10 == 0:
                        print("Paquetes enviados:", paquete_count)
                except Exception, e_send:
                    print("Error enviando:", e_send)
                    break  # salir y reconectar
                try:
                    e32.ao_sleep(period)
                except:
                    break  # salir si hay error en sleep
        except Exception, e:
            print("Cliente error:", e, " — reintentando en 1s")
            try:
                e32.ao_sleep(1)
            except:
                pass
        finally:
            try:
                if s:
                    s.close()
            except:
                pass

if __name__ == "__main__":
    main()
