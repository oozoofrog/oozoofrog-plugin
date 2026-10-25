import {readFileSync} from 'node:fs';
import {assertModel} from './model.mjs';
import {layoutView} from './layout.mjs';
export const escapeHTML=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function renderHTML(model){assertModel(model);const layouts=model.views.map(v=>layoutView(model,v));
 const payload=JSON.stringify({model,layouts}).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
 const css=readFileSync(new URL('../assets/viewer.css',import.meta.url),'utf8');const js=readFileSync(new URL('../assets/viewer.js',import.meta.url),'utf8');
 return `<!doctype html><html lang="${model.locale||'en'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><title>${escapeHTML(model.title)} · C4fy</title><style>${css}</style></head><body><div id="app" class="app"></div><noscript>C4fy requires JavaScript to display this interactive diagram.</noscript><script id="c4fy-data" type="application/json">${payload}</script><script>${js}</script></body></html>`;
}
