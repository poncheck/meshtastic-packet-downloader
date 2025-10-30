# Upgrade Guide / Przewodnik Aktualizacji

## Problem z `git pull` po edycji config.yaml?

Jeśli masz konflikt z `config.yaml` podczas `git pull`, wykonaj te kroki:

If you have a conflict with `config.yaml` during `git pull`, follow these steps:

### Rozwiązanie / Solution:

```bash
# 1. Zapisz swoją konfigurację / Backup your configuration
cp config.yaml config.yaml.backup

# 2. Usuń lokalny plik config.yaml / Remove local config.yaml
rm config.yaml

# 3. Pobierz aktualizacje / Pull updates
git pull

# 4. Skopiuj przykładową konfigurację / Copy example config
cp config.example.yaml config.yaml

# 5. Przywróć swoje ustawienia z backupu / Restore your settings from backup
# Skopiuj ustawienia z config.yaml.backup do config.yaml
# Copy settings from config.yaml.backup to config.yaml
nano config.yaml  # lub użyj swojego edytora / or use your editor
```

### Dlaczego to się stało? / Why did this happen?

Od teraz `config.yaml` jest **ignorowany przez git** i nie będzie już powodował konfliktów.
Template konfiguracji znajduje się w `config.example.yaml`.

From now on, `config.yaml` is **ignored by git** and will no longer cause conflicts.
The configuration template is in `config.example.yaml`.

### Nowe zmiany w konfiguracji / New configuration changes:

Najnowsza wersja ma nowy format MQTT (natywny Meshtastic):

The latest version has a new MQTT format (native Meshtastic):

```yaml
mqtt:
  broker: "mqtt.example.com"
  port: 1883
  username: "your_username"
  password: "your_password"
  topic_prefix: "msh/2"          # Nowy format / New format
  channel_name: "LongFast"       # Nazwa kanału / Channel name
  use_json: false                # false=protobuf, true=JSON
  qos: 1
  retain: false
  client_id: "meshtastic_downloader"
```

### Ważne zmiany / Important changes:

- **topic_prefix** zmieniony z `meshtastic/packets` na `msh/2`
- Dodany **channel_name** (np. "LongFast")
- Dodany **use_json** (domyślnie false - wysyła protobuf)

Po aktualizacji dostosuj swoją konfigurację MQTT!

After updating, adjust your MQTT configuration!
