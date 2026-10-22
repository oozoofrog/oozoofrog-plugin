#!/usr/bin/env python3
"""Render a reviewed travel JSON into a local, standalone Korean guidebook.
No network calls, itinerary inference, reservations, or factual verification.
"""
import argparse
import base64
import html
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def esc(value):
    return html.escape(str(value), quote=True)

def link(url, label):
    if not url or urlparse(str(url)).scheme not in ('https', 'http'):
        return esc(label) + ' · 링크 미확인'
    return '<a href="' + esc(url) + '" rel="noopener noreferrer">' + esc(label) + '</a>'

def paragraphs(value):
    if isinstance(value, list):
        return '<ul>' + ''.join('<li>' + esc(x) + '</li>' for x in value) + '</ul>'
    return '<p>' + esc(value) + '</p>'

def table(headers, rows, caption):
    return '<table class="responsive"><caption>' + esc(caption) + '</caption><thead><tr>' + ''.join('<th scope="col">' + esc(x) + '</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td data-label="' + esc(headers[i]) + '">' + esc(cell) + '</td>' for i, cell in enumerate(row)) + '</tr>' for row in rows) + '</tbody></table>'

def image_bytes(path):
    raw=path.read_bytes()
    if path.suffix.lower()=='.svg':
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('SVG declarations are not supported')
        try: tree=ET.fromstring(raw)
        except ET.ParseError as error: raise ValueError('invalid SVG: '+str(error))
        allowed={'svg','g','path','rect','line','polyline','polygon','circle','ellipse','text','tspan','defs','marker','linearGradient','radialGradient','stop','clipPath','mask','title','desc','symbol','use'}
        for node in tree.iter():
            if node.tag.split('}')[-1] not in allowed: raise ValueError('SVG must be a self-contained static diagram')
            for key,value in node.attrib.items():
                local=key.split('}')[-1].lower()
                if local.startswith('on') or local=='style': raise ValueError('SVG scripts and inline styles are not supported')
                if local=='href' and not value.startswith('#'): raise ValueError('SVG external references are not supported')
                if 'url(' in value.lower() and not re.fullmatch(r'url\(#[A-Za-z0-9_-]+\)',value): raise ValueError('SVG external resources are not supported')
    return raw

def validate(data):
    errors=[]
    for key in ('title','companions','checked','summary','trip_review','days','practical','field_search','unknowns','sources','attributions'):
        if key not in data: errors.append('missing '+key)
    if not isinstance(data.get('fictional'), bool): errors.append('fictional must be boolean')
    if not data.get('trip_review'): errors.append('whole-trip review required before daily details')
    if not data.get('days'): errors.append('at least one day required')
    for n, day in enumerate(data.get('days',[]),1):
        for key in ('title','briefing','today_decision','start','end','timeline','walking','buffer_steps','fatigue_alternative','weather_alternative','next_day_check','preparation','reservation_check','sights'):
            if key not in day: errors.append(f'day {n}: missing {key}')
        walks=day.get('walking',[])
        if not walks: errors.append(f'day {n}: empty hotel-to-hotel walking ledger')
        try:
            numbers=[x[k] for x in walks for k in ('low','high')]+[day.get('buffer_steps',0)]
            if any(type(x) is not int for x in numbers):
                errors.append(f'day {n}: walking values and buffer must be finite whole-number steps, not booleans or unknowns')
                continue
            low=sum(x['low'] for x in walks); high=sum(x['high'] for x in walks)+day.get('buffer_steps',0)
            if any(x['low']<0 or x['high']<x['low'] for x in walks): errors.append(f'day {n}: invalid walking range')
            if day.get('buffer_steps',0)<0: errors.append(f'day {n}: negative buffer')
            if high>=10000: errors.append(f'day {n}: upper estimate plus buffer {high} reaches/exceeds 10000; revise')
            if high<low: errors.append(f'day {n}: invalid total')
            if high>8000 and not day.get('target_note'): errors.append(f'day {n}: target deviation reason required above 8000')
            for x in walks:
                if not x.get('basis'): errors.append(f'day {n}: missing walking basis')
        except (KeyError,TypeError): errors.append(f'day {n}: numeric low/high and walking basis required')
    if errors: raise ValueError('\n'.join(errors))

def section(title, content, id=None, cls='card'):
    return '<section class="'+cls+'"'+(' id="'+esc(id)+'"' if id else '')+'><h2>'+esc(title)+'</h2>'+content+'</section>'

def details(title, content):
    return '<details><summary>'+esc(title)+'</summary>'+content+'</details>'

