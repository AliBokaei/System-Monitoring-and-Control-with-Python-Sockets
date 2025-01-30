import socket
import json
import psutil
import threading
import time
import os
from datetime import datetime

class EndpointAgent:
    def __init__(self, listen_host='0.0.0.0', listen_port=5555, manager_host=None, manager_port=None):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.manager_host = manager_host
        self.manager_port = manager_port
        self.udp_port = None
        self.cpu_threshold = 80
        self.tcp_socket = None
        self.udp_socket = None
        self.server_mode = manager_host is None  # If manager_host is None, run in server mode
        
        try:
            if self.server_mode:
                # Setup server socket
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind((listen_host, listen_port))
                self.server_socket.listen(1)
                print(f"Listening for manager connection on {listen_host}:{listen_port}")
            else:
                # Setup client socket
                self.connect_to_manager()
                
        except Exception as e:
            print(f"Error initializing agent: {e}")
            raise

    def connect_to_manager(self):
        """Connect to the manager as a client"""
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((self.manager_host, self.manager_port))
            
            # Get UDP port from manager
            self.udp_port = int(self.tcp_socket.recv(1024).decode())
            
            # Setup UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            print(f"Connected to manager at {self.manager_host}:{self.manager_port}")
            return True
            
        except Exception as e:
            print(f"Error connecting to manager: {e}")
            return False

    def wait_for_manager(self):
        """Wait for manager to connect"""
        try:
            print("Waiting for manager connection...")
            self.tcp_socket, manager_address = self.server_socket.accept()
            print(f"Manager connected from {manager_address}")
            
            # Get UDP port from manager
            self.udp_port = int(self.tcp_socket.recv(1024).decode())
            
            # Setup UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            return True
            
        except Exception as e:
            print(f"Error accepting manager connection: {e}")
            return False

    def get_process_count(self):
        """Get the count of running processes safely"""
        try:
            return len(list(psutil.process_iter()))
        except Exception as e:
            print(f"Error counting processes: {e}")
            return -1

    def start(self):
        if self.server_mode:
            while True:
                if self.wait_for_manager():
                    self.handle_connection()
                time.sleep(5)  # Wait before accepting new connection
        else:
            self.handle_connection()

    def handle_connection(self):
        """Handle the manager connection and commands"""
        # Start CPU monitoring in separate thread
        monitor_thread = threading.Thread(target=self.monitor_system)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        while True:
            try:
                command = self.tcp_socket.recv(1024).decode()
                if not command:  # Connection closed
                    print("Manager disconnected")
                    break
                
                if command == "GET_SYSTEM_STATS":
                    stats = {
                        'cpu': psutil.cpu_percent(),
                        'memory': psutil.virtual_memory().percent
                    }
                    self.tcp_socket.send(json.dumps(stats).encode())
                
                elif command == "GET_PROCESS_COUNT":
                    count = {
                        'processes': self.get_process_count()
                    }
                    self.tcp_socket.send(json.dumps(count).encode())
                
                elif command == "RESTART_SYSTEM":
                    os.system('shutdown -r now')
                
            except Exception as e:
                print(f"Error handling command: {e}")
                break

        # Clean up connection
        if self.tcp_socket:
            self.tcp_socket.close()
            self.tcp_socket = None

    def monitor_system(self):
        while self.tcp_socket:  # Only monitor while connected
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                
                if cpu_percent > self.cpu_threshold and self.udp_socket and self.udp_port:
                    alert = {
                        'alert': f'High CPU Usage: {cpu_percent}%',
                        'timestamp': str(datetime.now())
                    }
                    
                    # Send to the correct manager address
                    manager_addr = (
                        self.manager_host if self.manager_host 
                        else self.tcp_socket.getpeername()[0],
                        self.udp_port
                    )
                    
                    self.udp_socket.sendto(
                        json.dumps(alert).encode(),
                        manager_addr
                    )
                
                time.sleep(5)
            except Exception as e:
                print(f"Error in monitoring: {e}")
                time.sleep(5)

if __name__ == "__main__":
    try:
        # Decide whether to run in server or client mode
        mode = input("Enter mode (server/client) [server]: ").lower() or "server"
        
        if mode == "server":
            # Server mode - wait for manager to connect
            agent = EndpointAgent(listen_host='0.0.0.0', listen_port=5555)
        else:
            # Client mode - connect to manager
            manager_host = input("Enter manager IP address [192.168.80.128]: ") or "192.168.80.128"
            agent = EndpointAgent(
                manager_host=manager_host,
                manager_port=5555
            )
        
        agent.start()
        
    except KeyboardInterrupt:
        print("\nShutting down agent...")
    except Exception as e:
        print(f"Error: {e}")