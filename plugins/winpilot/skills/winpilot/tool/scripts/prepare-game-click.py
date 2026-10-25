"""방금 관찰한 버튼의 단일 클릭 계획을 만든다. 실행이나 권한 상승은 하지 않는다."""
import argparse, base64, datetime, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
import integration
integration.EXE = Path(os.environ.get('WINDOWS_PILOT_EXE', str(ROOT / 'artifacts/app/windows-pilot.exe')))
from integration import Client, CREATE_NO_WINDOW

parser = argparse.ArgumentParser()
parser.add_argument('x', type=int); parser.add_argument('y', type=int)
parser.add_argument('purpose'); parser.add_argument('--output', required=True)
args = parser.parse_args()
client = Client()
try:
    games = [w for w in client.tool('windows_list')[0]['windows'] if w['process'] == 'MabinogiMobile']
    assert len(games) == 1, '게임 창이 정확히 하나여야 합니다.'
    window = games[0]
    result = subprocess.run([str(integration.EXE), '--worker'], input=json.dumps(dict(operation='capture', window=window)),
        capture_output=True, text=True, encoding='utf-8', creationflags=CREATE_NO_WINDOW, timeout=8)
    capture = json.loads(result.stdout)['capture']
    assert capture['coordinate_mapping_valid']
    assert 24 <= args.x < capture['width']-24 and 24 <= args.y < capture['height']-24
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(window=window, observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        x=args.x, y=args.y, png_base64=capture['png_base64'], purpose=args.purpose), ensure_ascii=False), encoding='utf-8')
    output.with_suffix('.png').write_bytes(base64.b64decode(capture['png_base64']))
    print(json.dumps(dict(plan=str(output), image=str(output.with_suffix('.png')), expires_seconds=120), ensure_ascii=False))
finally:
    client.close()
