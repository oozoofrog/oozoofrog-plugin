#!/usr/bin/env python3
"""Optional local EmbeddingGemma 2 worker. One bounded request, no network, no input actions."""
import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import time

REQUIRED = {'sentence-transformers':'6.1.0','transformers':'5.20.1','torch':'2.14.1',
            'torchvision':'0.29.1','numpy':'2.5.4','pillow':'13.0.0','huggingface_hub':'1.33.0','safetensors':'0.8.0'}
REVISION = '914f7f89142e33e77833254d9c9b90c3cef7303b'


class Invalid(Exception):
    def __init__(self, code): self.code = code


def hashed(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def execute(args, request):
    if not isinstance(request,dict) or set(request)-{'operation','requestID','items'}:
        raise Invalid('invalid_request')
    request_id = request.get('requestID')
    if not isinstance(request_id,str) or len(request_id)!=36:
        raise Invalid('invalid_request')
    versions = {}
    for package, expected in REQUIRED.items():
        try: actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: raise Invalid('dependency_missing')
        if actual != expected: raise Invalid('dependency_version_mismatch')
        versions[package] = actual
    manifest = json.loads(args.manifest.read_text())
    if manifest.get('model')!='google/embeddinggemma-2' or manifest.get('revision')!=REVISION:
        raise Invalid('invalid_model_manifest')
    for entry in manifest['files']:
        path = args.model / entry['path']
        if path.stat().st_size!=entry['size'] or hashed(path)!=entry['sha256']:
            raise Invalid('model_integrity_failed')
    import torch
    if args.device=='mps' and not torch.backends.mps.is_available(): raise Invalid('model_device_unavailable')
    if request.get('operation')=='probe':
        return dict(requestID=request_id,status='ready',model=manifest['model'],revision=REVISION,dimensions=768,versions=versions,device=args.device)
    if request.get('operation')!='embed': raise Invalid('invalid_request')
    items=request.get('items')
    if not isinstance(items,list) or not 1<=len(items)<=50: raise Invalid('invalid_request')
    root=args.allowed_root.resolve(strict=True)
    from PIL import Image
    Image.MAX_IMAGE_PIXELS=16_777_216
    prepared=[]; ids=set()
    for item in items:
        if not isinstance(item,dict) or set(item)-{'id','kind','text','path'}: raise Invalid('invalid_request')
        key=item.get('id')
        if not isinstance(key,str) or len(key)!=64 or any(c not in '0123456789abcdef' for c in key) or key in ids: raise Invalid('invalid_request')
        ids.add(key); kind=item.get('kind')
        if kind=='image':
            if 'text' in item or not isinstance(item.get('path'),str): raise Invalid('invalid_request')
            path=Path(item['path']).resolve(strict=True)
            if not path.is_relative_to(root) or path.stat().st_size>16_777_216: raise Invalid('image_outside_selected_state')
            with Image.open(path) as image:
                if image.width>8192 or image.height>8192 or image.width*image.height>16_777_216: raise Invalid('image_too_large')
                image.load(); value={'image':image.convert('RGB').copy()}
        elif kind in ['query','document']:
            value=item.get('text')
            if 'path' in item or not isinstance(value,str) or len(value.encode())>4096: raise Invalid('invalid_request')
        else: raise Invalid('invalid_request')
        prepared.append((key,kind,value))
    from sentence_transformers import SentenceTransformer
    started=time.monotonic()
    model=SentenceTransformer(str(args.model),device=args.device,config_kwargs={'audio_config':None},
                              model_kwargs={'dtype':torch.float32},local_files_only=True,trust_remote_code=False)
    loaded=time.monotonic()
    vectors={}
    for kind in ['image','query','document']:
        batch=[(key,value) for key,k,value in prepared if k==kind]
        if not batch: continue
        encoded=model.encode([value for _,value in batch],batch_size=4,normalize_embeddings=True,
                             convert_to_numpy=True,show_progress_bar=False,prompt_name=None if kind=='image' else kind)
        for (key,_),vector in zip(batch,encoded):
            result=vector.tolist()
            if len(result)!=768 or not all(math.isfinite(x) for x in result) or not .99<=sum(x*x for x in result)<=1.01:
                raise Invalid('invalid_embedding')
            vectors[key]=result
    return dict(requestID=request_id,status='embedded',model=manifest['model'],revision=REVISION,dimensions=768,device=args.device,
                loadMilliseconds=(loaded-started)*1000,inferenceMilliseconds=(time.monotonic()-loaded)*1000,
                vectors=[dict(id=key,vector=vectors[key]) for key,_,_ in prepared])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',type=Path,required=True);parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--allowed-root',type=Path,required=True);parser.add_argument('--device',choices=['mps','cpu'],required=True)
    args=parser.parse_args()
    for key in ['HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_DATASETS_OFFLINE']: os.environ[key]='1'
    os.environ['TOKENIZERS_PARALLELISM']='false'
    raw=sys.stdin.buffer.read(131073)
    if len(raw)>131072: raise Invalid('request_too_large')
    request=json.loads(raw,parse_constant=lambda _:(_ for _ in ()).throw(Invalid('invalid_request')))
    with contextlib.redirect_stdout(sys.stderr): result=execute(args,request)
    encoded=json.dumps(result,separators=(',',':'),allow_nan=False)
    if len(encoded.encode())>1_048_576: raise Invalid('response_too_large')
    print(encoded,flush=True)


if __name__=='__main__':
    try: main()
    except Exception as error:
        print(json.dumps(dict(status='error',code=error.code if isinstance(error,Invalid) else 'embedding_worker_failed')),flush=True)
        # Never print request content, image paths, text, vectors or a traceback.
        print(type(error).__name__,file=sys.stderr)
        sys.exit(2)
