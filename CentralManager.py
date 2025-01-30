import socket
import threading
import json
from datetime import datetime
import subprocess
import os
import queue
import select
import time

class CentralManager:
    def __init__(self, tcp_host='0.0.0.0', tcp_port=5555, udp_port=5556, client_addresses=None):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.client_addresses = client_addresses or []  # List of (host, port) tuples
        self.clients = {}
        self.client_stats = {}
        self.command_queues = {}
        self.client_locks = {}
        
        try:
            self.check_and_close_port(self.tcp_port)
            self.check_and_close_port(self.udp_port)
            
            # Setup TCP Server
            self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server.bind((tcp_host, tcp_port))
            self.tcp_server.listen(5)
            
            # Setup UDP Server
            self.udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_server.bind((tcp_host, udp_port))
            
        except Exception as e:
            print(f"Error initializing server: {e}")
            raise

    def connect_to_client(self, client_address):
        """Attempt to connect to a specific client"""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)  # Set timeout for connection attempt
            client_socket.connect(client_address)
            
            # Send UDP port information
            client_socket.send(str(self.udp_port).encode())
            
            # Initialize client data structures
            self.clients[client_address] = client_socket
            self.client_stats[client_address] = {}
            self.command_queues[client_address] = queue.Queue()
            self.client_locks[client_address] = threading.Lock()
            
            # Start client handler thread
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
            client_thread.daemon = True
            client_thread.start()
            
            print(f"Successfully connected to client at {client_address}")
            return True
            
        except Exception as e:
            print(f"Failed to connect to client at {client_address}: {e}")
            return False

    def initialize_client_connections(self):
        """Initialize connections to all predefined clients"""
        print("Initializing connections to predefined clients...")
        for address in self.client_addresses:
            if not self.connect_to_client(address):
                print(f"Will retry connection to {address} later...")

    def retry_failed_connections(self):
        """Periodically retry connecting to failed clients"""
        while True:
            for address in self.client_addresses:
                if address not in self.clients:
                    self.connect_to_client(address)
            time.sleep(30)  # Wait 30 seconds before next retry

    def start(self):
        # Initialize connections to predefined clients
        self.initialize_client_connections()
        
        # Start connection retry thread
        retry_thread = threading.Thread(target=self.retry_failed_connections)
        retry_thread.daemon = True
        retry_thread.start()
        
        # Start UDP listener
        udp_thread = threading.Thread(target=self.handle_udp_messages)
        udp_thread.daemon = True
        udp_thread.start()
        
        # Start command interface
        cmd_thread = threading.Thread(target=self.command_interface)
        cmd_thread.daemon = True
        cmd_thread.start()
        
        # Start connection monitor
        monitor_thread = threading.Thread(target=self.monitor_connections)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        print(f"Central Manager running on TCP Port {self.tcp_port} and UDP Port {self.udp_port}")
        
        # Accept additional connections
        while True:
            client_socket, address = self.tcp_server.accept()
            print(f"\nNew connection from {address}")
            
            # Send UDP port information
            client_socket.send(str(self.udp_port).encode())
            
            # Initialize client data structures
            self.clients[address] = client_socket
            self.client_stats[address] = {}
            self.command_queues[address] = queue.Queue()
            self.client_locks[address] = threading.Lock()
            
            # Start client handler thread
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
            client_thread.daemon = True
            client_thread.start()

    # ... (rest of the methods remain the same)
    def check_and_close_port(self, port):
        try:
            command = f"lsof -t -i:{port}"
            process_id = subprocess.check_output(command, shell=True).decode().strip()
            
            if process_id:
                print(f"Port {port} is in use. Closing process {process_id}...")
                os.kill(int(process_id), 9)
                print(f"Process {process_id} closed.")
            
        except subprocess.CalledProcessError:
            print(f"Port {port} is not in use.")
        except Exception as e:
            print(f"Error checking port {port}: {e}")

    def remove_client(self, address):
        """Safely remove a client and clean up its resources"""
        print(f"\nRemoving client {address}...")
        try:
            if address in self.clients:
                self.clients[address].close()
                del self.clients[address]
            if address in self.client_stats:
                del self.client_stats[address]
            if address in self.command_queues:
                del self.command_queues[address]
            if address in self.client_locks:
                del self.client_locks[address]
            print(f"Client {address} successfully removed")
        except Exception as e:
            print(f"Error removing client {address}: {e}")

    def check_client_connection(self, client_socket):
        try:
            readable, _, _ = select.select([client_socket], [], [], 0)
            if readable:
                data = client_socket.recv(1)
                if not data:
                    return False
            return True
        except (socket.error, Exception):
            return False

    def monitor_connections(self):
        while True:
            disconnected_clients = []
            for address, client_socket in self.clients.items():
                if not self.check_client_connection(client_socket):
                    disconnected_clients.append(address)
            for address in disconnected_clients:
                self.remove_client(address)
            threading.Event().wait(5)

    def handle_client(self, client_socket, address):
        try:
            while True:
                if not self.check_client_connection(client_socket):
                    raise ConnectionError("Client disconnected")
                    
                try:
                    command = self.command_queues[address].get_nowait()
                    client_socket.send(command.encode())
                    
                    if command != "RESTART_SYSTEM":
                        client_socket.settimeout(5)
                        response = client_socket.recv(1024).decode()
                        client_socket.settimeout(None)
                        
                        if response:
                            self.client_stats[address] = json.loads(response)
                            print(f"\nResponse from {address}: {self.client_stats[address]}")
                        
                except queue.Empty:
                    pass
                except socket.timeout:
                    print(f"Timeout waiting for response from {address}")
                
                threading.Event().wait(0.1)
                
        except Exception as e:
            print(f"\nError handling client {address}: {e}")
        finally:
            self.remove_client(address)

    def handle_udp_messages(self):
        while True:
            try:
                data, addr = self.udp_server.recvfrom(1024)
                message = json.loads(data.decode())
                print(f"\nALERT from {addr} at {datetime.now()}: {message['alert']}")
            except Exception as e:
                print(f"Error handling UDP message: {e}")

    def command_interface(self):
        while True:
            print("\nCentral Manager Commands:")
            print("1. List Connected Clients")
            print("2. Get CPU and Memory Usage")
            print("3. Get Running Processes Count")
            print("4. Restart System")
            print("5. Exit")
            
            try:
                choice = input("Enter choice (1-5): ")
                
                if choice == '1':
                    self.list_clients()
                elif choice in ['2', '3', '4']:
                    if not self.clients:
                        print("No clients connected!")
                        continue
                    
                    self.list_clients()
                    client_id = input("Enter client number: ")
                    
                    try:
                        client_address = list(self.clients.keys())[int(client_id)-1]
                    except (IndexError, ValueError):
                        print("Invalid client number!")
                        continue
                    
                    if choice == '2':
                        self.command_queues[client_address].put("GET_SYSTEM_STATS")
                    elif choice == '3':
                        self.command_queues[client_address].put("GET_PROCESS_COUNT")
                    elif choice == '4':
                        confirm = input("Are you sure you want to restart the system? (y/n): ")
                        if confirm.lower() == 'y':
                            self.command_queues[client_address].put("RESTART_SYSTEM")
                
                elif choice == '5':
                    break
                
            except Exception as e:
                print(f"Error in command interface: {e}")

    def list_clients(self):
        if not self.clients:
            print("No clients connected!")
            return
            
        print("\nConnected Clients:")
        for i, address in enumerate(self.clients.keys(), 1):
            stats = self.client_stats.get(address, {})
            print(f"{i}. {address}")
            if 'cpu' in stats:
                print(f"   CPU: {stats['cpu']}%, Memory: {stats['memory']}%")
            if 'processes' in stats:
                print(f"   Processes: {stats['processes']}")

if __name__ == "__main__":
    try:
        # Define list of client addresses to connect to
        client_addresses = [
            ('192.168.80.128', 5555),
             ('192.168.80.130', 5555)
        ]
        
        manager = CentralManager(tcp_port=5555, udp_port=5556, client_addresses=client_addresses)
        manager.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error: {e}")