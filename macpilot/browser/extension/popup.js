const status=document.querySelector('#status');
document.querySelector('#extension').textContent='Extension ID: '+chrome.runtime.id;
chrome.storage.local.get('bridgeState').then(({bridgeState})=>{status.textContent=bridgeState?.connected?'MacPilot 연결됨':(bridgeState?.error||'로컬 native host를 설치하세요.');});
document.querySelector('#grant').onclick=async()=>{
 try{const url=new URL(document.querySelector('#origin').value);if(!['https:','http:'].includes(url.protocol))throw new Error('http 또는 https 주소를 입력하세요.');const allowed=await chrome.permissions.request({origins:[url.origin+'/*']});status.textContent=allowed?'이 사이트의 백그라운드 접근을 허용했습니다.':'권한을 허용하지 않았습니다.';}catch(error){status.textContent=error.message;}
};
