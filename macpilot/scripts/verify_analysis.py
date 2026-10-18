#!/usr/bin/env python3
"""Read-only AX analysis checks on two owned synthetic windows; no installation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from verify_capabilities import Fixture, dump
from verify_connection import Server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args = parser.parse_args()
    args.binary = args.binary.resolve(strict=True); args.fixture = args.fixture.resolve(strict=True)
    args.evidence = args.evidence.resolve(); args.evidence.mkdir(parents=True,exist_ok=False)
    checks=[]; first=second=server=None
    def ck(name,condition,**detail):
        checks.append(dict(check=name,passed=bool(condition),**detail))
        dump(args.evidence/'checks.json',checks)
        if not condition:raise AssertionError((name,detail))
    def analyze(operation='summary',**extra):
        observation=first.observe()
        return first.call('mac_analyze',dict(observation=observation['id'],operation=operation,**extra))
    try:
        first=Fixture(args)
        # Only synthetic fixture text is changed. No keyboard, global input or personal app is used.
        sample='가😀z literal a.*b'
        first.ax('literal','set_value',text=sample)
        background=argparse.Namespace(**vars(args)); background.evidence=args.evidence/'sentinel';background.evidence.mkdir()
        second=Fixture(background)
        before=first.call('mac_connection',dict(operation='status'))['foregroundPID']
        ck('owned sentinel is foreground',before==second.fixture_pid)
        result=analyze()
        ck('summary recollects a new observation',result['observation']!=result['sourceObservation'] and result['totalCollectedNodes']>5)
        ck('summary is read-only',result['readOnly'] and result['outcome']['dispatch']=='not_applicable')
        ck('secure provider text is absent','PROBE_SECRET_MUST_NOT_APPEAR' not in json.dumps(result))
        ck('summary does not activate the background app',first.call('mac_connection',dict(operation='status'))['foregroundPID']==before)
        result=analyze('search',query='a.*b')
        ck('literal regex-like text matches one fixture field',result['matchedCount']==1 and result['nodes'][0]['identifier']=='literal')
        result=analyze('search',query='A.*B')
        ck('search is case-insensitive',result['matchedCount']==1)
        result=analyze('search',query='PROBE_SECRET_MUST_NOT_APPEAR')
        ck('secure values cannot be searched',result['matchedCount']==0 and result['absenceEstablished'] is False)
        result=analyze('search',query='not-in-the-synthetic-fixture',maxNodes=1)
        ck('partial search cannot establish absence',result['coverage']=='partial' and result['absenceEstablished'] is False)
        result=analyze(limit=1)
        ck('pagination is distinct from tree coverage',result['returnedCount']==1 and result['hasMore'] and result['nextOffset']==1)
        result=analyze(role='AXButton',interactiveOnly=True)
        ck('role and interactive filters omit disabled controls',result['returnedCount']>=3 and all(n['role']=='AXButton' and n['enabled'] for n in result['nodes']))
        observation=first.observe(); field=first.node(observation,'literal')
        result=first.call('mac_analyze',dict(observation=observation['id'],operation='inspect',node=field['id']))
        ck('native attribute names are enumerated',result['attributes']['status']=='read' and 'AXValue' in result['attributes']['names'])
        ck('native parameterized attribute names are enumerated',result['parameterizedAttributes']['status']=='read' and 'AXStringForRange' in result['parameterizedAttributes']['names'])
        ck('native settable metadata is typed',result['settable']['AXValue']['status']=='read' and result['settable']['AXValue']['settable'] is True)
        result=first.call('mac_analyze',dict(observation=observation['id'],operation='read_text',node=field['id'],start=1,length=2))
        ck('UTF-16 range reads the complete surrogate pair',result['text']=='😀' and result['returnedUTF16Length']==2 and result['rangeComplete'])
        for attribute,extra,predicate in [
            ('bounds_for_range',dict(start=1,length=2),lambda r:r['bounds']['width']>0 and r['bounds']['height']>0),
            ('line_for_index',dict(start=1),lambda r:r['line']==0),
            ('range_for_line',dict(start=0),lambda r:r['start']==0 and r['length']>=3)]:
            layout=first.call('mac_analyze',dict(observation=observation['id'],operation='text_layout',node=field['id'],attribute=attribute,**extra))
            ck('native text layout '+attribute,layout['status']=='ui_layout_read' and predicate(layout))
        result=first.call('mac_analyze',dict(observation=observation['id'],operation='read_text',node=field['id'],start=999,length=1),True)
        ck('out-of-bounds text range is rejected',result.get('code')=='invalid_text_range')
        secret=first.node(observation,'secret')
        for operation,extra in [('inspect',{}),('read_text',dict(start=0,length=1))]:
            result=first.call('mac_analyze',dict(observation=observation['id'],operation=operation,node=secret['id'],**extra),True)
            ck('secure node rejects '+operation,result.get('code')=='invalid_node' and 'PROBE_SECRET' not in json.dumps(result))
        button=first.node(observation,'increment');frame=button['frame']
        result=first.call('mac_analyze',dict(observation=observation['id'],operation='hit_test',x=frame['x']+frame['width']/2,y=frame['y']+frame['height']/2))
        ck('app-scoped native hit test resolves the exact node',result['status']=='ui_hit' and result['node']['node']==button['id'])
        result=first.call('mac_analyze',dict(observation=observation['id'],operation='hit_test',x=-100000,y=-100000),True)
        ck('hit test rejects outside-window coordinates',result.get('code')=='outside_window')
        first.command('duplicate')
        result=analyze('search',query='ready')
        ck('duplicate matches remain ambiguous',result['matchedCount']==2 and 'selectedNode' not in result)
        observation=first.observe()
        node=first.node(observation,'literal')
        first.call('mac_ax',dict(observation=observation['id'],node=node['id'],operation='set_value',text='updated synthetic text'),True)
        result=first.call('mac_analyze',dict(observation=observation['id'],operation='inspect',node=node['id']),True)
        ck('stale or consumed observations are rejected',result.get('code') in ['stale_observation','observation_consumed'])
        server=Server(args.binary,first.root/'controller')
        catalog=server.request('tools/list',{})['tools']
        tool=next(t for t in catalog if t['name']=='mac_analyze')
        ck('fresh MCP exposes the read-only analysis tool',tool['annotations']['readOnlyHint'] is True,toolCount=len(catalog))
        observation=first.observe()
        result=server.call('mac_analyze',observation=observation['id'],operation='summary',limit=2)
        ck('fresh MCP executes native summary',result['status']=='ui_analyzed' and result['returnedCount']==2)
        ck('analysis never clicks fixture controls',first.state()['clicks']==0)
        ck('background analysis preserves foreground through the full suite',first.call('mac_connection',dict(operation='status'))['foregroundPID']==before)
    finally:
        if server:server.close()
        if second:second.close()
        if first:first.close()
        for source in (Path(__file__),Path(__file__).with_name('verify_capabilities.py')):
            shutil.copy2(source,args.evidence/source.name)
        dump(args.evidence/'report.json',dict(checks=checks,binarySHA256=hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                                             scope='owned_synthetic_windows',physicalDevice='NOT_RUN'))
    print(json.dumps(dict(status='passed',checks=len(checks),report=str(args.evidence/'report.json'))))


if __name__=='__main__':main()
