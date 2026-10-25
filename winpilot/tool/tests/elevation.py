"""Native elevation validation; never shows UAC or sends input."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from integration import EXE, ROOT, CREATE_NO_WINDOW

def reject(arguments, status):
    result = subprocess.run([str(EXE), *arguments], capture_output=True, text=True,
                            encoding='utf-8', timeout=10, creationflags=CREATE_NO_WINDOW)
    assert result.returncode == 1, result.stdout
    assert json.loads(result.stderr)['status'] == status, result.stderr
    assert len(result.stderr) < 500

with tempfile.TemporaryDirectory(dir=ROOT / 'artifacts') as folder:
    path = Path(folder) / '한글 클릭 계획.json'
    path.write_text('{"png_base64":"PRIVATE_SCREEN_DATA",broken}', encoding='utf-8')
    reject(['--elevate-game-click', str(path)], 'invalid_plan')
    plan = dict(window=dict(window_id='test', hwnd=1, pid=1, started=1, process='MabinogiMobile',
                            title='마비노기 모바일', bounds=dict(x=0,y=0,width=100,height=100), minimized=False, foreground=False),
                observed_at=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(minutes=3)).isoformat(),
                x=50,y=50,png_base64='test',purpose='골드 상세 정보 열기')
    path.write_text(json.dumps(plan,ensure_ascii=False),encoding='utf-8')
    reject(['--elevate-game-click', str(path)], 'stale_observation')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    plan['purpose']='변경된 계획'
    path.write_text(json.dumps(plan,ensure_ascii=False),encoding='utf-8-sig')
    reject(['--verify-game-click', str(path), before], 'plan_changed')
print(json.dumps(dict(status='passed',checks=3,uac_requested=False,native_input_sent=False)))
