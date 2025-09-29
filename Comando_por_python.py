import serial
import time
import os
import re

# Limpia la consola en Windows
os.system("cls")

# Configura el puerto serial
ser = serial.Serial(
    port="COM9",   # Cambia si usas otro puerto
    baudrate=9600,
    timeout=1
)

def send_command(command, wait=1):
    ser.write((command + "\n").encode())
    time.sleep(wait)
    output = ser.read_all().decode(errors="ignore")
    return output

try:
    print("🔗 Conectado al dispositivo en COM")

    # Hacemos que el router muestre todo sin cortar
    send_command("terminal length 0")

    # Ejecutamos show inventory
    output = send_command("show inventory", wait=2)

    # Buscamos el número de serie con regex
    match = re.search(r"SN:\s*([A-Z0-9]+)", output)
    if match:
        print("📌 Número de serie:", match.group(1))
    else:
        print("⚠ No se encontró el número de serie en la salida.")

finally:
    ser.close()

