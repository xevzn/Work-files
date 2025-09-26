import serial
import time
import pandas as pd
import os
import re

# 🔹 Limpiar pantalla según el SO
def clear_console():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

# 🔹 Enviar comando al router
def send_command(ser, command, delay=1):
    ser.write((command + "\r\n").encode())  # CRLF
    time.sleep(delay)
    output = ser.read(ser.in_waiting).decode(errors="ignore")
    return output

# 🔹 Obtener número de serie desde "show inventory"
def get_serial(ser):
    send_command(ser, "terminal length 0")  # evitar paginación
    output = send_command(ser, "show inventory", delay=2)
    match = re.search(r"SN:\s*([A-Z0-9]+)", output)
    if match:
        return match.group(1)
    return None

# 🔹 Configuración de dispositivo
def configure_device(port, hostname, user, password, domain):
    try:
        port = "COM5"
        ser = serial.Serial(port, baudrate=9600, timeout=1)
        time.sleep(2)
        print(f"\n🔗 Conectado al dispositivo en {port} ({hostname})")

        # Obtener número de serie
        serial_num = get_serial(ser)
        if not serial_num:
            print("⚠ No se pudo obtener el número de serie. Saltando configuración.")
            ser.close()
            return

        # Verificar si la serie coincide con alguna del CSV
        if hostname[1:] != serial_num[:6]:  # hostname = primera letra device + primeros 6 de serie CSV
            print(f"⚠ La serie del dispositivo ({serial_num}) no coincide con la del CSV ({hostname[1:]}). Saltando configuración.")
            ser.close()
            return

        # Enviar configuración básica
        send_command(ser, "enable")
        send_command(ser, "configure terminal")
        send_command(ser, f"hostname {hostname}")
        send_command(ser, f"username {user} privilege 15 secret {password}")
        send_command(ser, f"ip domain-name {domain}")
        send_command(ser, "crypto key generate rsa modulus 1024", delay=3)
        send_command(ser, "line vty 0 4")
        send_command(ser, "login local")
        send_command(ser, "transport input ssh")
        send_command(ser, "transport output ssh")
        send_command(ser, "exit")
        send_command(ser, "ip ssh version 2")
        send_command(ser, "end")
        send_command(ser, "write memory", delay=2)

        print(f"✅ Configuración aplicada correctamente en {hostname}.")

        ser.close()

    except Exception as e:
        print(f"❌ Error al configurar el dispositivo {hostname}: {e}")

# 🔹 Main
if __name__ == "__main__":
    df = pd.read_csv("C:\\Users\\Dani\\OneDrive\\Escritorio\\Clases Unipoli\\Cuatri 4\\Programacion de Redes\\Apuntes\\VENV\\Data.csv")
    print("\n📂 Dispositivos encontrados en el archivo:")
    print(df)

    # Crear lista de hostnames a partir de Device + Serie
    Hostnames = []
    for d, s in zip(df['Device'], df['Serie']):
        initial_d = str(d).strip()[0]
        initial_s = str(s).strip()[:6]
        device_name = initial_d + initial_s
        Hostnames.append(device_name)

    # Lista de configuraciones
    list_device = []
    for p, u, pas, dom, h in zip(df['Port'], df['User'], df['Password'], df['Ip-domain'], Hostnames):
        list_device.append((p, h, u, pas, dom))

    print("\n📋 Lista de dispositivos y sus configuraciones:")
    for item in list_device:
        print(item)
    input("Presione ENTER para continuar...")

    # Configurar dispositivos uno por uno
    for idx, (p, h, u, pas, dom) in enumerate(list_device, start=1):
        clear_console()
        print(f"\n➡️ Conecte ahora el dispositivo {idx}: {h} en el puerto {p}")
        input("Presione ENTER cuando el dispositivo esté conectado...")
        configure_device(p, h, u, pas, dom)
        print("=================================================")
        input("Presione ENTER para continuar...")
