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

## Wymagania / Requirements

- Python 3.8 lub nowszy / Python 3.8 or higher
- Dostęp do serwera MQTT / Access to an MQTT broker

## Instalacja / Installation

1. Sklonuj repozytorium / Clone the repository:
```bash
git clone <repository-url>
cd meshtastic-packet-downloader
```

2. Zainstaluj zależności / Install dependencies:
```bash
pip install -r requirements.txt
```

3. Skopiuj i dostosuj konfigurację / Copy and customize the configuration:
```bash
cp config.yaml config.local.yaml
nano config.local.yaml
```

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

## Uruchomienie / Running

### Standardowe uruchomienie / Standard run:
```bash
python3 meshtastic_downloader.py
```

### Z alternatywną konfiguracją / With alternative config:
```bash
python3 meshtastic_downloader.py config.local.yaml
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
ExecStart=/usr/bin/python3 /path/to/meshtastic-packet-downloader/meshtastic_downloader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Następnie / Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable meshtastic-downloader
sudo systemctl start meshtastic-downloader
sudo systemctl status meshtastic-downloader
```

## Format danych MQTT / MQTT Data Format

Pakiety są publikowane na topic: `{topic_prefix}/{node_id}`

Packets are published to topic: `{topic_prefix}/{node_id}`

Przykładowy payload / Example payload:
```json
{
  "source": "Zachód",
  "id": 123456789,
  "from": 862947392,
  "to": 4294967295,
  "timestamp": "2025-10-30T12:00:00Z",
  "channel": 0,
  "hop_limit": 3,
  "want_ack": false,
  "rssi": -90,
  "snr": 8.5,
  "decoded": {
    "portnum": "TEXT_MESSAGE_APP",
    "payload": "48656c6c6f"
  }
}
```

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

### Błąd połączenia z MQTT / MQTT connection error
Sprawdź ustawienia brokera, użytkownika i hasła w konfiguracji.

Check broker settings, username, and password in configuration.

### Błąd dekodowania pakietów / Packet decoding error
Sprawdź czy używasz prawidłowego klucza szyfrowania.

Check if you're using the correct encryption key.

### API nie zwraca danych / API returns no data
Sprawdź URL źródła i upewnij się, że API jest dostępne.

Check the source URL and ensure the API is accessible.

## Kontakt / Contact

- Email: info@meshtastic.info.pl
- Website: https://meshtastic.info.pl

## Licencja / License

MIT License - see LICENSE file for details.
