#!/usr/bin/env python3
"""
Meshtastic Packet Downloader
Downloads packets from API sources, decodes them, and publishes to MQTT broker.
"""

import json
import logging
import logging.handlers
import time
import sys
from typing import Dict, List, Set, Any, Optional
from pathlib import Path
from base64 import b64decode
from datetime import datetime

import requests
import yaml
import paho.mqtt.client as mqtt
from meshtastic.protobuf import mesh_pb2, mqtt_pb2, portnums_pb2
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class MeshtasticDownloader:
    """Main class for downloading and processing Meshtastic packets."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the downloader with configuration."""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.logger.info("Meshtastic Packet Downloader starting...")

        # Load processed packets state
        self.state_file = Path(self.config['processing']['state_file'])
        self.processed_packets: Set[str] = self._load_state()

        # Initialize MQTT client
        self.mqtt_client = self._setup_mqtt()

        # Decryption keys
        self.encryption_keys = [
            b64decode(self.config['meshtastic']['default_key'])
        ] + [
            b64decode(key) for key in self.config['meshtastic'].get('additional_keys', [])
        ]

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config['logging']
        log_level = getattr(logging, log_config['level'].upper())

        # Create logger
        self.logger = logging.getLogger('MeshtasticDownloader')
        self.logger.setLevel(log_level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_config['file'],
            maxBytes=log_config['max_file_size'],
            backupCount=log_config['backup_count']
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(console_format)
        self.logger.addHandler(file_handler)

    def _load_state(self) -> Set[str]:
        """Load processed packets state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded {len(data)} processed packet IDs from state file")
                    return set(data)
            except Exception as e:
                self.logger.error(f"Error loading state file: {e}")
        return set()

    def _save_state(self):
        """Save processed packets state to file."""
        try:
            # Limit state size
            max_size = self.config['processing']['max_state_size']
            if len(self.processed_packets) > max_size:
                # Keep only the most recent entries (convert to list, slice, back to set)
                self.processed_packets = set(list(self.processed_packets)[-max_size:])

            with open(self.state_file, 'w') as f:
                json.dump(list(self.processed_packets), f)
            self.logger.debug(f"Saved {len(self.processed_packets)} packet IDs to state file")
        except Exception as e:
            self.logger.error(f"Error saving state file: {e}")

    def _setup_mqtt(self) -> mqtt.Client:
        """Setup MQTT client connection."""
        mqtt_config = self.config['mqtt']

        client = mqtt.Client(client_id=mqtt_config['client_id'])

        if mqtt_config.get('username') and mqtt_config.get('password'):
            client.username_pw_set(mqtt_config['username'], mqtt_config['password'])

        # Set up callbacks
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.logger.info("Connected to MQTT broker")
            else:
                self.logger.error(f"Failed to connect to MQTT broker: {rc}")

        def on_disconnect(client, userdata, rc):
            if rc != 0:
                self.logger.warning(f"Unexpected MQTT disconnection: {rc}")

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect

        try:
            client.connect(mqtt_config['broker'], mqtt_config['port'], 60)
            client.loop_start()
        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            raise

        return client

    def _decrypt_packet(self, packet_bytes: bytes, nonce: bytes) -> Optional[bytes]:
        """Attempt to decrypt a packet with available keys."""
        for key in self.encryption_keys:
            try:
                cipher = Cipher(
                    algorithms.AES(key),
                    modes.CTR(nonce),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                decrypted = decryptor.update(packet_bytes) + decryptor.finalize()
                return decrypted
            except Exception as e:
                self.logger.debug(f"Decryption failed with key: {e}")
                continue
        return None

    def _process_packet(self, packet_data: Dict[str, Any], source_name: str) -> bool:
        """Process a single packet: decode and publish to MQTT."""
        try:
            # Generate unique packet ID (API uses 'Time' with capital T, 'Data' with capital D)
            time_val = packet_data.get('Time') or packet_data.get('timestamp', '')
            data_id = packet_data.get('id', '') or packet_data.get('Gateway', '')
            packet_id = f"{source_name}_{data_id}_{time_val}"

            # Skip if already processed
            if packet_id in self.processed_packets:
                self.logger.debug(f"Skipping already processed packet: {packet_id}")
                return False

            # Extract packet information
            raw_data = packet_data.get('Data') or packet_data.get('data')
            if not raw_data:
                self.logger.warning(f"No Data in packet: {packet_id}")
                return False

            # Try to decode as ServiceEnvelope (MQTT format)
            try:
                service_envelope = mqtt_pb2.ServiceEnvelope()
                service_envelope.ParseFromString(b64decode(raw_data))

                # Extract the mesh packet
                mesh_packet = service_envelope.packet

                # If encrypted, try to decrypt
                if mesh_packet.encrypted:
                    # Create nonce from packet ID and sender
                    nonce_bytes = mesh_packet.id.to_bytes(8, 'little') + mesh_packet.from_node.to_bytes(8, 'little')

                    decrypted = self._decrypt_packet(mesh_packet.encrypted, nonce_bytes)
                    if decrypted:
                        # Parse decrypted data
                        data_message = mesh_pb2.Data()
                        data_message.ParseFromString(decrypted)
                        mesh_packet.decoded.CopyFrom(data_message)
                        self.logger.debug(f"Successfully decrypted packet {packet_id}")
                    else:
                        self.logger.warning(f"Failed to decrypt packet {packet_id}")

                # Prepare packet for publishing
                packet_info = {
                    'source': source_name,
                    'id': mesh_packet.id,
                    'from': mesh_packet.from_node,
                    'to': mesh_packet.to_node,
                    'timestamp': packet_data.get('Time') or packet_data.get('timestamp', ''),
                    'gateway': packet_data.get('Gateway'),
                    'channel': mesh_packet.channel,
                    'hop_limit': mesh_packet.hop_limit,
                    'want_ack': mesh_packet.want_ack,
                    'rssi': packet_data.get('rssi') or packet_data.get('RSSI'),
                    'snr': packet_data.get('snr') or packet_data.get('SNR'),
                }

                # Add decoded data if available
                if mesh_packet.HasField('decoded'):
                    packet_info['decoded'] = {
                        'portnum': portnums_pb2.PortNum.Name(mesh_packet.decoded.portnum),
                        'payload': mesh_packet.decoded.payload.hex() if mesh_packet.decoded.payload else None,
                    }

                # Publish to MQTT
                topic = f"{self.config['mqtt']['topic_prefix']}/{hex(mesh_packet.from_node)[2:]}"
                payload = json.dumps(packet_info, indent=2)

                self.mqtt_client.publish(
                    topic,
                    payload,
                    qos=self.config['mqtt']['qos'],
                    retain=self.config['mqtt']['retain']
                )

                self.logger.info(f"Published packet {packet_id} to {topic}")

                # Mark as processed
                self.processed_packets.add(packet_id)
                return True

            except Exception as e:
                self.logger.error(f"Error processing packet {packet_id}: {e}", exc_info=True)
                return False

        except Exception as e:
            self.logger.error(f"Error in packet processing: {e}", exc_info=True)
            return False

    def _fetch_packets(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch packets from an API source."""
        api_settings = self.config['api_settings']
        headers = {
            'User-Agent': api_settings['user_agent']
        }

        retries = 0
        while retries < api_settings['retry_attempts']:
            try:
                self.logger.debug(f"Fetching packets from {source['name']}")
                response = requests.get(
                    source['url'],
                    headers=headers,
                    timeout=api_settings['timeout']
                )
                response.raise_for_status()

                data = response.json()
                self.logger.info(f"Fetched {len(data) if isinstance(data, list) else 1} packets from {source['name']}")

                # Ensure data is a list
                if isinstance(data, dict):
                    data = [data]

                return data

            except Exception as e:
                retries += 1
                self.logger.error(f"Error fetching from {source['name']} (attempt {retries}): {e}")
                if retries < api_settings['retry_attempts']:
                    time.sleep(api_settings['retry_delay'])
                else:
                    self.logger.error(f"Failed to fetch from {source['name']} after {retries} attempts")
                    return []

    def run(self):
        """Main run loop."""
        poll_interval = self.config['processing']['poll_interval']

        self.logger.info("Starting main loop...")

        try:
            while True:
                for source in self.config['api_sources']:
                    if not source.get('enabled', True):
                        continue

                    packets = self._fetch_packets(source)
                    processed_count = 0

                    for packet in packets:
                        if self._process_packet(packet, source['name']):
                            processed_count += 1

                    if processed_count > 0:
                        self.logger.info(f"Processed {processed_count} new packets from {source['name']}")
                        self._save_state()

                self.logger.debug(f"Sleeping for {poll_interval} seconds...")
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            self._save_state()
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            sys.exit(0)


def main():
    """Main entry point."""
    downloader = MeshtasticDownloader()
    downloader.run()


if __name__ == "__main__":
    main()
