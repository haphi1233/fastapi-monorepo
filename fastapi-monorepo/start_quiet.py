#!/usr/bin/env python
"""
Script khởi động tất cả services với log output tối giản
Chỉ hiển thị thông tin quan trọng, không spam log
"""
import os
import sys
import time
import subprocess
import signal
from typing import List, Dict
import threading

# Add current directory to path for libs imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

class QuietMonorepoManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.processes: Dict[str, subprocess.Popen] = {}
        self.services: Dict[str, Dict] = {
            "Auth Service": {
                "path": os.path.join(self.base_dir, "services", "auth"),
                "script": "start.py",
                "port": 8001,
                "url": "http://localhost:8001"
            },
            "Articles Service": {
                "path": os.path.join(self.base_dir, "services", "articles"),
                "script": "start.py", 
                "port": 8002,
                "url": "http://localhost:8002"
            },
            "Products Service": {
                "path": os.path.join(self.base_dir, "services", "products"),
                "script": "start.py",
                "port": 8003,
                "url": "http://localhost:8003"
            },
            "API Gateway": {
                "path": self.base_dir,
                "script": "start_gateway.py",
                "port": 8080,
                "url": "http://localhost:8080"
            }
        }
        self.running = True
    
    def print_banner(self):
        """In banner chào mừng ngắn gọn"""
        print("\n" + "="*50)
        print("🚀 KHỞI ĐỘNG FASTAPI MONOREPO")
        print("="*50)
    
    def check_port(self, port: int) -> bool:
        """Kiểm tra port có đang được sử dụng không"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    
    def start_service(self, name: str, config: Dict) -> subprocess.Popen:
        """Khởi động một service (silent mode)"""
        # Khởi động service với output redirect sang DEVNULL
        process = subprocess.Popen(
            [sys.executable, config['script']],
            cwd=config['path'],
            stdout=subprocess.DEVNULL,  # Không hiển thị output
            stderr=subprocess.DEVNULL,  # Không hiển thị error
            universal_newlines=True
        )
        return process
    
    def start_all(self):
        """Khởi động tất cả services"""
        self.print_banner()
        
        print("\n⏳ Đang khởi động các services...")
        
        for name, config in self.services.items():
            try:
                # Kiểm tra và dừng process cũ nếu cần
                if self.check_port(config['port']):
                    print(f"   • {name}: Port {config['port']} đã được sử dụng, đang cleanup...")
                    # Kill process cũ trên Windows
                    if os.name == 'nt':
                        subprocess.run(
                            f"for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{config['port']}') do taskkill /PID %a /F",
                            shell=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        time.sleep(1)
                
                process = self.start_service(name, config)
                self.processes[name] = process
                
                # Đợi service khởi động
                time.sleep(2)
                
                # Kiểm tra service đã lên chưa
                if self.check_port(config['port']):
                    print(f"   ✅ {name}: Port {config['port']}")
                else:
                    print(f"   ⏳ {name}: Đang khởi động...")
                    
            except Exception as e:
                print(f"   ❌ {name}: Lỗi - {e}")
        
        print("\n" + "="*50)
        print("✨ HỆ THỐNG ĐÃ SẴN SÀNG!")
        print("="*50)
        print("\n📌 Truy cập:")
        print("   • API Gateway: http://localhost:8080")
        print("   • Swagger Docs: http://localhost:8080/docs")
        print("   • Dashboard: http://localhost:8080/dashboard")
        print("\n⛔ Nhấn Ctrl+C để dừng tất cả services")
        print("="*50)
    
    def monitor_quietly(self):
        """Monitor services mà không spam log"""
        while self.running:
            time.sleep(30)  # Check mỗi 30 giây
            
            # Chỉ kiểm tra và restart nếu service chết
            for name, process in self.processes.items():
                if process.poll() is not None:
                    print(f"\n⚠️  {name} đã dừng, đang khởi động lại...")
                    config = self.services[name]
                    new_process = self.start_service(name, config)
                    self.processes[name] = new_process
    
    def stop_all(self):
        """Dừng tất cả services"""
        self.running = False
        print("\n\n🛑 Đang dừng tất cả services...")
        
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=3)
                print(f"   • {name}: Đã dừng")
            except:
                try:
                    process.kill()
                    print(f"   • {name}: Đã force stop")
                except:
                    pass
        
        print("\n✅ Đã dừng toàn bộ hệ thống!\n")
    
    def run(self):
        """Chạy hệ thống"""
        try:
            # Khởi động tất cả services
            self.start_all()
            
            # Monitor trong background thread
            monitor_thread = threading.Thread(target=self.monitor_quietly)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Đợi user nhấn Ctrl+C
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stop_all()
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Lỗi hệ thống: {e}")
            self.stop_all()
            sys.exit(1)

def main():
    """Main function"""
    manager = QuietMonorepoManager()
    
    # Đăng ký signal handler
    def signal_handler(sig, frame):
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Chạy hệ thống
    manager.run()

if __name__ == "__main__":
    main()
