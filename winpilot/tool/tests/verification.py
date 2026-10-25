"""자체 Count 창에서 자동 시작, 중단, 무인 종료를 검증한다."""
import argparse, ctypes as c, json, subprocess, time
from ctypes import wintypes as w
from integration import Client, ROOT, EXE, CREATE_NO_WINDOW
REPORTS = EXE.parent.parent / 'verification'
u=c.WinDLL('user32')
u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
u.SendMessageW.argtypes=[w.HWND,w.UINT,c.c_size_t,c.c_ssize_t]
callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
u.EnumChildWindows.argtypes=[w.HWND,callback,w.LPARAM]
parser=argparse.ArgumentParser(); parser.add_argument('--no-input',action='store_true'); args=parser.parse_args()
fixture=subprocess.Popen([str(EXE),'--fixture','A'],creationflags=CREATE_NO_WINDOW)
client=Client(); forms=[]; checks=[]
def wait_window(pid):
    end=time.monotonic()+15
    while time.monotonic()<end:
        found=next((x for x in client.tool('windows_list')[0]['windows'] if x['pid']==pid),None)
        if found: return found
        time.sleep(.02)
    raise AssertionError('안내 창 표시 실패')
def controls(win):
    found={}
    @callback
    def visit(hwnd,_):
        text=c.create_unicode_buffer(512); u.GetWindowTextW(hwnd,text,512); found[text.value]=hwnd; return True
    u.EnumChildWindows(win['hwnd'],visit,0)
    return found
def count():
    obs,_=client.tool('window_observe',{'window_id':target['window_id'],'capture':False})
    return next(e['name'] for e in obs['elements'] if e['name'].startswith('Count:'))
def launch():
    existing_reports=set(REPORTS.glob('*/result.json'))
    startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
    p=subprocess.Popen([str(EXE),'--verify-fixture',str(fixture.pid),str(target['started'])],creationflags=CREATE_NO_WINDOW,startupinfo=startup)
    p.existing_reports=existing_reports
    forms.append(p); return p

def report(p):
    matches=[json.loads(f.read_text(encoding='utf-8')) for f in REPORTS.glob('*/result.json') if f not in p.existing_reports]
    return next(x for x in matches if x.get('runner_pid')==p.pid)
try:
    target=wait_window(fixture.pid)
    p=launch(); toast=wait_window(p.pid)
    buttons=controls(toast)
    assert '검증 시작' not in buttons and '실행 전 화면' not in buttons
    assert toast['bounds']['width']<=440 and toast['bounds']['height']<=100
    u.SendMessageW(buttons['중지'],0xF5,0,0)
    p.wait(timeout=15)
    assert count()=='Count:0'
    r=report(p); assert r['automatic'] and not r['dispatched'] and r['result']['status']=='interrupted',r
    checks.append('숨김 실행에서도 작은 알림 표시·수동 시작 UI 없음·준비 중 취소 시 입력 없이 자동 종료')
    if not args.no_input:
        p=launch()
        p.wait(timeout=25)
        r=report(p)
        assert r['dispatched'] and r['result']['status']=='dispatched_unverified',r
        assert count()=='Count:1'
        assert r['verified'] is False and r['before_image'] and r['after_image']
        checks.append('사용자 버튼 없이 자동 클릭 정확히 1회·기록 저장·결과 창 없이 종료')
    output=dict(status='passed',checks=checks,game_input_tested=False,uac_tested=False,no_input=args.no_input)
    path=ROOT/'artifacts'/('verification-auto-no-input.json' if args.no_input else 'verification-auto.json')
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(output,ensure_ascii=False))
finally:
    client.close()
    for p in forms+[fixture]:
        if p.poll() is None: p.terminate(); p.wait(timeout=5)
