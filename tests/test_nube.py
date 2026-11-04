"""Prueba del modo institucional (Microsoft 365) de Delta con Graph y login simulados.
- La página se sirve como https://delta.test/ (origen seguro) con un config.json de prueba.
- login.microsoftonline.com y graph.microsoft.com se simulan: no sale nada a internet.
Verifica: inicio de sesión PKCE, lectura de los dos Excel por vínculo, que no se
re-descarguen si no cambiaron, publicación de stocks al JSON compartido, que otro
"PC" vea lo mismo, y el uso de la última copia sin internet.
"""
import asyncio, os, json, base64, datetime as dt, urllib.parse as up
from playwright.async_api import async_playwright
BASE=os.path.dirname(os.path.abspath(__file__)); RAIZ=os.path.join(BASE,'..'); DEMO=os.path.join(RAIZ,'demo')
HTML=open(os.path.join(RAIZ,'index.html'),'rb').read()
def demo(p): return open(os.path.join(DEMO,next(x for x in sorted(os.listdir(DEMO)) if x.startswith(p))),'rb').read()
CONS=demo('05_'); SAPU=demo('12_'); INV=os.path.join(DEMO,next(x for x in sorted(os.listdir(DEMO)) if x.startswith('01_')))
CFG={"nombre":"DESAM Prueba","tenant":"prueba.cl","dominio":"prueba.cl","clientId":"00000000-test",
     "consumos":"https://prueba-my.sharepoint.com/:x:/g/personal/a/CONSUMOS","sapu":"https://prueba-my.sharepoint.com/:x:/g/personal/a/SAPU"}
fallas=[]
def ok(c,m): print(('✓ ' if c else '✗ ')+m); (None if c else fallas.append(m))

class Nube:
    """Graph simulado compartido por los dos 'PC' (contextos)."""
    def __init__(s): s.descargas={'consumos':0,'sapu':0}; s.comp=None; s.comp_etag=0; s.puts=0; s.caido=False; s.etag={'consumos':'e1','sapu':'s1'}
    async def handle(s,route):
        r=await s._handle(route); return r is not False
    async def _handle(s,route):
        u=route.request.url; m=route.request.method
        if s.caido and ('graph.microsoft.com' in u or 'dl.test' in u or 'login.microsoftonline' in u): return await route.abort()
        if u.startswith('https://login.microsoftonline.com/') and '/token' in u:
            return await route.fulfill(status=200,headers={'Access-Control-Allow-Origin':'*'},content_type='application/json',body=json.dumps({'access_token':'AT1','refresh_token':'RT1','expires_in':3600}))
        if 'graph.microsoft.com' in u:
            p=up.urlparse(u).path.replace('/v1.0','')
            H={'Access-Control-Allow-Origin':'*'}
            if p=='/me': return await route.fulfill(status=200,headers=H,content_type='application/json',body=json.dumps({'displayName':'Q.F. Prueba'}))
            if p.startswith('/shares/'):
                sid=p.split('/')[2]; url=base64.urlsafe_b64decode(sid[2:]+'==').decode()
                k='consumos' if url.endswith('CONSUMOS') else 'sapu'
                return await route.fulfill(status=200,headers=H,content_type='application/json',body=json.dumps({'id':k,'name':k.upper()+'.xlsx','eTag':s.etag[k],'lastModifiedDateTime':'2026-11-03T12:00:00Z',
                    'lastModifiedBy':{'user':{'displayName':'Felipe'}},'parentReference':{'driveId':'D1','id':'P1'},'@microsoft.graph.downloadUrl':'https://dl.test/'+k}))
            if p.startswith('/drives/D1/items/P1:/'):
                if m=='PUT':
                    s.comp=route.request.post_data; s.comp_etag+=1; s.puts+=1
                    return await route.fulfill(status=200,headers=H,content_type='application/json',body=json.dumps({'eTag':'c%d'%s.comp_etag,'lastModifiedDateTime':'2026-11-04T10:00:00Z'}))
                if not s.comp: return await route.fulfill(status=404,headers=H,body='{}')
                return await route.fulfill(status=200,headers=H,content_type='application/json',body=json.dumps({'eTag':'c%d'%s.comp_etag,'lastModifiedDateTime':'2026-11-04T10:00:00Z','lastModifiedBy':{'user':{'displayName':'Q.F. Prueba'}},'@microsoft.graph.downloadUrl':'https://dl.test/comp'}))
            return await route.fulfill(status=404,headers=H,body='{}')
        if u.startswith('https://dl.test/'):
            k=u.rsplit('/',1)[1]; H={'Access-Control-Allow-Origin':'*'}
            if k=='comp': return await route.fulfill(status=200,headers=H,content_type='application/json',body=s.comp)
            s.descargas[k]+=1
            return await route.fulfill(status=200,headers=H,body=CONS if k=='consumos' else SAPU)
        return False

