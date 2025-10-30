#!/usr/bin/env python3
"""
Meshtastic Packet Tester
Test tool to fetch and display packets without sending to MQTT.
"""

import json
import sys
import argparse
import traceback
from typing import Dict, List, Any, Optional
from pathlib import Path
from base64 import b64decode
from datetime import datetime

import requests
import yaml
from meshtastic.protobuf import mesh_pb2, mqtt_pb2, portnums_pb2
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box


class PacketTester:
    """Test tool for Meshtastic packets."""

    def __init__(self, config_path: str = "config.yaml", debug: bool = False):
        """Initialize the tester with configuration."""
        self.config = self._load_config(config_path)
        self.console = Console()
        self.debug = debug

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
            except Exception:
                continue
        return None

    def _fetch_packets(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch packets from an API source."""
        api_settings = self.config['api_settings']
        headers = {
            'User-Agent': api_settings['user_agent']
        }

        try:
            self.console.print(f"\n[cyan]Fetching packets from:[/cyan] {source['name']}")
            self.console.print(f"[dim]URL: {source['url']}[/dim]")

            response = requests.get(
                source['url'],
                headers=headers,
                timeout=api_settings['timeout']
            )
            response.raise_for_status()

            data = response.json()

            # Ensure data is a list
            if isinstance(data, dict):
                data = [data]

            self.console.print(f"[green]✓[/green] Fetched {len(data)} packets\n")
            return data

        except Exception as e:
            self.console.print(f"[red]✗ Error fetching from {source['name']}: {e}[/red]")
            return []

    def _format_node_id(self, node_id: int) -> str:
        """Format node ID as hex string."""
        return f"!{hex(node_id)[2:]}"

    def _get_portnum_name(self, portnum: int) -> str:
        """Get human-readable portnum name."""
        try:
            return portnums_pb2.PortNum.Name(portnum)
        except:
            return f"UNKNOWN_{portnum}"

    def _decode_payload(self, payload: bytes, portnum: int) -> str:
        """Try to decode payload based on portnum."""
        if not payload:
            return "[dim]<empty>[/dim]"

        portnum_name = self._get_portnum_name(portnum)

        # Try to decode text messages
        if "TEXT_MESSAGE" in portnum_name:
            try:
                return payload.decode('utf-8')
            except:
                pass

        # Try to decode position data
        elif "POSITION" in portnum_name:
            try:
                position = mesh_pb2.Position()
                position.ParseFromString(payload)
                lat = position.latitude_i * 1e-7
                lon = position.longitude_i * 1e-7
                alt = position.altitude
                return f"Lat: {lat:.6f}, Lon: {lon:.6f}, Alt: {alt}m"
            except:
                pass

        # Try to decode node info
        elif "NODEINFO" in portnum_name:
            try:
                user = mesh_pb2.User()
                user.ParseFromString(payload)
                return f"ID: {user.id}, Name: {user.long_name}, Short: {user.short_name}"
            except:
                pass

        # Try to decode telemetry
        elif "TELEMETRY" in portnum_name:
            try:
                telemetry = mesh_pb2.Telemetry()
                telemetry.ParseFromString(payload)

                parts = []

                # Device metrics
                if telemetry.HasField('device_metrics'):
                    dm = telemetry.device_metrics
                    if dm.battery_level > 0:
                        parts.append(f"Battery: {dm.battery_level}%")
                    if dm.voltage > 0:
                        parts.append(f"Voltage: {dm.voltage:.2f}V")
                    if dm.channel_utilization > 0:
                        parts.append(f"Ch.Util: {dm.channel_utilization:.1f}%")
                    if dm.air_util_tx > 0:
                        parts.append(f"AirUtil: {dm.air_util_tx:.1f}%")

                # Environment metrics
                if telemetry.HasField('environment_metrics'):
                    em = telemetry.environment_metrics
                    if em.temperature != 0:
                        parts.append(f"Temp: {em.temperature:.1f}°C")
                    if em.relative_humidity != 0:
                        parts.append(f"Humidity: {em.relative_humidity:.1f}%")
                    if em.barometric_pressure != 0:
                        parts.append(f"Pressure: {em.barometric_pressure:.1f}hPa")
                    if em.voltage != 0:
                        parts.append(f"Voltage: {em.voltage:.2f}V")

                # Power metrics
                if telemetry.HasField('power_metrics'):
                    pm = telemetry.power_metrics
                    if pm.ch1_voltage > 0:
                        parts.append(f"CH1: {pm.ch1_voltage:.2f}V")
                    if pm.ch1_current > 0:
                        parts.append(f"CH1 Current: {pm.ch1_current:.2f}mA")

                # Time field
                if telemetry.time > 0:
                    parts.append(f"Time: {telemetry.time}")

                if parts:
                    return ", ".join(parts)
                else:
                    # If no fields found, show structure in debug
                    return f"<Telemetry: {str(telemetry)[:100]}>"

            except Exception as e:
                if self.debug:
                    self.console.print(f"[yellow]Telemetry decode error: {e}[/yellow]")
                pass

        # Default: show hex
        hex_str = payload.hex()
        if len(hex_str) > 100:
            return f"{hex_str[:100]}... ({len(payload)} bytes)"
        return f"{hex_str} ({len(payload)} bytes)"

    def _display_packet(self, packet_data: Dict[str, Any], source_name: str, index: int):
        """Display a single packet in a nice format."""
        try:
            # Debug mode: show raw packet structure
            if self.debug:
                self.console.print(f"\n[yellow]━━━ Debug: Raw Packet #{index + 1} ━━━[/yellow]")
                self.console.print(Panel(
                    Syntax(json.dumps(packet_data, indent=2, default=str), "json", theme="monokai"),
                    title="Raw Packet Data",
                    border_style="yellow"
                ))
                self.console.print(f"[dim]Keys in packet: {list(packet_data.keys())}[/dim]\n")

            # API uses 'Data' with capital D
            raw_data = packet_data.get('Data') or packet_data.get('data')
            if not raw_data:
                if self.debug:
                    self.console.print(f"[red]No 'Data' or 'data' field in packet[/red]")
                return

            # Decode the base64 data
            decoded_bytes = b64decode(raw_data)

            if self.debug:
                self.console.print(f"\n[cyan]Base64 decoded length: {len(decoded_bytes)} bytes[/cyan]")
                self.console.print(f"[dim]First 50 bytes (hex): {decoded_bytes[:50].hex()}[/dim]\n")

            # Try to decode - first as direct MeshPacket, then as ServiceEnvelope
            mesh_packet = None
            decode_method = None

            # Try 1: Direct MeshPacket
            try:
                mesh_packet = mesh_pb2.MeshPacket()
                mesh_packet.ParseFromString(decoded_bytes)
                decode_method = "MeshPacket (direct)"

                if self.debug:
                    self.console.print("[green]✓ Successfully decoded as direct MeshPacket[/green]")
                    self.console.print("\n[cyan]━━━ Decoded MeshPacket ━━━[/cyan]")
                    self.console.print(Panel(
                        str(mesh_packet),
                        title="MeshPacket (Protobuf)",
                        border_style="cyan"
                    ))
            except Exception as e:
                if self.debug:
                    self.console.print(f"[yellow]Failed to decode as direct MeshPacket: {e}[/yellow]")

                # Try 2: ServiceEnvelope
                try:
                    service_envelope = mqtt_pb2.ServiceEnvelope()
                    service_envelope.ParseFromString(decoded_bytes)
                    mesh_packet = service_envelope.packet
                    decode_method = "ServiceEnvelope"

                    if self.debug:
                        self.console.print("[green]✓ Successfully decoded as ServiceEnvelope[/green]")
                        self.console.print("\n[cyan]━━━ Decoded ServiceEnvelope ━━━[/cyan]")
                        self.console.print(Panel(
                            str(service_envelope),
                            title="ServiceEnvelope (Protobuf)",
                            border_style="cyan"
                        ))
                except Exception as e2:
                    if self.debug:
                        self.console.print(f"[red]Failed to decode as ServiceEnvelope: {e2}[/red]")
                    raise Exception(f"Could not decode packet as MeshPacket or ServiceEnvelope")

            if mesh_packet is None:
                return

            # Now process the decoded packet
            try:
                # If encrypted, try to decrypt
                decrypted_success = False
                if mesh_packet.encrypted:
                    if self.debug:
                        self.console.print(f"[yellow]Packet is encrypted, attempting decryption...[/yellow]")
                        self.console.print(f"[dim]Encrypted data length: {len(mesh_packet.encrypted)} bytes[/dim]")

                    nonce_bytes = mesh_packet.id.to_bytes(8, 'little') + getattr(mesh_packet, 'from').to_bytes(8, 'little')
                    decrypted = self._decrypt_packet(mesh_packet.encrypted, nonce_bytes)
                    if decrypted:
                        data_message = mesh_pb2.Data()
                        data_message.ParseFromString(decrypted)
                        mesh_packet.decoded.CopyFrom(data_message)
                        decrypted_success = True

                        if self.debug:
                            self.console.print(f"[green]✓ Decryption successful![/green]")
                            self.console.print("\n[cyan]━━━ Decrypted Data Message ━━━[/cyan]")
                            self.console.print(Panel(
                                str(data_message),
                                title="Decrypted Data (Protobuf)",
                                border_style="green"
                            ))
                    else:
                        if self.debug:
                            self.console.print(f"[red]✗ Decryption failed with all available keys[/red]")
                else:
                    if self.debug:
                        self.console.print(f"[cyan]Packet is not encrypted[/cyan]")

                # Create display table
                table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
                table.add_column("Field", style="cyan", width=20)
                table.add_column("Value", style="white")

                # Basic info
                table.add_row("Source", f"[yellow]{source_name}[/yellow]")
                if self.debug and decode_method:
                    table.add_row("Decode Method", f"[dim]{decode_method}[/dim]")
                table.add_row("Packet ID", f"{mesh_packet.id}")
                from_node = getattr(mesh_packet, 'from')
                to_node = getattr(mesh_packet, 'to')
                table.add_row("From", f"[green]{self._format_node_id(from_node)}[/green] ({from_node})")
                table.add_row("To", f"[blue]{self._format_node_id(to_node)}[/blue] ({to_node})")
                table.add_row("Channel", f"{mesh_packet.channel}")
                table.add_row("Hop Limit", f"{mesh_packet.hop_limit}")

                # Gateway info
                if packet_data.get('Gateway'):
                    table.add_row("Gateway", f"!{packet_data['Gateway']}")

                # Timestamp (API uses 'Time' with capital T)
                if packet_data.get('Time') or packet_data.get('timestamp'):
                    time_val = packet_data.get('Time') or packet_data.get('timestamp')
                    table.add_row("Time", time_val)

                # Signal info (check both cases)
                if packet_data.get('rssi') or packet_data.get('RSSI'):
                    rssi = packet_data.get('rssi') or packet_data.get('RSSI')
                    table.add_row("RSSI", f"{rssi} dBm")
                if packet_data.get('snr') or packet_data.get('SNR'):
                    snr = packet_data.get('snr') or packet_data.get('SNR')
                    table.add_row("SNR", f"{snr} dB")

                # Encryption status
                if mesh_packet.encrypted:
                    status = "[green]✓ Decrypted[/green]" if decrypted_success else "[red]✗ Failed to decrypt[/red]"
                    table.add_row("Encryption", status)

                # Decoded data
                if mesh_packet.HasField('decoded'):
                    portnum_name = self._get_portnum_name(mesh_packet.decoded.portnum)
                    table.add_row("Type", f"[magenta]{portnum_name}[/magenta]")

                    if mesh_packet.decoded.payload:
                        payload_str = self._decode_payload(mesh_packet.decoded.payload, mesh_packet.decoded.portnum)
                        table.add_row("Payload", payload_str)

                        # Debug: show raw payload details
                        if self.debug:
                            self.console.print(f"\n[cyan]━━━ Payload Details ━━━[/cyan]")
                            self.console.print(f"[dim]Raw hex: {mesh_packet.decoded.payload.hex()}[/dim]")
                            self.console.print(f"[dim]Length: {len(mesh_packet.decoded.payload)} bytes[/dim]")
                            self.console.print(f"[dim]Portnum: {mesh_packet.decoded.portnum} ({portnum_name})[/dim]")

                            # Try to decode telemetry in debug mode to show structure
                            if "TELEMETRY" in portnum_name:
                                try:
                                    telemetry = mesh_pb2.Telemetry()
                                    telemetry.ParseFromString(mesh_packet.decoded.payload)
                                    self.console.print(f"\n[cyan]━━━ Parsed Telemetry Structure ━━━[/cyan]")
                                    self.console.print(Panel(
                                        str(telemetry),
                                        title="Telemetry (Protobuf)",
                                        border_style="green"
                                    ))

                                    # Show detailed field inspection
                                    self.console.print(f"\n[cyan]━━━ Telemetry Fields Inspection ━━━[/cyan]")
                                    self.console.print(f"[dim]Time: {telemetry.time}[/dim]")
                                    self.console.print(f"[dim]HasField('device_metrics'): {telemetry.HasField('device_metrics')}[/dim]")
                                    self.console.print(f"[dim]HasField('environment_metrics'): {telemetry.HasField('environment_metrics')}[/dim]")
                                    self.console.print(f"[dim]HasField('power_metrics'): {telemetry.HasField('power_metrics')}[/dim]")

                                    if telemetry.HasField('device_metrics'):
                                        dm = telemetry.device_metrics
                                        self.console.print(f"\n[green]Device Metrics:[/green]")
                                        self.console.print(f"  battery_level: {dm.battery_level}")
                                        self.console.print(f"  voltage: {dm.voltage}")
                                        self.console.print(f"  channel_utilization: {dm.channel_utilization}")
                                        self.console.print(f"  air_util_tx: {dm.air_util_tx}")

                                    if telemetry.HasField('environment_metrics'):
                                        em = telemetry.environment_metrics
                                        self.console.print(f"\n[green]Environment Metrics:[/green]")
                                        self.console.print(f"  temperature: {em.temperature}")
                                        self.console.print(f"  relative_humidity: {em.relative_humidity}")
                                        self.console.print(f"  barometric_pressure: {em.barometric_pressure}")

                                except Exception as e:
                                    self.console.print(f"[red]Failed to parse telemetry: {e}[/red]")
                                    import traceback
                                    self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

                # Display the packet
                title = f"Packet #{index + 1}"
                self.console.print(Panel(table, title=title, border_style="blue"))

                # Add separator in debug mode
                if self.debug:
                    self.console.print("[dim]" + "─" * 80 + "[/dim]\n")

            except Exception as e:
                self.console.print(f"[red]Error processing packet: {e}[/red]")
                if self.debug:
                    self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

        except Exception as e:
            self.console.print(f"[red]Error in display: {e}[/red]")
            if self.debug:
                self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    def test_source(self, source_name: Optional[str] = None, limit: int = 10):
        """Test fetching and decoding packets from sources."""
        self.console.print("\n[bold]Meshtastic Packet Tester[/bold]")
        self.console.print("[dim]Testing packet download and decoding (no MQTT)[/dim]\n")

        sources = self.config['api_sources']

        # Filter by source name if specified
        if source_name:
            sources = [s for s in sources if s['name'].lower() == source_name.lower()]
            if not sources:
                self.console.print(f"[red]Source '{source_name}' not found in config[/red]")
                return

        total_processed = 0

        for source in sources:
            if not source.get('enabled', True):
                self.console.print(f"[yellow]Skipping disabled source: {source['name']}[/yellow]")
                continue

            packets = self._fetch_packets(source)

            # Limit number of packets to display
            display_count = min(len(packets), limit)

            for i, packet in enumerate(packets[:display_count]):
                self._display_packet(packet, source['name'], total_processed)
                total_processed += 1

            if len(packets) > display_count:
                self.console.print(f"\n[dim]... and {len(packets) - display_count} more packets (use --limit to show more)[/dim]\n")

        if total_processed == 0:
            self.console.print("[yellow]No packets received[/yellow]")
        else:
            self.console.print(f"\n[green]✓[/green] Displayed {total_processed} packets")

    def list_sources(self):
        """List all configured API sources."""
        self.console.print("\n[bold]Configured API Sources:[/bold]\n")

        table = Table(show_header=True, box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("URL", style="white")
        table.add_column("Status", style="green")

        for source in self.config['api_sources']:
            status = "✓ Enabled" if source.get('enabled', True) else "✗ Disabled"
            table.add_row(source['name'], source['url'], status)

        self.console.print(table)
        self.console.print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Meshtastic Packet Tester - Test packet download and decoding without MQTT"
    )
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '-s', '--source',
        help='Test only specific source by name'
    )
    parser.add_argument(
        '-l', '--limit',
        type=int,
        default=10,
        help='Maximum number of packets to display (default: 10)'
    )
    parser.add_argument(
        '--list-sources',
        action='store_true',
        help='List all configured sources and exit'
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug mode to show raw packet data and detailed errors'
    )

    args = parser.parse_args()

    try:
        tester = PacketTester(args.config, debug=args.debug)

        if args.list_sources:
            tester.list_sources()
        else:
            tester.test_source(args.source, args.limit)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
