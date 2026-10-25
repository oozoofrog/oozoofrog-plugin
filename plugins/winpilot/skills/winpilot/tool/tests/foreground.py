"""자체 캔버스에서 전경 그리기·중지 버튼·외부 입력 감지와 해제를 검증한다."""
import base64, ctypes as c, json, subprocess, time
from ctypes import wintypes as w
from integration import Client, ROOT, EXE, CREATE_NO_WINDOW

u=c.WinDLL('user32',use_last_error=True)
u.GetAsyncKeyState.restype=c.c_short
u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int]
u.SendMessageW.argtypes=[w.HWND,w.UINT,c.c_size_t,c.c_ssize_t]
callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
u.EnumChildWindows.argtypes=[w.HWND,callback,w.LPARAM]
fixture=subprocess.Popen([str(EXE),'--fixture','A'],creationflags=CREATE_NO_WINDOW)
client=Client(); checks=[]; results=[]
try:
    for _ in range(60):
        listing,_=client.tool('windows_list')
        win=next((x for x in listing['windows'] if x['pid']==fixture.pid),None)
        if win: break
        time.sleep(.1)
    assert win,'시험 창 시작 실패'
    def draw(request):
        obs,_=client.tool('window_observe',{'window_id':win['window_id']})
        canvas=next(e['bounds'] for e in obs['elements'] if e['name']=='PilotCanvas')
        x=canvas['x']-obs['capture']['bounds']['x']+25
        y=canvas['y']-obs['capture']['bounds']['y']+25
        job,_=client.tool('action_run',dict(window_id=win['window_id'],observation_id=obs['observation_id'],request_id=request,
             type='drag',foreground_policy='allow',x=x,y=y,to_x=x+200,to_y=y+70,duration_ms=1800))
        return job['job_id']
    def check_release():
        assert u.GetAsyncKeyState(1)>=0,'마우스 버튼이 해제되지 않음'
        listing,_=client.tool('windows_list')
        assert not any(x['title'].startswith('Windows Pilot 제어') or x['title']=='Windows Pilot 입력 제어 중' for x in listing['windows'])
        obs,raw=client.tool('window_observe',{'window_id':win['window_id']})
        label=next(e['name'] for e in obs['elements'] if e['name'].startswith('Segments:'))
        assert label.endswith('Held:False'),label
        return label,raw
    job=draw('draw'); r=client.wait(job); results.append(r)
    assert r['status']=='dispatched_unverified',r
    label,raw=check_release()
    assert int(label.split(';')[0].split(':')[1])>0,label
    image=next(x for x in raw['content'] if x['type']=='image')
    (ROOT/'artifacts/foreground-fixture.png').write_bytes(base64.b64decode(image['data']))
    checks.append('전경 실제 드래그로 선 생성·버튼 해제·안내 제거')
    job=draw('button-stop')
    notice=None
    for _ in range(40):
        listing,_=client.tool('windows_list')
        notice=next((x for x in listing['windows'] if x['title']=='Windows Pilot 입력 제어 중'),None)
        if notice and u.GetAsyncKeyState(1)<0: break
        time.sleep(.05)
    assert notice and u.GetAsyncKeyState(1)<0,'안내 또는 진행 중 버튼 누름을 확인하지 못함'
    edges=[x for x in listing['windows'] if x['title']=='Windows Pilot 제어 테두리']
    assert not edges,('제거한 테두리가 남아 있음',edges)
    buttons=[]
    @callback
    def visit(hwnd,_):
        text=c.create_unicode_buffer(256); u.GetWindowTextW(hwnd,text,256)
        if text.value=='중지': buttons.append(hwnd)
        return True
    u.EnumChildWindows(notice['hwnd'],visit,0)
    assert len(buttons)==1
    u.SendMessageW(buttons[0],0xF5,0,0)
    ended=None
    for _ in range(30):
        listing,_=client.tool('windows_list')
        ended=next((x for x in listing['windows'] if x['title']=='Windows Pilot 제어 종료'),None)
        if ended: break
        time.sleep(.03)
    assert ended,'사용자가 직접 조작 가능한 종료 안내가 표시되지 않음'
    assert u.GetAsyncKeyState(1)>=0,'종료 안내 전에 버튼이 해제되지 않음'
    messages=[]
    @callback
    def read_notice(hwnd,_):
        text=c.create_unicode_buffer(512); u.GetWindowTextW(hwnd,text,512); messages.append(text.value)
        return True
    u.EnumChildWindows(ended['hwnd'],read_notice,0)
    assert any('직접 사용하세요' in text for text in messages),messages
    r=client.wait(job); results.append(r); assert r['status']=='interrupted',r
    check_release(); checks.append('즉시 중지 후 버튼 해제 → 직접 조작 가능 안내 → 안내 제거')
    job=draw('external-input')
    deadline=time.monotonic()+6
    while u.GetAsyncKeyState(1)>=0 and time.monotonic()<deadline: time.sleep(.02)
    assert u.GetAsyncKeyState(1)<0
    # windows-pilot 표식이 없는 외부 입력으로 사용자 입력과 동일한 중단 분기를 검사한다.
    u.mouse_event(0x2001,50,0,0,0)
    r=client.wait(job); results.append(r); assert r['status']=='interrupted',r
    check_release(); checks.append('다른 출처의 마우스 입력 감지 후 자동 중단·버튼 해제')
    job=draw('external-keyboard')
    deadline=time.monotonic()+6
    while u.GetAsyncKeyState(1)>=0 and time.monotonic()<deadline: time.sleep(.02)
    assert u.GetAsyncKeyState(1)<0
    try: u.keybd_event(0x87,0,0,0)
    finally: u.keybd_event(0x87,0,2,0)
    r=client.wait(job); results.append(r); assert r['status']=='interrupted',r
    check_release(); checks.append('다른 출처의 키보드 입력 감지 후 자동 중단·버튼 해제')
    report=dict(status='passed',checks=checks,results=results,physical_hardware_interrupt_tested=False)
    (ROOT/'artifacts/foreground.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
finally:
    client.close()
    if fixture.poll() is None: fixture.terminate(); fixture.wait(timeout=5)
