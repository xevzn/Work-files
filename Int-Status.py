import serial
import serial.tools.list_ports
import time
import pandas as pd
import os
import csv
import sys
import textfsm
from textFSM import FSM

# 🔹 Limpiar pantalla
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

# 🔹 Abrir puerto serial con reintentos
def open_serial(port, retries=3, delay=3):
    for i in range(retries):
        try:
            ser = serial.Serial(port, baudrate=9600, timeout=1)
            time.sleep(5)
            return ser
        except Exception as e:
            print(f"⚠ Error al abrir {port}: {e}")
            time.sleep(delay)
    return None

# 🔹 Enviar comando al router
def send_command(ser, command, delay=1):
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write((command + "\r\n").encode())
        time.sleep(delay)
        output = ser.read(ser.in_waiting).decode(errors="ignore")
        return output
    except Exception as e:
        print(f"❌ Error al enviar comando '{command}': {e}")
        return ""

# 🔹 Obtener número de serie con TextFSM
def get_serial(ser):
    send_command(ser, "terminal length 0")
    output = send_command(ser, "show inventory", delay=2)

    template_path = os.path.join("templates", "cisco_ios_show_inventory.textfsm")
    if not os.path.exists(template_path):
        print(f"❌ No se encontró la plantilla {template_path}")
        return "DESCONOCIDO"

    with open(template_path) as template:
        fsm = textfsm.TextFSM(template)
        results = fsm.ParseText(output)

    if results:
        return results[0][4]  # Columna SN
    return "DESCONOCIDO"

# 🔹 NUEVA opción 3: Guardar estado de interfaces (una línea por dispositivo)
def guardar_status(ser):
    # Obtener número de serie
    send_command(ser, "terminal length 0")
    salida_inventario = send_command(ser, "show inventory", delay=2)
    serie = "DESCONOCIDO"
    for linea in salida_inventario.splitlines():
        if "SN:" in linea:
            serie = linea.split("SN:")[-1].strip()
            break

    # Obtener interfaces Ethernet
    salida_interfaces = send_command(ser, "show ip interface brief", delay=2)
    interfaces = []
    for linea in salida_interfaces.splitlines():
        if any(prefijo in linea for prefijo in ["FastEthernet", "GigabitEthernet", "Ethernet"]):
            partes = linea.split()
            if len(partes) >= 6:
                nombre = partes[0]
                estado = partes[-2]
                protocolo = partes[-1]
                interfaces.append(f"{nombre}:{estado}/{protocolo}")

    # Guardar en CSV una línea por dispositivo
    archivo = "Dispositivos.csv"
    existe = os.path.isfile(archivo)
    with open(archivo, "a", newline="") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["Serie", "Interfaces"])
        writer.writerow([serie, "; ".join(interfaces)])

    print(f"\n✅ Información guardada en {archivo}")
    print(f"Serie detectada: {serie}")
    print("Interfaces encontradas:")
    for i in interfaces:
        print("  -", i)

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
        print(f"🔎 Número de serie: {serial_num}")

        # Aquí irían interfaces y guardado en CSV (omitido porque no pediste modificar opción 2)

        # Configuración SSH básica
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
        print(f"❌ Error en {hostname}: {e}")
        return False

# 🔹 Modo manual
def manual_command_mode():
    clear_console()
    print("="*60)
    print("🔧 Modo de comandos manuales")
    print("="*60)
    ports = list_ports()
    if not ports:
        input("No hay puertos disponibles. Presione ENTER...")
        return
    port = input("Ingrese el puerto serial (ej: COM3): ").strip()
    ser = open_serial(port)
    if not ser:
        input("No se pudo abrir el puerto. ENTER para regresar...")
        return
    print("Conectado. Escriba 'exit' para salir del modo manual.")
    while True:
        cmd = input("Comando> ").strip()
        if cmd.lower() == "exit":
            break
        if cmd:
            respuesta = send_command(ser, cmd, delay=2)
            print(f"Respuesta:\n{respuesta}")
    ser.close()
    input("Sesión finalizada. ENTER para regresar...")

