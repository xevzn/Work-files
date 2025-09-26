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
        ser = serial.Serial(port, baudrate=9600, timeout=1)
        time.sleep(2)
        print(f"\n🔗 Conectado al dispositivo en {port} ({hostname})")

        # Obtener número de serie
        serial_num = get_serial(ser)
        if not serial_num:
            print("⚠ No se pudo obtener el número de serie. Saltando configuración.")
            ser.close()
            return

        # Verificar coincidencia de serie
        if hostname[1:] != serial_num[:6]:
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

# 🔹 Función para enviar comandos manuales
def command_mode():
    port = input("Ingrese el puerto serial (ej. COM5): ")
    try:
        ser = serial.Serial(port, baudrate=9600, timeout=1)
        time.sleep(2)
        print(f"\n🔗 Conectado al dispositivo en {port}")
        send_command(ser, "terminal length 0")  # para ver todo el output

        while True:
            cmd = input("Ingrese comando (o 'exit' para salir): ")
            if cmd.lower() in ["exit", "salir", "quit"]:
                break
            output = send_command(ser, cmd, delay=1)
            print("📜 Salida del dispositivo:\n", output)

        ser.close()
    except Exception as e:
        print(f"❌ Error: {e}")

# 🔹 Función para configuración inicial desde CSV
def config_mode():
    df = pd.read_csv("C:\\Users\\Dani\\OneDrive\\Escritorio\\Clases Unipoli\\Cuatri 4\\Programacion de Redes\\Apuntes\\VENV\\Data.csv")
    print("\n📂 Dispositivos encontrados en el archivo:")
    print(df)

    # Crear lista de hostnames
    Hostnames = []
    for d, s in zip(df['Device'], df['Serie']):
        initial_d = str(d).strip()[0]
        initial_s = str(s).strip()[:6]
        device_name = initial_d + initial_s
        Hostnames.append(device_name)

    list_device = []
    for p, u, pas, dom, h in zip(df['Port'], df['User'], df['Password'], df['Ip-domain'], Hostnames):
        list_device.append((p, h, u, pas, dom))

    input("Presione ENTER para continuar con la configuración...")

    for idx, (p, h, u, pas, dom) in enumerate(list_device, start=1):
        clear_console()
        print(f"\n➡️ Conecte ahora el dispositivo {idx}: {h} en el puerto {p}")
        input("Presione ENTER cuando el dispositivo esté conectado...")
        configure_device(p, h, u, pas, dom)
        print("=================================================")
        input("Presione ENTER para continuar...")

# 🔹 Menú principal
def main_menu():
    while True:
        clear_console()
        print("=== Menú principal ===")
        print("1️⃣  Enviar comandos manuales")
        print("2️⃣  Aplicar configuración inicial desde CSV")
        print("3️⃣  Salir")
        choice = input("Seleccione una opción: ")

        if choice == "1":
            command_mode()
        elif choice == "2":
            config_mode()
        elif choice == "3":
            print("Saliendo del programa...")
            break
        else:
            print("Opción inválida. Intente de nuevo.")
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
