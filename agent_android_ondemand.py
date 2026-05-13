#!/usr/bin/env python3
"""
FamilyControl Agent Android (Termux)
Si collega al backend Railway e invia dati
"""

import os
import json
import time
import subprocess
import requests
import socket
from datetime import datetime

# ==================== CONFIGURAZIONE ====================
# ⚠️ CAMBIA CON IL TUO BACKEND URL
BACKEND_URL = "https://familycontrol-backend-production.up.railway.app"

# Credenziali per autenticazione
USERNAME = "admin"
PASSWORD = "admin123"

# ID dispositivo (generato automaticamente)
try:
    DEVICE_ID = subprocess.check_output(['getprop', 'ro.serialno']).decode().strip()
    if not DEVICE_ID or DEVICE_ID == "unknown":
        DEVICE_ID = socket.gethostname()
except:
    DEVICE_ID = socket.gethostname()

DEVICE_NAME = f"Android_{DEVICE_ID[:8]}"
DEVICE_TYPE = "android"

# ==================== FUNZIONI ====================

def get_token():
    """Ottiene token JWT dal backend"""
    try:
        print("🔐 Autenticazione in corso...")
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            token = response.json().get("token")
            print("✅ Token ottenuto")
            return token
        else:
            print(f"❌ Login fallito: {response.status_code}")
            if response.status_code == 401:
                print("   Verifica username/password nel database")
            return None
    except requests.exceptions.ConnectionError:
        print(f"❌ Impossibile connettersi a {BACKEND_URL}")
        print("   Verifica che il backend sia online")
        return None
    except Exception as e:
        print(f"❌ Errore login: {e}")
        return None

def register_device(token):
    """Registra il dispositivo sul backend"""
    try:
        print("📝 Registrazione dispositivo...")
        response = requests.post(
            f"{BACKEND_URL}/api/devices/register",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "deviceId": DEVICE_ID,
                "deviceName": DEVICE_NAME,
                "deviceType": DEVICE_TYPE
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ Dispositivo registrato: {DEVICE_NAME}")
            print(f"   ID: {DEVICE_ID}")
            return True
        else:
            print(f"❌ Registrazione fallita: {response.status_code}")
            if response.status_code == 401:
                print("   Token scaduto o non valido")
            return False
    except Exception as e:
        print(f"❌ Errore registrazione: {e}")
        return False

def get_battery_info():
    """Ottiene info batteria"""
    try:
        result = subprocess.check_output(['dumpsys', 'battery']).decode()
        battery = {}
        
        for line in result.split('\n'):
            if 'level:' in line:
                battery['level'] = int(line.split(':')[1].strip())
            if 'temperature:' in line:
                temp = int(line.split(':')[1].strip()) / 10
                battery['temperature'] = f"{temp}°C"
            if 'status:' in line:
                status_codes = {
                    '1': 'unknown', 
                    '2': 'charging', 
                    '3': 'discharging', 
                    '4': 'not charging', 
                    '5': 'full'
                }
                code = line.split(':')[1].strip()
                battery['status'] = status_codes.get(code, code)
            if 'health:' in line:
                health_codes = {
                    '1': 'unknown', '2': 'good', '3': 'overheat',
                    '4': 'dead', '5': 'over voltage', '6': 'unspecified failure', '7': 'cold'
                }
                code = line.split(':')[1].strip()
                battery['health'] = health_codes.get(code, code)
        
        return battery if battery else {'error': 'Battery info non disponibile'}
    except Exception as e:
        return {'error': f'Errore batteria: {str(e)}'}

def get_device_info():
    """Ottiene info dispositivo"""
    try:
        brand = subprocess.check_output(['getprop', 'ro.product.brand']).decode().strip()
        model = subprocess.check_output(['getprop', 'ro.product.model']).decode().strip()
        android_version = subprocess.check_output(['getprop', 'ro.build.version.release']).decode().strip()
        sdk_version = subprocess.check_output(['getprop', 'ro.build.version.sdk']).decode().strip()
        
        return {
            'brand': brand,
            'model': model,
            'android_version': android_version,
            'sdk_version': sdk_version,
            'device_id': DEVICE_ID
        }
    except Exception as e:
        return {'error': f'Impossibile ottenere info: {str(e)}'}

def get_installed_apps():
    """Ottiene lista delle app installate (prime 50)"""
    try:
        result = subprocess.check_output(['pm', 'list', 'packages'], stderr=subprocess.DEVNULL).decode()
        apps = [line.replace('package:', '').strip() for line in result.split('\n') if 'package:' in line]
        # Restituisce solo le prime 50 per non appesantire
        return apps[:50]
    except Exception as e:
        return [f'Errore: {str(e)}']

def send_data(token, data_type, data_content):
    """Invia dati al backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/devices/{DEVICE_ID}/data",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "dataType": data_type,
                "dataContent": data_content
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"  📤 {data_type} inviato")
            return True
        else:
            print(f"  ⚠️ Errore invio {data_type}: {response.status_code}")
            if response.status_code == 404:
                print(f"     API endpoint non trovato. Verifica il backend.")
            return False
    except Exception as e:
        print(f"  ❌ Errore invio: {e}")
        return False

def check_commands(token):
    """Controlla comandi pendenti per il dispositivo"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/devices/{DEVICE_ID}/commands",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            commands = response.json()
            for cmd in commands:
                print(f"  📡 Comando ricevuto: {cmd.get('command')}")
                
                # Esegui il comando
                result = execute_command(cmd.get('command'))
                
                # Segna come completato
                requests.patch(
                    f"{BACKEND_URL}/api/commands/{cmd.get('id')}",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"status": "completed", "result": result},
                    timeout=5
                )
        return True
    except Exception as e:
        print(f"  ⚠️ Errore comandi: {e}")
        return False

