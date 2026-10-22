#!/usr/bin/env python3
"""Static HTML checks only. Does not certify sources, external links, layout or accessibility."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlparse
class Check(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=set();self.anchors=[];self.errors=[];self.external=[];self.images=0;self.lang=False;self.title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='html': self.lang=a.get('lang')=='ko'
        if tag=='title': self.title=True
        if 'id' in a:
            if a['id'] in self.ids:self.errors.append('duplicate id '+a['id'])
            self.ids.add(a['id'])
        if tag=='img':
            self.images+=1
            if not a.get('alt'):self.errors.append('image missing alt')
        for key in ('href','src'):
            value=a.get(key,'')
            if not value:continue
            if value.startswith('#'):self.anchors.append(value[1:]);continue
            scheme=urlparse(value).scheme
            if scheme not in ('http','https','data'):self.errors.append('unsafe or unbundled URL '+value[:120])
            if tag in ('img','script','link') and scheme!='data':self.errors.append('external runtime resource '+value[:120])
            if scheme in ('http','https'):self.external.append(value)
    def finish(self):
        self.errors.extend('broken anchor #'+x for x in self.anchors if x not in self.ids)
        if not self.lang:self.errors.append('html lang must be ko')
        if not self.title:self.errors.append('title missing')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('html',type=Path);a=p.parse_args();c=Check();c.feed(a.html.read_text());c.finish()
    print(json.dumps({'file':str(a.html.resolve()),'static_pass':not c.errors,'errors':c.errors,'images':c.images,'external_links_not_verified':sorted(set(c.external)),'not_tested':['source accuracy','external link targets','browser behavior','layout/print','keyboard and screen reader','physical step count']},ensure_ascii=False,indent=2));raise SystemExit(bool(c.errors))
if __name__=='__main__':main()
