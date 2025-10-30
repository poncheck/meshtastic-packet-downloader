# Meshtastic Packet Downloader

Skrypt do pobierania, dekodowania i przesyłania pakietów Meshtastic z API do serwera MQTT.

Script for downloading, decoding, and forwarding Meshtastic packets from API sources to an MQTT broker.

## Funkcje / Features

- ✅ Pobieranie pakietów z wielu źródeł API / Fetch packets from multiple API sources
- ✅ Dekodowanie pakietów Meshtastic przy użyciu domyślnego klucza / Decode Meshtastic packets using default key
- ✅ Publikacja zdekodowanych pakietów do brokera MQTT / Publish decoded packets to MQTT broker
- ✅ Śledzenie przetworzonych pakietów (brak duplikatów) / Track processed packets (no duplicates)
- ✅ Konfigurowalne źródła danych / Configurable data sources
- ✅ Automatyczne ponowne próby przy błędach / Automatic retry on errors
- ✅ Rotacja logów / Log rotation
- ✅ Obsługa wielu kluczy szyfrowania / Support for multiple encryption keys
- ✅ Narzędzie testowe do podglądu pakietów / Test tool for packet preview (without MQTT)

## Wymagania / Requirements

- Python 3.8 lub nowszy / Python 3.8 or higher
- Dostęp do serwera MQTT / Access to an MQTT broker

## Instalacja / Installation

### Metoda 1: Używając skryptu setup (ZALECANE / RECOMMENDED)

```bash
# Sklonuj repozytorium / Clone the repository
git clone <repository-url>
cd meshtastic-packet-downloader

# Uruchom skrypt setup / Run setup script
./setup.sh

# Aktywuj środowisko wirtualne / Activate virtual environment
source venv/bin/activate
```

### Metoda 2: Instalacja ręczna / Manual installation

1. Sklonuj repozytorium / Clone the repository:
```bash
git clone <repository-url>
cd meshtastic-packet-downloader
```

2. Utwórz wirtualne środowisko Python / Create Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# lub/or: venv\Scripts\activate  # Windows
```

3. Zainstaluj zależności / Install dependencies:
```bash
pip install -r requirements.txt
```

4. Skopiuj i dostosuj konfigurację / Copy and customize the configuration:
```bash
cp config.example.yaml config.yaml
nano config.yaml
```

**WAŻNE / IMPORTANT:** Zawsze aktywuj środowisko wirtualne przed uruchomieniem skryptu!
Always activate the virtual environment before running the script!

## Konfiguracja / Configuration

Edytuj plik `config.yaml` (lub utwórz `config.local.yaml` dla lokalnej konfiguracji):

Edit the `config.yaml` file (or create `config.local.yaml` for local configuration):

### Źródła API / API Sources

```yaml
api_sources:
  - name: "Zachód"
    url: "https://lorastats.pl/API/Zach%C3%B3d/PacketsRaw/JSON"
    enabled: true
  - name: "Inne źródło"
    url: "https://example.com/api/packets"
    enabled: true
```

### Ustawienia MQTT / MQTT Settings

```yaml
mqtt:
  broker: "mqtt.example.com"
  port: 1883
  username: "your_username"
  password: "your_password"
  topic_prefix: "meshtastic/packets"
  qos: 1
  retain: false
  client_id: "meshtastic_downloader"
```

### Klucze szyfrowania / Encryption Keys

```yaml
meshtastic:
  default_key: "AQ=="  # Domyślny klucz Meshtastic / Default Meshtastic key
  additional_keys:
    - "inny_klucz_base64"
```

## Testowanie / Testing

Przed uruchomieniem głównego skryptu, możesz przetestować pobieranie i dekodowanie pakietów bez wysyłania do MQTT:

Before running the main script, you can test packet download and decoding without sending to MQTT:

```bash
# Aktywuj środowisko wirtualne / Activate virtual environment
source venv/bin/activate

# Wyświetl 10 najnowszych pakietów / Display 10 most recent packets
python test_packets.py

# Wyświetl 20 pakietów / Display 20 packets
python test_packets.py --limit 20

# Testuj konkretne źródło / Test specific source
python test_packets.py --source "Zachód"

# Lista wszystkich źródeł / List all sources
python test_packets.py --list-sources

# Pomoc / Help
python test_packets.py --help
```

Narzędzie testowe wyświetla szczegółowe informacje o pakietach:
- ID pakietu i węzłów (from/to)
- Typ wiadomości (TEXT, POSITION, TELEMETRY, etc.)
- Zdekodowaną zawartość (tekst, współrzędne, dane telemetryczne)
- Informacje o sygnale (RSSI, SNR)
- Status deszyfrowania

Test tool displays detailed packet information:
- Packet and node IDs (from/to)
- Message type (TEXT, POSITION, TELEMETRY, etc.)
- Decoded content (text, coordinates, telemetry data)
- Signal information (RSSI, SNR)
- Decryption status

## Uruchomienie / Running

### Standardowe uruchomienie / Standard run:
```bash
# Aktywuj środowisko wirtualne / Activate virtual environment
source venv/bin/activate