def execute_command(command):
    """Esegue un comando sul dispositivo"""
    try:
        if command == "get_battery":
            return get_battery_info()
        elif command == "get_device_info":
            return get_device_info()
        elif command == "get_apps":
            return get_installed_apps()
        elif command == "lock_device":
            # Blocca schermo (richiede permessi)
            subprocess.run(['input', 'keyevent', '26'], capture_output=True)
            return {"status": "locked"}
        elif command == "take_screenshot":
            # Screenshot (richiede permessi)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"/sdcard/screenshot_{timestamp}.png"
            subprocess.run(['screencap', '-p', path], capture_output=True)
            return {"status": "screenshot_taken", "path": path}
        else:
            return {"error": f"Comando sconosciuto: {command}"}
    except Exception as e:
        return {"error": str(e)}

def update_status(token, status):
    """Aggiorna lo stato del dispositivo"""
    try:
        requests.patch(
            f"{BACKEND_URL}/api/devices/{DEVICE_ID}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": status},
            timeout=5
        )
    except:
        pass

# ==================== MAIN ====================

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║     FamilyControl Agent Android (Termux)                  ║
║     Monitoraggio dispositivi personali                    ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    print(f"📡 Backend: {BACKEND_URL}")
    print(f"🔑 Username: {USERNAME}")
    
    # Ottieni token
    token = get_token()
    if not token:
        print("\n❌ Impossibile autenticarsi. Riprova tra 10 secondi...")
        time.sleep(10)
        return
    
    # Registra dispositivo
    if not register_device(token):
        print("⚠️ Registrazione fallita, continuo lo stesso...")
    
    print(f"\n🚀 Dispositivo: {DEVICE_NAME}")
    print(f"🆔 ID: {DEVICE_ID}")
    print(f"📱 Tipo: {DEVICE_TYPE}")
    
    # Invia info dispositivo subito
    print(f"\n📡 Invio info iniziali...")
    device_info = get_device_info()
    send_data(token, "device_info", device_info)
    
    # Invia lista app (opzionale, commenta se troppo pesante)
    # apps = get_installed_apps()
    # send_data(token, "installed_apps", apps)
    
    print(f"\n🔄 Avvio monitoraggio (invio ogni 60 secondi)")
    print(f"   Premi Ctrl+C per fermare\n")
    
    counter = 0
    # Loop principale
    try:
        while True:
            counter += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Ciclo #{counter}")
            
            # Invia batteria
            battery = get_battery_info()
            send_data(token, "battery", battery)
            
            # Aggiorna stato
            update_status(token, "online")
            
            # Controlla comandi
            check_commands(token)
            
            # Attesa prima del prossimo ciclo
            print(f"   Attesa 60 secondi...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Agent fermato manualmente")
        update_status(token, "offline")
        print("👋 Arrivederci!")

if __name__ == "__main__":
    main()