def render(data, base):
    validate(data)
    font=ROOT/'assets/NanumGothic-Regular.ttf'
    fontcss=''
    fontnote='나눔고딕 파일 미내장: 기기에 설치된 나눔고딕 또는 시스템 글꼴로 표시합니다.'
    if font.exists() and (ROOT/'assets/OFL.txt').exists():
        encoded=base64.b64encode(font.read_bytes()).decode()
        fontcss="@font-face{font-family:'Nanum Gothic';src:url(data:font/ttf;base64,"+encoded+") format('truetype');font-weight:400;font-display:swap}"
        fontnote='나눔고딕을 내장했습니다. 폰트 이용조건은 아래에 보존합니다.'
    first=data['days'][0]
    first_low=sum(x['low'] for x in first['walking']); first_high=sum(x['high'] for x in first['walking'])+first['buffer_steps']
    header='<p class="muted">'+('가상 입력 검증용 · ' if data['fictional'] else '')+'한국어 여행 가이드북</p><h1>'+esc(data['title'])+'</h1>'
    header+='<div class="tip"><p><strong>오늘의 판단</strong> · '+esc(first['today_decision'])+'</p><p><strong>하루 계획 추정 '+f'{first_low:,}~{first_high:,}'+'보</strong><br><span class="small">여유 '+esc(first['buffer_steps'])+'보 포함 · 실제 걸음 수는 달라집니다.</span></p></div>'
    if data['fictional']:
        header+='<p class="warning"><strong>가상 입력 검증용 예시</strong> · 지명·시각·거리·걸음 수는 실제 여행 사실이 아닙니다. 예약·현장 이동에 사용하지 마세요.</p>'
    header+='<p>'+esc(data['companions'])+'</p><p class="small">자료 확인일: '+esc(data['checked'])+'</p><p>'+esc(data['summary'])+'</p>'
    nav=[('trip-review','전체 일정 점검')]+[(f'day-{i}',d['title']) for i,d in enumerate(data['days'],1)]+[('practical','실전 안내'),('field-search','현장 검색표'),('sources','참고자료')]
    header+='<nav aria-label="목차">'+''.join('<a href="#'+k+'">'+esc(v)+'</a>' for k,v in nav)+'</nav>'
    content=section('전체 일정의 동행자 부담과 조정',paragraphs(data['trip_review']),'trip-review')
    for i,day in enumerate(data['days'],1):
        low=sum(x['low'] for x in day['walking']); high=sum(x['high'] for x in day['walking'])+day['buffer_steps']
        body='<p class="brief tip">'+esc(day['briefing'])+'</p><p><strong>호텔 출발 '+esc(day['start'])+' → 귀가 '+esc(day['end'])+'</strong></p>'
        body+='<p><strong>하루 보행 추정 '+f'{low:,}~{high:,}'+'보</strong> · 여유 '+esc(day['buffer_steps'])+'보 포함. 계획 목표 7~8천 보, 상한 1만 보 미만. 실제 계측 보증이 아닙니다.</p>'
        if not 7000<=high<=8000: body+='<p class="tip">목표 범위와 차이가 있는 이유: '+esc(day.get('target_note','목표보다 낮은 보행 부담을 선택했습니다.'))+'</p>'
        body+=table(['시각','구분','활동·이동·휴식','생략 시 절감'],[[x.get('time','미정'),x.get('priority','미확인'),x.get('activity',''),x.get('skip_saving','해당 없음')] for x in day['timeline']],'하루 시간표')
        body+=details('보행 합산과 불확실성',table(['구간·숨은 보행','범위(보)','추정 근거'],[[x['label'],f"{x['low']:,}~{x['high']:,}",x['basis']] for x in day['walking']],'호텔 출발부터 귀가까지')+'<p>예비 보행 '+esc(day['buffer_steps'])+'보. 복도·역·공항·환승·식사·입구·대기·계단·경사를 별도로 누락 점검합니다.</p>')
        body+=details('교통·승하차·식사·앉는 휴식',paragraphs(day.get('transport_rest',['승하차·식사·좌석 확인 필요'])))
        for j,sight in enumerate(day['sights'],1):
            sightbody=paragraphs(sight.get('overview','설명 미확인'))
            for key,label in [('history','역사·인물·연표'),('artifacts','핵심 유물·관찰 지점'),('route','입장·관찰·퇴장 동선')]:
                sightbody+='<h3>'+label+'</h3>'+paragraphs(sight.get(key,'미확인'))
            for k,pic in enumerate(sight.get('images',[]),1):
                path=(base/pic['file']).resolve()
                if not path.is_file(): raise ValueError('image file missing: '+str(path))
                if path.suffix.lower() not in ('.png','.jpg','.jpeg','.gif','.webp','.svg'): raise ValueError('unsupported image format')
                if not pic.get('alt') or not pic.get('license') or not pic.get('credit'): raise ValueError('image alt/license/credit required')
                mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
                uri='data:'+mime+';base64,'+base64.b64encode(image_bytes(path)).decode()
                ident=f'image-{i}-{j}-{k}'
                sightbody+='<figure><a href="'+uri+'" download="'+esc(path.name)+'" aria-label="'+esc(pic['alt'])+' 원본 내려받기"><img id="'+ident+'" src="'+uri+'" alt="'+esc(pic['alt'])+'" data-caption="'+esc(pic.get('caption',''))+'"></a><figcaption>'+esc(pic.get('caption',''))+' (확대 불가 시 이미지를 눌러 원본 내려받기)</figcaption><button type="button" class="no-print" data-zoom="'+ident+'">이미지 확대</button><p class="credits">'+esc(pic['credit'])+' · '+esc(pic['license'])+' · '+link(pic.get('source'),pic.get('source_label','원본 출처'))+'</p></figure>'
            if not sight.get('images'): sightbody+='<p class="muted">정확히 일치하는 허가된 사진 미확보. 다른 대상 사진으로 대체하지 않았습니다.</p>'
            body+=details(sight['name'],sightbody)
        body+=details('준비물·예약 확인',paragraphs(day['preparation'])+paragraphs(day['reservation_check']))
        body+=details('날씨·피로·다음 날 대안','<h3>날씨</h3>'+paragraphs(day['weather_alternative'])+'<h3>피로</h3>'+paragraphs(day['fatigue_alternative'])+'<h3>다음 날 출발 점검</h3>'+paragraphs(day['next_day_check']))
        content+=section(day['title'],body,f'day-{i}')
    practical=''
    for p in data['practical']:
        practical+=details(p['title'],'<p class="tag">'+esc(p.get('status','미확인'))+' · '+esc(p.get('version','버전 미확인'))+' · '+esc(p.get('checked','확인일 미정'))+'</p>'+paragraphs(p.get('steps',[])))
    content+=section('출입국·교통·결제 실전 안내',practical,'practical')
    field=''
    for i,item in enumerate(data['field_search'],1):
        ident=f'copy-{i}'
        map_ok=(item.get('map_verified') is True and re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(item.get('map_checked',''))) and urlparse(str(item.get('map_evidence',''))).scheme in ('http','https'))
        map_html=(link(item.get('map_url'),'검증 지도 열기')+' · '+link(item.get('map_evidence'),'입출구 확인 근거')) if map_ok else '지도 링크 미제공 · 정확한 입출구·목적지 검증 필요'
        field+='<article><h3>'+esc(item['ko'])+'</h3><p>현지어: '+esc(item.get('local','미확인'))+'<br>영어: '+esc(item.get('en','미확인'))+'</p><p>정확한 입출구·승하차점: '+esc(item.get('access','미확인'))+'</p><p>'+map_html+' · '+esc(item.get('map_checked','지도 미검증'))+'</p><label for="'+ident+'">복사할 현지 이름</label><input class="copy-value" id="'+ident+'" readonly value="'+esc(item.get('local','미확인'))+'"><div class="copy-row"><button class="no-print" type="button" data-copy="'+ident+'">이름 복사</button></div><p class="status small" id="'+ident+'-status" role="status">자동 복사가 안 되면 위 이름을 직접 선택해 복사하세요.</p><p class="tip">직원에게 보여줄 문장: '+esc(item.get('staff','문장 미확인'))+'</p></article>'
    content+=section('마지막 현장 검색표',field,'field-search')
    content+=section('확정이 필요한 항목',paragraphs(data['unknowns']),'unknowns')
    sourcebody='<p>사실·후기·추정·미확인을 구분합니다. 검색요약만 확인한 자료는 본문 열람으로 표시하지 않습니다.</p>'
    for src in data['sources']:
        sourcebody+='<p>'+link(src.get('url'),src['title'])+' · '+esc(src.get('kind','미확인'))+' · '+esc(src.get('access','열람 범위 미확인'))+' · '+esc(src.get('checked','확인일 미정'))+'</p>'
    if not data['sources']: sourcebody+='<p>이 가상 예시는 실제 여행 운영정보를 사용하지 않습니다.</p>'
    content+=section('참고자료·조사 충돌',sourcebody+paragraphs(data.get('research_conflicts','충돌 없음 또는 실제 조사 전')),'sources','card sources')
    footer='<p class="tip">오프라인: 본문·내장 이미지·폰트·목차·접기는 인터넷 없이 열립니다. 외부 지도·공식 페이지는 온라인 연결이 필요합니다. 자동 복사는 브라우저 권한에 따라 실패할 수 있으며 수동 선택으로 대체합니다.</p><p class="small">'+fontnote+'</p><div class="credits"><h2>필수 저작권·라이선스</h2>'+paragraphs(data['attributions'])
    licensefile=ROOT/'assets/OFL.txt'
    if fontcss: footer+=details('나눔고딕 SIL Open Font License', '<pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+esc(licensefile.read_text())+'</pre>')
    footer+='</div>'
    values={'TITLE':esc(data['title']),'FONT':fontcss,'HEADER':header,'CONTENT':content,'FOOTER':footer}
    return re.sub(r'@@(TITLE|FONT|HEADER|CONTENT|FOOTER)@@',lambda match:values[match.group(1)],(ROOT/'assets/template.html').read_text())

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    try:
        data=json.loads(args.input.read_text());result=render(data,args.input.resolve().parent)
    except (ValueError,KeyError,TypeError,FileNotFoundError) as error:
        parser.exit(2,'Generation refused: '+str(error)+'\n')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(result);print(json.dumps({'output':str(args.output.resolve()),'bytes':len(result.encode()),'fictional':data['fictional'],'scope':'rendered; source truth and visual layout require separate verification'},ensure_ascii=False))
if __name__=='__main__':main()
