"""Run from a stable source directory and open the browser after HTTP readiness."""
from pathlib import Path
import os,sys,threading,time,urllib.request,json,webbrowser
ROOT=Path(__file__).resolve().parent;os.chdir(ROOT);sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS']:os.environ.setdefault(key,'1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')
def open_when_ready():
    print("[launch] Waiting for web server to start...", flush=True)
    for _ in range(60):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1) as r:
                if r.status == 200:
                    print("[launch] Server online! Opening browser at http://127.0.0.1:8000 ...", flush=True)
                    webbrowser.open('http://127.0.0.1:8000')
                    return
        except Exception:
            pass
        time.sleep(0.5)
def free_port(port=8000):
    try:
        import socket, subprocess
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) == 0:
                print(f"[launch] Port {port} in use. Cleaning up prior server instance...", flush=True)
                if sys.platform == 'win32':
                    out = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True)
                    for line in out.strip().splitlines():
                        if 'LISTENING' in line:
                            pid = line.strip().split()[-1]
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                    time.sleep(1)
    except Exception:
        pass

if __name__=='__main__':
    free_port(8000)
    if '--no-browser' not in sys.argv:threading.Thread(target=open_when_ready,daemon=True).start()
    import uvicorn
    uvicorn.run('assurex_claim_engine.web.app:app',host='127.0.0.1',port=8000)

