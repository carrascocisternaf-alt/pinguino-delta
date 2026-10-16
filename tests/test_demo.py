"""Prueba funcional de Pingüino Delta con los Excels de demostración.
- Sin internet (todo request externo se bloquea: valida que el HTML sea autónomo).
- Fecha fija 16-10-2026 (los vencimientos demo están calculados desde ese día).
- Verificación exacta de conteos y de la clasificación de Rotación.
Uso: pip install playwright && playwright install chromium && python3 tests/test_demo.py
"""
import asyncio, os, sys, datetime as dt
from playwright.async_api import async_playwright
BASE=os.path.dirname(os.path.abspath(__file__)); RAIZ=os.path.join(BASE,'..')
DEMO=os.path.join(RAIZ,'demo'); HTML='file://'+os.path.abspath(os.path.join(RAIZ,'index.html'))
def f(p): return next(os.path.join(DEMO,x) for x in sorted(os.listdir(DEMO)) if x.startswith(p))
fallas=[]
def ok(cond,msg): print(('✓ ' if cond else '✗ ')+msg); (None if cond else fallas.append(msg))

async def nueva(b):
    pg=await b.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('dialog',lambda d:(errs.append('DIALOGO: '+d.message[:200]),asyncio.ensure_future(d.accept())))
    async def route(rt):
        await (rt.continue_() if rt.request.url.startswith('file:') else rt.abort())
    await pg.route('**/*',route)
    await pg.clock.install(time=dt.datetime(2026,10,16,10,0))
    await pg.goto(HTML); await pg.wait_for_timeout(1500)
    return pg,errs

async def st(pg,i): return await pg.eval_on_selector('#'+i,'e=>e.textContent')

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        # ── Escenario A: archivos separados ──
        pg,errs=await nueva(b)
        ok(await pg.evaluate("typeof XLSX")=='object','SheetJS embebido disponible sin internet')
        ok(await pg.eval_on_selector('[data-an=log]','e=>getComputedStyle(e).display')=='none','Pestaña LOG oculta')
        for fid,pre,sid,txt in [('fi-inv','01','st-inv','✓ 40 artículos'),('fi-cons','02','st-cons','✓ 40 artículos'),
            ('fi-prog','03','st-prog','3 artículo(s) con doble programación'),('fi-disp','04','st-disp','años: 2024, 2025, 2026'),
            ('cal-fi','06','cal-st','✓ 223 despachos'),('costo-fi','07','costo-st','✓ 40 artículos'),
            ('difinv-fi','08','difinv-st','✓ 14 artículo(s)'),('gasto-fi','09','gasto-st','✓ 840 registros')]:
            await pg.set_input_files('#'+fid,f(pre)); await pg.wait_for_timeout(700)
            t=await st(pg,sid); ok(txt in t,f'{pre} → {t[:90]}')
        ok(await pg.evaluate("Object.keys(ARTS_DINAMICOS).length")==0,'0 artículos no reconocidos (homologación 100%)')
        await pg.evaluate("calcularRotacion('arsenal')")
        c=await pg.evaluate("(()=>{const R=window._rotResultados_arsenal;const L=R.map?R:R.res;const c={};L.forEach(x=>c[x.estado]=(c[x.estado]||0)+1);return c})()")
        ok(c=={'ok':24,'critico':5,'sobrestock':6,'vence-pronto':5},f'Rotación: {c}')
        ok(not errs,f'Sin errores JS ni alertas: {errs}')
        # ── Escenario B: archivo único ──
        pg,errs=await nueva(b)
        await pg.set_input_files('#fi-prog',f('05')); await pg.wait_for_timeout(900)
        t=await st(pg,'st-prog'); ok('80 filas de consumo / 86 de programación' in t,'05 archivo único → '+t[-90:])
        ok('✓ 40 artículos' in await st(pg,'st-cons'),'05 → consumo promedio derivado')
        ok(not errs,f'Sin errores JS ni alertas: {errs}')
        await b.close()
    print('\nRESULTADO:', 'TODO OK' if not fallas else f'{len(fallas)} FALLA(S)')
    sys.exit(1 if fallas else 0)
asyncio.run(main())
