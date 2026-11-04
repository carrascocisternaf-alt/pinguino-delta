/* Pingüino Delta · sitio institucional: abre sin internet con la última versión vista.
   Solo guarda el cargador (index.html) y el manifiesto (mismo origen). Los datos
   (Excel y stocks) los guarda la propia página en IndexedDB. */
const CACHE='delta-inst-v2';
const BASICOS=['./','manifest.webmanifest','icono.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(BASICOS).catch(()=>{})));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const r=e.request;const u=new URL(r.url);
  if(r.method!=='GET'||u.origin!==location.origin)return;
  const esPagina=r.mode==='navigate';
  // Red primero (siempre la versión más nueva); sin red, la última guardada
  e.respondWith(fetch(r).then(res=>{if(res.ok){const cp=res.clone();caches.open(CACHE).then(c=>c.put(esPagina?'./':r,cp));}return res;})
    .catch(()=>caches.match(esPagina?'./':r).then(m=>m||caches.match('./'))));
});