# Uruchom skrypt / Run script
python meshtastic_downloader.py
```

### Z alternatywną konfiguracją / With alternative config:
```bash
source venv/bin/activate
python meshtastic_downloader.py config.local.yaml
```

### Jako usługa systemd / As systemd service:

Utwórz plik `/etc/systemd/system/meshtastic-downloader.service`:

Create file `/etc/systemd/system/meshtastic-downloader.service`:

```ini
[Unit]
Description=Meshtastic Packet Downloader
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/meshtastic-packet-downloader
ExecStart=/path/to/meshtastic-packet-downloader/venv/bin/python /path/to/meshtastic-packet-downloader/meshtastic_downloader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Uwaga:** Zmień `your_user` i ścieżki na właściwe wartości!
**Note:** Change `your_user` and paths to appropriate values!

Następnie / Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable meshtastic-downloader
sudo systemctl start meshtastic-downloader
sudo systemctl status meshtastic-downloader
```

## Format danych MQTT / MQTT Data Format

Pakiety są publikowane w **natywnym formacie Meshtastic** (ServiceEnvelope protobuf).

Packets are published in **native Meshtastic format** (ServiceEnvelope protobuf).

### Format Topic / Topic Format

**Protobuf (domyślny / default):**
```
msh/2/c/[channel_name]/[gateway_id]
```

**JSON (opcjonalnie / optional):**
```
msh/2/json/[channel_name]/[gateway_id]
```

Gdzie / Where:
- `msh/2` = Meshtastic wersja 2 protokołu
- `c` = compact (protobuf) lub `json` = JSON format
- `[channel_name]` = nazwa kanału (np. "LongFast")
- `[gateway_id]` = ID gateway który odebrał pakiet (hex, np. "ba0ca350")

### Payload Format

**Protobuf (domyślny):**
Payload to surowy protobuf `ServiceEnvelope` zawierający `MeshPacket` - identyczny format jak natywne urządzenia Meshtastic.

Payload is raw protobuf `ServiceEnvelope` containing `MeshPacket` - identical format to native Meshtastic devices.

**JSON (jeśli `use_json: true` w konfigu):**
Payload to JSON reprezentacja ServiceEnvelope.

Payload is JSON representation of ServiceEnvelope.

### Kompatybilność / Compatibility

Ten format jest **w pełni kompatybilny** z:
- MQTT Explorer
- Meshtastic aplikacjami (Android/iOS/Web)
- mqtt-meshtastic-bridge
- Innymi narzędziami Meshtastic

This format is **fully compatible** with:
- MQTT Explorer
- Meshtastic apps (Android/iOS/Web)
- mqtt-meshtastic-bridge
- Other Meshtastic tools

## Logi / Logs

Logi są zapisywane do:
- Konsola / Console
- Plik `meshtastic_downloader.log` (z rotacją)

Logs are written to:
- Console
- File `meshtastic_downloader.log` (with rotation)

Poziomy logowania / Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Stan przetwarzania / Processing State

Przetworzone pakiety są śledzone w pliku `processed_packets.json`, aby uniknąć duplikatów.

Processed packets are tracked in `processed_packets.json` file to avoid duplicates.

## Rozwiązywanie problemów / Troubleshooting

### Błąd "externally-managed-environment" przy instalacji pakietów
Ten błąd występuje w nowoczesnych wersjach Pythona/Linuxa. **Użyj wirtualnego środowiska** (venv) jak opisano w sekcji instalacji. Nigdy nie używaj `--break-system-packages`!

This error occurs in modern Python/Linux versions. **Use a virtual environment** (venv) as described in the installation section. Never use `--break-system-packages`!

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Błąd połączenia z MQTT / MQTT connection error
Sprawdź ustawienia brokera, użytkownika i hasła w konfiguracji.

Check broker settings, username, and password in configuration.

### Błąd dekodowania pakietów / Packet decoding error
Sprawdź czy używasz prawidłowego klucza szyfrowania.

Check if you're using the correct encryption key.

### API nie zwraca danych / API returns no data
Sprawdź URL źródła i upewnij się, że API jest dostępne.

Check the source URL and ensure the API is accessible.

### Brak modułu "venv"
Jeśli otrzymujesz błąd o braku modułu venv, zainstaluj `python3-venv`:

If you get an error about missing venv module, install `python3-venv`:

```bash
sudo apt install python3-venv python3-full
```

## Kontakt / Contact

- Email: info@meshtastic.info.pl
- Website: https://meshtastic.info.pl

## Licencja / License

MIT License - see LICENSE file for details.
