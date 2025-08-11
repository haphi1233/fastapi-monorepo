#!/usr/bin/env python
"""
Script khởi động tất cả services trong FastAPI Monorepo
Dùng script này để khởi động toàn bộ hệ thống với 1 lệnh duy nhất
"""
import os
import sys
import time
import subprocess
import signal
from typing import List, Dict

# Add current directory to path for libs imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

class MonorepoManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.processes: List[subprocess.Popen] = []
        self.services: Dict[str, Dict] = {
            "Auth Service": {
                "path": os.path.join(self.base_dir, "services", "auth"),
                "script": "start.py",
                "port": 8001,
                "color": "\033[94m"  # Blue
            },
            "Articles Service": {
                "path": os.path.join(self.base_dir, "services", "articles"),
                "script": "start.py", 
                "port": 8002,
                "color": "\033[92m"  # Green
            },
            "Products Service": {
                "path": os.path.join(self.base_dir, "services", "products"),
                "script": "start.py",
                "port": 8003,
                "color": "\033[93m"  # Yellow
            },
            "API Gateway": {
                "path": self.base_dir,
                "script": "start_gateway.py",
                "port": 8080,
                "color": "\033[95m"  # Magenta
            }
        }
    
    def print_banner(self):
        """In banner chào mừng"""
        print("\n" + "="*60)
        print("🚀 FASTAPI MONOREPO - KHỞI ĐỘNG HỆ THỐNG")
        print("="*60)
        print("\n📋 Các services sẽ được khởi động:")
        for name, config in self.services.items():
            print(f"  • {name}: Port {config['port']}")
        print("\n" + "="*60 + "\n")
    
    def check_port(self, port: int) -> bool:
        """Kiểm tra port có đang được sử dụng không"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    
    def start_service(self, name: str, config: Dict) -> subprocess.Popen:
        """Khởi động một service"""
        print(f"{config['color']}[{name}] Đang khởi động trên port {config['port']}...\033[0m")
        
        # Kiểm tra port (không hiển thị netstat output)
        if self.check_port(config['port']):
            print(f"⚠️  Port {config['port']} đã được sử dụng")
            
        # Khởi động service
        process = subprocess.Popen(
            [sys.executable, config['script']],
            cwd=config['path'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        return process
    
    def start_all(self):
        """Khởi động tất cả services"""
        self.print_banner()
        
        for name, config in self.services.items():
            try:
                process = self.start_service(name, config)
                self.processes.append(process)
                time.sleep(2)  # Đợi service khởi động
                
                # Kiểm tra service đã lên chưa
                if self.check_port(config['port']):
                    print(f"✅ {name} đã khởi động thành công!\n")
                else:
                    print(f"⏳ {name} đang khởi động...\n")
                    
            except Exception as e:
                print(f"❌ Lỗi khi khởi động {name}: {e}\n")
        
        print("\n" + "="*60)
        print("✨ TẤT CẢ SERVICES ĐÃ ĐƯỢC KHỞI ĐỘNG!")
        print("="*60)
        print("\n📌 Truy cập hệ thống:")
        print("  • API Gateway: http://localhost:8080")
        print("  • Swagger UI: http://localhost:8080/docs")
        print("  • Dashboard: http://localhost:8080/dashboard")
        print("\n📝 Nhấn Ctrl+C để dừng tất cả services")
        print("="*60 + "\n")
    
    def stop_all(self):
        """Dừng tất cả services"""
        print("\n\n🛑 Đang dừng tất cả services...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        print("✅ Đã dừng tất cả services!\n")
    
    def monitor_services(self):
        """Theo dõi output của services"""
        print("\n📌 Hệ thống đang chạy. Nhấn Ctrl+C để dừng.\n")
        try:
            while True:
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        # Service đã dừng, khởi động lại
                        service_name = list(self.services.keys())[i]
                        print(f"⚠️  {service_name} đã dừng. Đang khởi động lại...")
                        config = self.services[service_name]
                        new_process = self.start_service(service_name, config)
                        self.processes[i] = new_process
                
                time.sleep(30)  # Kiểm tra mỗi 30 giây thay vì 5 giây
                
        except KeyboardInterrupt:
            self.stop_all()
            sys.exit(0)

def main():
    """Main function"""
    manager = MonorepoManager()
    
    # Đăng ký signal handler
    def signal_handler(sig, frame):
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Khởi động tất cả services
        manager.start_all()
        
        # Monitor services
        manager.monitor_services()
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        manager.stop_all()
        sys.exit(1)

if __name__ == "__main__":
    main()