async def pc(b,nube,login=True):
    ctx=await b.new_context(); pg=await ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('dialog',lambda d:(errs.append('DIALOGO '+d.message[:150]),asyncio.ensure_future(d.accept())))
    async def route(rt):
        u=rt.request.url
        if u.startswith('https://delta.test/'):
            path=up.urlparse(u).path
            if path in ('/','/index.html'): return await rt.fulfill(status=200,content_type='text/html',body=HTML)
            if path=='/config.json': return await rt.fulfill(status=200,content_type='application/json',body=json.dumps(CFG))
            if path=='/sw.js': return await rt.fulfill(status=200,content_type='text/javascript',body='self.addEventListener("fetch",()=>{});')
            if path=='/manifest.webmanifest': return await rt.fulfill(status=200,content_type='application/manifest+json',body='{"name":"x"}')
            return await rt.fulfill(status=404,body='')
        if not await nube.handle(rt): await rt.abort()
    await ctx.route('**/*',route)
    await pg.clock.install(time=dt.datetime(2026,11,4,10,0))
    return ctx,pg,errs

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); N=Nube()
        # ── PC 1: sin sesión → botón entrar → login simulado ──
        ctx,pg,errs=await pc(b,N)
        await pg.goto('https://delta.test/'); await pg.wait_for_timeout(2500)
        txt=await pg.inner_text('#nube-bar')
        ok('Entrar con cuenta prueba.cl' in txt and await pg.evaluate("document.getElementById('demo-bar').style.display")=='none',f'Modo institucional activo, pide iniciar sesión y oculta datos de prueba ({txt[:80]!r})')
        # El login redirige a Microsoft: se intercepta y se responde como si volviera con code
        async def login_route(rt):
            q=up.parse_qs(up.urlparse(rt.request.url).query)
            assert q['code_challenge_method']==['S256'] and q['redirect_uri']==['https://delta.test/'] and 'Files.ReadWrite.All' in q['scope'][0]
            await rt.fulfill(status=200,content_type='text/html',body='<script>location.replace("https://delta.test/?code=CODE1&state='+q['state'][0]+'")</script>')
        await ctx.route('https://login.microsoftonline.com/prueba.cl/oauth2/v2.0/authorize*',login_route)
        await pg.evaluate("nubeEntrar()"); await pg.wait_for_timeout(4000)
        r=await pg.evaluate("({u:location.search,tok:!!JSON.parse(localStorage.getItem('pdn_tok')||'null'),cons:Object.keys(cons_map).length,prog:Object.keys(prog).length,dias:_sdCfg().diarioDias.length,txt:document.getElementById('nube-bar').innerText})")
        ok(r['u']=='' and r['tok'],'Inicio de sesión PKCE: vuelve con código, guarda la sesión y limpia la URL')
        ok(r['cons']>0 and r['prog']>0 and r['dias']==15,f"Lee de SharePoint el archivo único (consumos {r['cons']}, programación {r['prog']}) y el diario SAPU ({r['dias']} días)")
        ok('Q.F. Prueba' in r['txt'] and 'archivo modificado' in r['txt'],f"Barra muestra usuario y fecha de los archivos ({r['txt'][:120]!r})")
        # Sin cambios en SharePoint → no se vuelve a descargar
        await pg.evaluate("nubeSincronizar(true)"); await pg.wait_for_timeout(1500)
        ok(N.descargas=={'consumos':1,'sapu':1},f'Sincronizar sin cambios no re-descarga ({N.descargas})')
        N.etag['consumos']='e2'; await pg.evaluate("nubeSincronizar(true)"); await pg.wait_for_timeout(2000)
        ok(N.descargas['consumos']==2,f'Si el Excel cambió en SharePoint se descarga de nuevo ({N.descargas})')
        # Carga manual de inventario → se publica al JSON compartido
        await pg.set_input_files('#fi-inv',INV); await pg.wait_for_timeout(4500)
        comp=json.loads(N.comp) if N.comp else {}
        ok(N.puts>=1 and len(comp.get('datos',{}).get('inv',{}))>0 and comp.get('por')=='Q.F. Prueba',f"El stock cargado a mano se sube al JSON compartido (subidas {N.puts}, artículos {len(comp.get('datos',{}).get('inv',{}))})")
        ninv=await pg.evaluate("Object.keys(inv).length")
        ok(not errs,f'PC 1 sin errores ({errs})')
        # ── PC 2 (otro navegador, con sesión): ve lo mismo sin cargar nada ──
        ctx2,pg2,errs2=await pc(b,N)
        await pg2.goto('https://delta.test/'); await pg2.evaluate("localStorage.setItem('pdn_tok',JSON.stringify({at:'AT2',rt:'RT2',exp:Date.now()+3600e3}))")
        await pg2.reload(); await pg2.wait_for_timeout(4500)
        r=await pg2.evaluate("({inv:Object.keys(inv).length,cons:Object.keys(cons_map).length,dias:_sdCfg().diarioDias.length})")
        ok(r['inv']==ninv and r['cons']>0 and r['dias']==15,f'Otro PC con el link ve el mismo stock, consumos y diario SAPU ({r}, inv PC1 {ninv})')
        # ── PC 2 sin internet: recarga y usa la última copia ──
        N.caido=True
        await pg2.reload(); await pg2.wait_for_timeout(4000)
        r=await pg2.evaluate("({cons:Object.keys(cons_map).length,ap:NUBE.estado.consumos&&NUBE.estado.consumos.aplicadoEtag,inv:Object.keys(inv).length,txt:document.getElementById('nube-bar').innerText})")
        ok(r['cons']>0 and r['ap']=='e2' and r['inv']==ninv and 'última copia' in r['txt'],f"Sin internet abre con la última copia descargada ({r['cons']} artículos, etag {r['ap']}, {r['txt'][:160]!r})")
        ok(not errs2,f'PC 2 sin errores ({errs2})')
        await b.close()
    print('\nRESULTADO:', 'TODO OK' if not fallas else f'{len(fallas)} FALLA(S)')
    if fallas: raise SystemExit(1)
asyncio.run(main())
