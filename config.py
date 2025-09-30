import serial
import serial.tools.list_ports
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

# 🔹 Mostrar puertos disponibles
def list_ports():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    print("\n" + "="*50)
    print(f"🔌 Puertos disponibles: {', '.join(ports) if ports else 'Ninguno encontrado'}")
    print("="*50)
    return ports

# 🔹 Intentar abrir el puerto con reintentos
def open_serial(port, retries=3, delay=3):
    for i in range(retries):
        try:
            ser = serial.Serial(port, baudrate=9600, timeout=1)
            time.sleep(5)  # darle tiempo al adaptador
            return ser
        except PermissionError as e:
            print(f"⚠ Puerto ocupado o no listo ({e}). Reintentando {i+1}/{retries}...")
            time.sleep(delay)
        except Exception as e:
            print(f"❌ Error inesperado al abrir {port}: {e}")
            time.sleep(delay)
    return None

# 🔹 Enviar comando al router
def send_command(ser, command, delay=1):
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write((command + "\r\n").encode())  # CRLF
        time.sleep(delay)
        output = ser.read(ser.in_waiting).decode(errors="ignore")
        return output
    except Exception as e:
        print(f"❌ Error al enviar comando '{command}': {e}")
        return ""

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
        ser = open_serial(port)
        if not ser:
            print(f"❌ No se pudo abrir el puerto {port}. Saltando {hostname}.")
            return False

        print(f"\n🔗 Conectado al dispositivo en {port} ({hostname})")

        # Obtener número de serie
        serial_num = get_serial(ser)
        if not serial_num:
            print("⚠ No se pudo obtener el número de serie. Saltando configuración.")
            ser.close()
            return False
        else: 
            print(f"🔎 Número de serie encontrado: {serial_num}")

        # Verificar coincidencia completa de serie
        if hostname[1:] != serial_num:
            print(f"⚠ La serie del dispositivo ({serial_num}) no coincide con la del CSV ({hostname[1:]}). Saltando configuración.")
            ser.close()
            return False

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
        return True

    except Exception as e:
        print(f"❌ Error al configurar el dispositivo {hostname}: {e}")
        return False

# 🔹 Main
if __name__ == "__main__":
    clear_console()
    print("="*60)
    print("📂 Leyendo archivo de dispositivos...")
    print("="*60)
    df = pd.read_csv("C:\\Users\\Dani\\OneDrive\\Escritorio\\Clases Unipoli\\Cuatri 4\\Programacion de Redes\\Apuntes\\VENV\\Data.csv")
    print("\n📋 Dispositivos encontrados en el archivo:")
    print(df.to_string(index=False))

    # Crear lista de hostnames a partir de Device + Serie completa
    Hostnames = []
    for d, s in zip(df['Device'], df['Serie']):
        initial_d = str(d).strip()[0]
        initial_s = str(s).strip()  # toda la serie
        device_name = initial_d + initial_s
        Hostnames.append(device_name)

    # Lista de configuraciones
    list_device = []
    for p, u, pas, dom, h in zip(df['Port'], df['User'], df['Password'], df['Ip-domain'], Hostnames):
        list_device.append((p, h, u, pas, dom))

    print("\n" + "="*60)
    print("📋 Lista de dispositivos y sus configuraciones:")
    print("="*60)
    for idx, item in enumerate(list_device, 1):
        print(f"{idx}. Puerto: {item[0]} | Hostname: {item[1]} | Usuario: {item[2]} | Dominio: {item[4]}")
    input("\nPresione ENTER para continuar...")

    # Mostrar puertos disponibles antes de iniciar
    list_ports()
    input("\nVerifique los puertos disponibles. Presione ENTER para iniciar la configuración...")

    # Registros de éxito/fallo
    configured_devices = []
    skipped_devices = []

    # Configurar dispositivos uno por uno
    for idx, (p, h, u, pas, dom) in enumerate(list_device, start=1):
        clear_console()
        print("="*60)
        print(f"➡️  Configuración del dispositivo {idx}/{len(list_device)}: {h}")
        print("="*60)
        list_ports()
        print(f"\n🔗 Por favor, conecte el dispositivo '{h}' al puerto '{p}'.")
        print("🔄 Si es necesario, desconecte y vuelva a conectar la conexión serial.")
        input("Presione ENTER cuando el dispositivo esté conectado...")

        success = configure_device(p, h, u, pas, dom)
        if success:
            configured_devices.append(h)
        else:
            skipped_devices.append(h)

        print("\n" + "-"*60)
        input("Presione ENTER para continuar con el siguiente dispositivo...")

    # Mostrar resumen final
    clear_console()
    print("="*60)
    print("📊 Resumen de la configuración:")
    print("="*60)
    print(f"✅ Dispositivos configurados ({len(configured_devices)}):")
    for d in configured_devices:
        print(f"   - {d}")
    print(f"\n⚠ Dispositivos saltados ({len(skipped_devices)}):")
    for d in skipped_devices:
        print(f"   - {d}")
    print("\nProceso finalizado. Puede cerrar la ventana.")