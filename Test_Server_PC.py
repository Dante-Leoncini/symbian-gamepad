import socket, struct, random, time

HOST, PORT = "127.0.0.1", 5000

def random_packet():
    stick_x = random.randint(-32768, 32767)
    stick_y = random.randint(-32768, 32767)
    btn_byte = sum((random.randint(0, 1) << i) for i in range(8))
    dpad_byte = sum((random.randint(0, 1) << i) for i in range(4))
    return struct.pack('<hhBB', stick_x, stick_y, btn_byte, dpad_byte)

while True:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            print("Conectado")
            while True:
                s.sendall(random_packet())
                time.sleep(1/120)
    except Exception as e:
        print("Cliente error:", e, " — reintentando en 1s")
        time.sleep(1)