# 🔹 Modo configuración inicial
def initial_config_mode(list_device):
    for idx, (p, h, u, pas, dom) in enumerate(list_device, start=1):
        clear_console()
        print("="*60)
        print(f"➡️ Configuración del dispositivo {idx}/{len(list_device)}: {h}")
        print("="*60)
        list_ports()
        input(f"\n🔗 Conecte '{h}' al puerto '{p}' y presione ENTER...")
        configure_device(p, h, u, pas, dom)
        input("ENTER para continuar con el siguiente dispositivo...")

# 🔹 Modo estado de interfaces (MODIFICADO para usar guardar_status)
def interface_status_mode(list_device):
    clear_console()
    print("="*60)
    print("🔎 Estado de interfaces y protocolos (resumen por dispositivo)")
    print("="*60)
    ports = list_ports()
    if not ports:
        input("No hay puertos disponibles. Presione ENTER...")
        return
    port = input("Ingrese el puerto serial (ej: COM3): ").strip()
    ser = open_serial(port)
    if not ser:
        input("❌ No se pudo abrir el puerto. ENTER para regresar...")
        return

    guardar_status(ser)  # ✅ Aquí guardamos serie + interfaces
    ser.close()
    input("\nProceso finalizado. ENTER para regresar al menú...")

# 🔹 FSM principal
def main_fsm(list_device):
    fsm = FSM('MENU')
    fsm.add_state('MENU')
    fsm.add_state('MANUAL')
    fsm.add_state('CONFIG')
    fsm.add_state('STATUS')
    fsm.add_state('EXIT')

    fsm.add_transition('MENU', '1', 'MANUAL')
    fsm.add_transition('MENU', '2', 'CONFIG')
    fsm.add_transition('MENU', '3', 'STATUS')
    fsm.add_transition('MENU', '0', 'EXIT')
    fsm.add_transition('MANUAL', 'done', 'MENU')
    fsm.add_transition('CONFIG', 'done', 'MENU')
    fsm.add_transition('STATUS', 'done', 'MENU')

    while fsm.state != 'EXIT':
        if fsm.state == 'MENU':
            clear_console()
            print("="*60)
            print("   MENÚ PRINCIPAL - Gestión de Dispositivos Cisco")
            print("="*60)
            print("1. Modo comandos manuales")
            print("2. Configuración inicial")
            print("3. Estado de interfaces")
            print("0. Salir")
            opcion = input("Seleccione: ").strip()
            if opcion in ['1','2','3','0']:
                fsm.input(opcion)
            else:
                input("Opción no válida. ENTER para continuar...")
        elif fsm.state == 'MANUAL':
            manual_command_mode()
            fsm.input('done')
        elif fsm.state == 'CONFIG':
            initial_config_mode(list_device)
            fsm.input('done')
        elif fsm.state == 'STATUS':
            interface_status_mode(list_device)
            fsm.input('done')

if __name__ == "__main__":
    csv_path = "Data.csv"
    required_columns = {'Device','Serie','Port','User','Password','Ip-domain'}
    if not os.path.isfile(csv_path):
        print(f"❌ El archivo '{csv_path}' no existe.")
        sys.exit(1)
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        sys.exit(1)
    if not required_columns.issubset(df.columns):
        print(f"❌ El CSV debe contener: {', '.join(required_columns)}")
        sys.exit(1)

    Hostnames = []  
    for d, s in zip(df['Device'], df['Serie']):
        Hostnames.append(str(d).strip()[0] + str(s).strip())
    list_device = [(p,h,u,pas,dom) for p,h,u,pas,dom in zip(df['Port'], Hostnames, df['User'], df['Password'], df['Ip-domain'])]

    main_fsm(list_device)
