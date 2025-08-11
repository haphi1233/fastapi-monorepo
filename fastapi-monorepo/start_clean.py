#!/usr/bin/env python
"""
Script khởi động sạch sẽ - hiển thị thông tin cần thiết, không spam log
"""
import os
import sys
import time
import subprocess
import signal
from typing import Dict
import threading
from datetime import datetime

# Add current directory to path for libs imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

class CleanMonorepoManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.processes: Dict[str, subprocess.Popen] = {}
        self.services = {
            "Auth": {
                "path": os.path.join(self.base_dir, "services", "auth"),
                "script": "start.py",
                "port": 8001
            },
            "Articles": {
                "path": os.path.join(self.base_dir, "services", "articles"),
                "script": "start.py", 
                "port": 8002
            },
            "Products": {
                "path": os.path.join(self.base_dir, "services", "products"),
                "script": "start.py",
                "port": 8003
            },
            "Gateway": {
                "path": self.base_dir,
                "script": "start_gateway.py",
                "port": 8080
            }
        }
        self.running = True
        self.last_check = {}
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def check_port(self, port: int) -> bool:
        """Kiểm tra port"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    
    def kill_port(self, port: int):
        """Kill process on port"""
        if os.name == 'nt':
            # Windows - sử dụng cách khác để tránh lỗi Git Bash
            cmd = f'powershell "Get-NetTCPConnection -LocalPort {port} -State Listen | Select -ExpandProperty OwningProcess | ForEach-Object {{ Stop-Process -Id $_ -Force }}"'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Linux/Mac
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def start_service(self, name: str, config: Dict) -> subprocess.Popen:
        """Khởi động service với output được filter"""
        # Kill port cũ nếu đang dùng
        if self.check_port(config['port']):
            self.kill_port(config['port'])
            time.sleep(1)
        
        # Start service
        process = subprocess.Popen(
            [sys.executable, config['script']],
            cwd=config['path'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Thread để đọc output nhưng chỉ hiển thị error
        def read_output():
            for line in process.stdout:
                if any(keyword in line.lower() for keyword in ['error', 'exception', 'failed', 'critical']):
                    print(f"[{name}] ⚠️ {line.strip()}")
        
        thread = threading.Thread(target=read_output)
        thread.daemon = True
        thread.start()
        
        return process
    
    def display_status(self):
        """Hiển thị status table đẹp"""
        self.clear_screen()
        print("+" + "-"*58 + "+")
        print("|" + " "*20 + "FASTAPI MONOREPO" + " "*22 + "|")
        print("+" + "-"*58 + "+")
        print("| Service     | Port  | Status    | URL                   |")
        print("|-------------|-------|-----------|----------------------|")
        
        for name, config in self.services.items():
            port = config['port']
            status = "[OK]" if self.check_port(port) else "[--]"
            url = f"localhost:{port}"
            print(f"| {name:<11} | {port:<5} | {status:<9} | {url:<21} |")
        
        print("+" + "-"*58 + "+")
        
        print("\nQuick Access:")
        print("  * Swagger UI: http://localhost:8080/docs")
        print("  * Dashboard:  http://localhost:8080/dashboard")
        print("  * Health:     http://localhost:8080/health")
        
        current_time = datetime.now().strftime("%H:%M:%S")
        print(f"\nLast updated: {current_time} | Press Ctrl+C to stop")
    
    def start_all(self):
        """Khởi động tất cả services"""
        print("\n⏳ Starting services...")
        
        for name, config in self.services.items():
            try:
                process = self.start_service(name, config)
                self.processes[name] = process
                print(f"  • {name}: Starting on port {config['port']}...")
                time.sleep(2)
            except Exception as e:
                print(f"  ❌ {name}: {e}")
        
        # Wait for all services to be ready
        time.sleep(3)
        
        # Display initial status
        self.display_status()
    
    def monitor(self):
        """Monitor services và update display"""
        while self.running:
            try:
                # Check và restart nếu cần
                for name, process in self.processes.items():
                    if process.poll() is not None:
                        # Service died, restart silently
                        config = self.services[name]
                        new_process = self.start_service(name, config)
                        self.processes[name] = new_process
                
                # Update display mỗi 10 giây
                time.sleep(10)
                if self.running:
                    self.display_status()
                    
            except KeyboardInterrupt:
                break
    
    def stop_all(self):
        """Dừng tất cả services"""
        self.running = False
        print("\n\n🛑 Stopping all services...")
        
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=2)
                print(f"  • {name}: Stopped")
            except:
                try:
                    process.kill()
                except:
                    pass
        
        print("\n✅ All services stopped!\n")
    
    def run(self):
        """Main run loop"""
        try:
            self.start_all()
            self.monitor()
        except KeyboardInterrupt:
            self.stop_all()

def main():
    manager = CleanMonorepoManager()
    
    # Signal handler
    def signal_handler(sig, frame):
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run
    manager.run()

if __name__ == "__main__":
    main()
