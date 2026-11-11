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
        # ── Escenario C: botón "Cargar datos de prueba" (datos embebidos) ──
        pg,errs=await nueva(b)
        await pg.click('#demo-bar button'); await pg.wait_for_timeout(5500)
        ok('12 archivos de prueba cargados' in await st(pg,'demo-st'),'Botón → '+(await st(pg,'demo-st'))[:60])
        for sid,txt in [('st-inv','✓ 40 artículos'),('st-prog','doble programación'),('st-disp','años: 2024, 2025, 2026'),('cal-st','✓ 223 despachos'),('difinv-st','✓ 14 artículo(s)'),('gasto-st','✓ 840 registros')]:
            ok(txt in await st(pg,sid),f'Botón → {sid}')
        await pg.evaluate("calcularRotacion('arsenal')")
        c=await pg.evaluate("(()=>{const R=window._rotResultados_arsenal;const L=R.map?R:R.res;const c={};L.forEach(x=>c[x.estado]=(c[x.estado]||0)+1);return c})()")
        ok(c=={'ok':24,'critico':5,'sobrestock':6,'vence-pronto':5},f'Botón → Rotación: {c}')
        # Bajar a cero: incluye meses ANTES de «Mes inicio reprogramar» (programación vigente cancelable)
        await pg.evaluate("switchMode('arsenal');aSwitch('masiva');document.getElementById('a-masiva-mes').value='11';document.getElementById('a-masiva-aini').value='2026';document.getElementById('a-masiva-mes-reprog').value='2';calcularMasiva('arsenal')")
        await pg.wait_for_timeout(8000)
        r=await pg.evaluate("""(()=>{calcularAjustesMasiva('arsenal');const F=window._ajustesCero_arsenal,R=window._masiva_res;
          const malas=F.filter(f=>f.antes).filter(f=>{const d=R.find(x=>x.art===f.art).filaAnual[f.anio][MESES[f.mesNum-1]];return d.esFuturo||!(f.cobSin>parseFloat(document.getElementById('a-masiva-cmax').value));});
          return{antes:F.filter(f=>f.antes).length,meses:[...new Set(F.filter(f=>f.antes).map(f=>f.mes+' '+f.anio))],malas:malas.length,despues:F.filter(f=>!f.antes&&(f.anio*12+f.mesNum)<2027*12+2).length}})()""")
        ok(r['antes']>0 and 'Enero 2027' in r['meses'] and r['malas']==0 and r['despues']==0,f"Bajar a cero: meses antes de reprogramar (Nov–Ene) con cobertura sin el ingreso sobre el máximo ({r})")
        # Resumen (situación actual sin reprogramar)
        r=await pg.evaluate("""(()=>{localStorage.removeItem('pd_res');RES=null;aSwitch('dash');resParam('meses',2);const R=RES_ULT,c=_resCfg();
          const x=R.filas.find(f=>f.art==='PARACETAMOL 500 MG COMPRIMIDO');
          // verificación independiente: stock − vencido + programación − consumo × meses
          let s=x.stock-x.vencido;x.detalle.forEach(d=>{s+=d.p-x.cons-d.ven;});
          resParam('vista','ped');const ped=_resFiltradas();resParam('vista','sit');
          resParam('grupo','t:SAPU');const sapu=_resFiltradas();resParam('grupo','');resParam('prog','sin');const sin=_resFiltradas().length;resParam('prog','todos');
          resParam('q','paracetamol 500');const q=_resFiltradas().map(f=>f.art);resParam('q','');
          const ords=_resFiltradas().map(f=>f.cob).filter(v=>v!=null&&isFinite(v));
          return{meses:R.meses.length,ok:Math.abs(s-x.sFin)<1e-6,cob:Math.abs(x.cob-x.sFin/x.cons)<1e-9,ped:ped.length&&ped.every(f=>f.pedido===Math.max(0,Math.ceil(c.obj*f.cons-f.sFin))&&f.pedido>0),
            sapu:sapu.length>0&&sapu.every(f=>f.tags.includes('SAPU')),sin,q,orden:ords.every((v,i)=>!i||ords[i-1]<=v),tabla:!!document.querySelector('#res-tabla table'),prom3:x.fuente}})()""")
        ok(r['meses']==3 and r['ok'] and r['cob'] and r['ped'] and r['sapu'] and r['q']==['PARACETAMOL 500 MG COMPRIMIDO'] and r['orden'] and r['tabla'] and r['prom3']=='prom. 3 m',f"Resumen: stock fin de período, meses cubiertos, pedido especial, filtros, buscador y orden ({r})")
        await pg.evaluate("document.querySelector('details.res-viejo').open=true;calcularDashboard('arsenal')"); await pg.wait_for_timeout(1500)
        ok(await pg.evaluate("document.getElementById('a-dash-viejo').innerText.length>200&&!!document.getElementById('res-tabla')"),'Resumen: los indicadores anteriores siguen disponibles en el desplegable')
        # Órdenes de compra (sin sitio compartido: en este navegador)
        await pg.evaluate("switchMode('oc')"); await pg.wait_for_timeout(500)
        await pg.click('#view-oc button.oc-prim >> text=+ Nueva OC')
        await pg.fill('#oc-f-num','777-1-LE26'); await pg.fill('#view-oc .oc-fgrid input[list=oc-dl-prov]','GALENICUM HEALTH CHILE SPA')
        await pg.fill('#view-oc .oc-f-art >> nth=0','PARACETAMOL 500 MG COMPRIMIDO'); await pg.fill('#view-oc .oc-ft tbody tr:nth-child(1) td:nth-child(2) input','2.000')
        await pg.click('text=Guardar OC'); await pg.wait_for_timeout(500)
        await pg.locator('#view-oc tr',has_text='PARACETAMOL').locator('button.oc-eb',has_text='OK').click(); await pg.wait_for_timeout(300)
        await pg.click('#view-oc button.oc-prim >> text=Proceder cierre'); await pg.wait_for_timeout(300)
        r=await pg.evaluate("(()=>{const o=Object.values(OC.ocs)[0];return{n:Object.keys(OC.ocs).length,est:o.estado,l:o.lineas.map(l=>[l.estado,l.recib,l.cant]),provs:OC_PROVS_KITE.length}})()")
        ok(r['n']==1 and r['est']=='cerrada' and r['l']==[['ok',2000,2000]] and r['provs']>=70,f"Órdenes de compra: crear, marcar OK (recibido = pedido) y cerrar; {r['provs']} proveedores de Kite ({r})")
        await pg.click('text=+ Nueva OC'); await pg.fill('#oc-f-num','777-1-le26'); await pg.fill('#view-oc .oc-fgrid input[list=oc-dl-prov]','X'); await pg.fill('#view-oc .oc-f-art >> nth=0','A'); await pg.fill('#view-oc .oc-ft tbody tr:nth-child(1) td:nth-child(2) input','1')
        await pg.click('text=Guardar OC'); await pg.wait_for_timeout(300)
        ok('Ya existe la OC' in await pg.inner_text('#oc-f-msg'),'Órdenes de compra: no permite N° de OC repetido')
        await pg.click('#view-oc .oc-facc button >> text=Cancelar'); await pg.evaluate("switchMode('arsenal')")
        # ── Escenario F: Reposición SAPU ──
        await pg.evaluate("switchMode('sapu');sapuSwitch('repo');repoParam('frec','semanal');repoParam('vista','mes');repoParam('mes','2026-11')")
        await pg.wait_for_timeout(500)
        r=await pg.evaluate("""(()=>{const F=_repoUltimo.filas;const by=n=>F.find(a=>a.art.startsWith(n));
          const excl=F.filter(a=>a.P.excl);
          return{n:F.length,
            exclSoloBodega:excl.every(a=>a.picks.every(p=>p.origen==='Bodega central')),
            fefoLido:(by('LIDOCAINA').picks[0]||{}).lote,
            paraB:(repoParam('mes','2026-10'),_repoUltimo.filas.find(a=>a.art.startsWith('PARACETAMOL 500')).picks[0]||{}).origen,
            salbFalt:by('SALBUTAMOL').falt>0}})()""")
        ok(r['n']==16 and r['exclSoloBodega'],f'Reposición SAPU: 16 artículos y exclusivos solo desde bodega central ({r})')
        ok(r['fefoLido']=='BC-LI01' and r['paraB']=='Bodega central',f"Reposición SAPU: FEFO (lidocaína {r['fefoLido']}) y bodega antes que farmacia (paracetamol: {r['paraB']})")
        ok(r['salbFalt'],'Reposición SAPU: respeta la reserva de farmacia (salbutamol con faltante)')
        r=await pg.evaluate("""(()=>{repoParam('mes','2026-11');const a='ATROPINA 1 MG/ML SOLUCIÓN INYECTABLE AMPOLLA';prog[a]={origen:'CENABAST',años:{2026:{diciembre:50}},origenPorAño:{2026:'CENABAST'},desglose:{}};repoParam('mes','2026-12');
          return _repoUltimo.filas.find(x=>x.art===a).lleg.map(l=>l.q+'|'+l.destino)})()""")
        ok(r==['50|Bodega central'],f'Reposición SAPU: lo programado de un exclusivo llega a bodega central ({r})')
        r=await pg.evaluate("""(()=>{sapuSwitch('repo');repoParam('vista','semana');repoParam('frec','semanal');const F=_repoUltimo.filas;const by=n=>F.find(a=>a.art.startsWith(n));
          return{fuente:by('PARACETAMOL 500').P.fStock,stock:by('PARACETAMOL 500').P.stockSapu,col:_repoCfg().sapuStockArchivo.includes('Stock Sist.')}})()""")
        ok(r['fuente'].startswith('AVIS') and r['stock']==240 and r['col'],f'Stock SAPU (AVIS): usa «Stock Sist.» por lote, no «Stock Total» ({r})')
        r=await pg.evaluate("""(()=>{sapuSwitch('repo');const tot=document.querySelectorAll('#repo-tabla tbody tr[data-art]').length;repoBuscar('paracetamol');
          const vis=[...document.querySelectorAll('#repo-tabla tbody tr[data-art]')].filter(t=>t.style.display!=='none').map(t=>t.dataset.art);
          repoParam('vista','semana');const sigue=[...document.querySelectorAll('#repo-tabla tbody tr[data-art]')].filter(t=>t.style.display!=='none').length;repoBuscar('');
          return{tot,vis,sigue,q:document.getElementById('repo-buscar').value}})()""")
        ok(r['tot']>1 and r['vis'] and all('PARACETAMOL' in v for v in r['vis']) and r['sigue']==len(r['vis']),f'Reposición SAPU: buscador filtra y se mantiene al recalcular ({r})')
        r=await pg.evaluate("""(()=>{sapuSwitch('repo');repoParam('vista','semana');const vis=()=>[...document.querySelectorAll('#repo-tabla tbody tr[data-art]')].filter(t=>t.style.display!=='none');
          const F=_repoUltimo.filas;repoFiltrar('falt');const nf=vis().length;const okf=vis().every(t=>F.find(a=>normArt(a.art)===t.dataset.art).falt>0);
          repoFiltrar('rep');const nr=vis().length;repoParam('vista','semana');const sigue=vis().length;repoFiltrar('rep');const todos=vis().length;
          const th=[...document.querySelectorAll('#repo-tabla th')].map(t=>t.textContent).find(t=>t.startsWith('Stock SAPU'));
          return{nf,okf,kf:F.filter(a=>a.falt>0).length,nr,kr:F.filter(a=>a.env>0).length,sigue,todos,n:F.length,th}})()""")
        ok(r['nf']==r['kf'] and r['okf'] and r['nr']==r['kr'] and r['sigue']==r['nr'] and r['todos']==r['n'] and r['th']=='Stock SAPUactual',f'Reposición SAPU: clic en tarjetas filtra (faltante / a reponer), se mantiene al recalcular y «Stock SAPU actual» ({r})')
        r=await pg.evaluate("""(()=>{const R=_repoCfg();const a='SALBUTAMOL AEROSOL 100 MCG/DOSIS INHALADOR';const bak=JSON.stringify(R.bodega[a]||[]);
          R.bodega[a]=[{lote:'V',venc:'09/2026',stock:50},{lote:'B',venc:'03/2027',stock:7},{lote:'A',venc:'12/2026',stock:5}];const d=_bodCentralDisp(a);R.bodega[a]=JSON.parse(bak);
          return{q:d.q,fefo:d.lotes.map(l=>l.lote)}})()""")
        ok(r=={'q':12,'fefo':['A','B']},f'Pedido especial: stock de bodega central sin lotes vencidos y en orden FEFO ({r})')
        # ── Escenario G: consumo real del SAPU (mensual en archivo único y diario) ──
        r=await pg.evaluate("""(()=>{const c=_sapuCfg();return{dias:c.diarioDias.length,real:_sapuConsReal('PARACETAMOL 500 MG COMPRIMIDO'),fuente:(sapuSwitch('repo'),_repoUltimo.filas.find(a=>a.art==='PARACETAMOL 500 MG COMPRIMIDO').P.cons.f)}})()""")
        ok(r['dias']==15 and r['real']['tipo']=='diario' and r['fuente'].startswith('Real diario'),f"Consumo real SAPU: 15 días informados y Reposición usa el real diario ({r['fuente']})")
        pg2,errs2=await nueva(b)
        await pg2.set_input_files('#fi-prog',f('05')); await pg2.wait_for_timeout(900)
        r=await pg2.evaluate("[cons_mensual['PARACETAMOL 500 MG COMPRIMIDO'][2026]['julio'],(_sapuCfg().consMensualSapu['PARACETAMOL 500 MG COMPRIMIDO']||{})[2026],!!cons_mensual['ATROPINA 1 MG/ML SOLUCIÓN INYECTABLE AMPOLLA']]")
        ok(r[0]==19874 and r[1] and r[1].get('julio')==399 and r[2] is False,f'Archivo único: «Consumo SAPU 2026» no se suma al botiquín ({r})')
        ok(not errs2,f'Archivo único con SAPU sin errores ({errs2})')
        errs=[e for e in errs if not e.startswith('DIALOGO: Se cargarán los datos FICTICIOS')]
        ok(not errs,f'Botón → sin errores JS ni alertas: {errs}')
        # ── Escenario D: buscador de la Ayuda ──
        pg,errs=await nueva(b)
        await pg.evaluate("switchMode('ayuda')")
        r=await pg.evaluate("({fuera:document.querySelectorAll('.arch-card:not(#view-ayuda .arch-card)').length,dentro:document.querySelectorAll('#view-ayuda .arch-grid > .arch-card').length,ids:[...document.querySelectorAll('[id]')].map(e=>e.id).filter((x,i,a)=>a.indexOf(x)!==i)})")
        ok(r['fuera']==0 and r['dentro']==13 and not r['ids'],f'Ayuda: las 13 fichas de archivos están solo en la Ayuda y no hay ids duplicados ({r})')
        r=await pg.evaluate("(ayudaBuscar('respaldo'),document.querySelector('#ay-res .ay-t')?.textContent)")
        ok(r=='Exportar e importar respaldo',f'Buscador → «respaldo»: {r}')
        r=await pg.evaluate("(ayudaBuscar('monte carlo'),[...document.querySelectorAll('#ay-res .ay-t')].map(e=>e.textContent))")
        ok(r==['Probabilidad de quiebre'],f'Buscador → «monte carlo»: {r}')
        n=await pg.evaluate("(()=>{let f=0;AYUDA_CATALOGO.filter(e=>e.go).forEach(e=>{try{ayudaIr(e.go)}catch(x){f++}});return f})()")
        ok(n==0 and not errs,f'Buscador → todos los «Ir →» sin errores ({errs})')
        # ── Escenario H: invariantes de Reposición SAPU con datos aleatorios ──
        pg3,errs3=await nueva(b)
        r=await pg3.evaluate("window.__FUZZ_N=120;"+open(os.path.join(BASE,'fuzz_reposicion.js'),encoding='utf-8').read())
        ok(r['casos']==120 and not r['fallas'],f"Reposición SAPU: 120 escenarios aleatorios sin violar invariantes (despacho = picking, unidades enteras, sin stocks negativos, reserva de farmacia, destino de lo programado) {r['fallas'][:3]}")
        ok(not errs3,f'Invariantes sin errores JS ({errs3})')
        # ── Escenario E: IA local (homologación, calidad, política, grupos) ──
        pg,errs=await nueva(b)
        h=await pg.evaluate("homEvaluar()")
        ok(h['nuevo']>h['anterior'] and h['errDosisN']<=h['errDosisJ'],f"Homologación: {h['nuevo']:.0%} vs {h['anterior']:.0%} anterior; errores de dosis {h['errDosisN']} vs {h['errDosisJ']}")
        r=await pg.evaluate("(r=>[r.art,r.det.bloqueo])(homSugerir('LOSARTAN 100 MG CM'))")
        ok(r[1] is True,f'Homologación: no sugiere dosis distinta ({r})')
        await pg.click('#demo-bar button'); await pg.wait_for_timeout(5500)
        n=await pg.evaluate("calidadRevisar().length")
        ok(n==0,f'Calidad: 0 avisos con datos demo correctos ({n})')
        await pg.evaluate("cons_mensual['LOSARTAN (POTASICO) 50 MG COMPRIMIDO'][2026]['marzo']*=10")
        r=await pg.evaluate("calidadRevisar().map(x=>x.sev+'|'+x.art)")
        ok(r==['alta|LOSARTAN (POTASICO) 50 MG COMPRIMIDO'],f'Calidad: detecta un cero de más sembrado ({r})')
        await pg.evaluate("cons_mensual['LOSARTAN (POTASICO) 50 MG COMPRIMIDO'][2026]['marzo']/=10")
        await pg.evaluate("switchMode('analisis');anSwitch('politica')"); await pg.click('#an-politica .btn-calc')
        await pg.wait_for_function("typeof politicaRes!=='undefined'&&politicaRes",timeout=60000)
        r=await pg.evaluate("({n:politicaRes.res.length,mejor:politicaRes.res.every(x=>x.rec.c<=x.actual.c+1e-9||!x.rec.cumple||x.actual.pq>({V:0.05,E:0.10}[x.ven]||1))})")
        ok(r['n']==40 and r['mejor'],f'Política: 40 artículos y la recomendada nunca es peor que la actual ({r})')
        await pg.evaluate("anSwitch('gruposcomp')"); await pg.click('#an-gruposcomp .btn-calc'); await pg.wait_for_timeout(1200)
        r=await pg.evaluate("({k:gruposRes.k,n:gruposRes.asig.length,unicos:new Set(gruposRes.grupos.map(g=>g.nombre)).size===gruposRes.grupos.length})")
        ok(3<=r['k']<=6 and r['n']==40 and r['unicos'],f'Grupos: {r}')
        errs=[e for e in errs if not e.startswith('DIALOGO: Se cargarán los datos FICTICIOS')]
        ok(not errs,f'IA local sin errores JS ({errs})')
        # ── Escenario I: Excel tal como los entrega AVIS (filas extra arriba) y consumo diario «Día N (día semana)» ──
        pg,errs=await nueva(b)
        SUBIR="""(id,aoa,nombre)=>{const ws=XLSX.utils.aoa_to_sheet(aoa),wb=XLSX.utils.book_new();XLSX.utils.book_append_sheet(wb,ws,'Export');
          const buf=XLSX.write(wb,{type:'array',bookType:'xlsx'});const dt=new DataTransfer();dt.items.add(new File([buf],nombre));
          const el=document.getElementById(id);el.files=dt.files;el.dispatchEvent(new Event('change',{bubbles:true}));}"""
        toma=[[],['TOMA DE INVENTARIO'],[],['Fecha',':','10/10/2026'],['Funcionario',':','(1-9) PERSONA DE PRUEBA'],[' '],[],[],
              ['Grupo','Familia','Código','Nombre Artículo','Ubicación','Vencimiento','Lote','Stock Sist.','Último Precio\nIngresado','Stock Valorizado'],
              ['MED','MED','1','PARACETAMOL 500 MG COMPRIMIDO','UNICO','13/02/2028','L1','1.234,00','0.00','0.00'],
              ['MED','MED','1','PARACETAMOL 500 MG COMPRIMIDO','UNICO','01/11/2027','L2','3.00','0.00','0.00']]
        await pg.evaluate(f"({SUBIR})('fi-inv',{toma!r},'toma.xlsx')".replace('None','null')); await pg.wait_for_timeout(700)
        r=await pg.evaluate("JSON.stringify(inv['PARACETAMOL 500 MG COMPRIMIDO'])")
        ok(r=='[{"lote":"L1","venc":"02/2028","stock":1234},{"lote":"L2","venc":"11/2027","stock":3}]',f'AVIS con 8 filas de título: Mi arsenal lee el inventario y los números en texto ({r})')
        await pg.evaluate("switchMode('sapu')"); await pg.wait_for_timeout(400)
        await pg.evaluate(f"({SUBIR})('sp-sst-fi',{toma!r},'toma.xlsx')".replace('None','null')); await pg.wait_for_timeout(700)
        r=await pg.evaluate("_repoCfg().sapuStockFecha")
        ok(r=='2026-10-10',f'Stock SAPU: toma la fecha del reporte AVIS ({r})')
        dia=[['ARTICULO','CONSUMO DIA 1 (LUNES) ','CONSUMO DIA 2 (MARTES)','CONSUMO DIA 3 (MIERCOLES)','CONSUMO DIA 4 (JUEVES)','CONSUMO DIA 5 (VIERNES)'],
             ['PARACETAMOL 500 MG COMPRIMIDO',4,0,2,6,None],['IBUPROFENO 400 MG COMPRIMIDO',1,1,0,0,None]]
        await pg.evaluate(f"({SUBIR})('sp-dia-fi',{dia!r},'consumo.xlsx')".replace('None','null')); await pg.wait_for_timeout(700)
        r=await pg.evaluate("(()=>{const c=_sdCfg();return{ini:c.diarioRel&&c.diarioRel.inicio,dias:c.diarioDias,p:c.diario['PARACETAMOL 500 MG COMPRIMIDO']}})()")
        ok(r['ini']=='2026-10-12' and r['dias']==['2026-10-12','2026-10-13','2026-10-14','2026-10-15'] and r['p']['2026-10-15']==6,
           f'Consumo diario «Día N (día)»: Día 1 = lunes 12/10, columna vacía no cuenta ({r})')
        r=await pg.evaluate("(()=>{sapuCambiarInicioRel('2026-10-05');const c=_sdCfg();return{dias:c.diarioDias,p:c.diario['PARACETAMOL 500 MG COMPRIMIDO']}})()")
        ok(r['dias']==['2026-10-05','2026-10-06','2026-10-07','2026-10-08'] and r['p']=={'2026-10-05':4,'2026-10-06':0,'2026-10-07':2,'2026-10-08':6},f'Consumo diario: cambiar «Día 1» re-fecha sin duplicar ({r})')
        r=await pg.evaluate("""JSON.stringify(['INSULINA CRISTALINA 100 UI/ML SOLUCIÓN INYECTABLEF','INSULINA CRISTALINA 200 UI/ML SOLUCIÓN INYECTABLEF','PARACETAMOL 500 MG COMPRIMIDOX'].map(n=>{const h=resolverNombreArticulo(n);return h.origen+'|'+h.avis}))""")
        ok(r=='["fraccionado|INSULINA CRISTALINA 100 UI/ML SOLUCIÓN INYECTABLE","nuevo|INSULINA CRISTALINA 200 UI/ML SOLUCIÓN INYECTABLE","aprox|PARACETAMOL 500 MG COMPRIMIDO"]',f'Homologación: «F» de fraccionado de AVIS se une a su artículo; tipeo de 1 letra solo con la misma dosis ({r})')
        r=await pg.evaluate("JSON.stringify(['SALBUTAMOL SOLUCION PARA NEBULIZADOR 5 MG ML GOTASF','PARACETAMOL 500 MG COMPRIMIDO F','ARTICULO INVENTADO 10 MG XYZF'].map(n=>{const h=resolverNombreArticulo(n);return h.origen+'|'+h.avis}))")
        ok(r=='["fraccionado|SALBUTAMOL SOLUCION PARA NEBULIZADOR 5 MG ML GOTAS","fraccionado|PARACETAMOL 500 MG COMPRIMIDO","nuevo|ARTICULO INVENTADO 10 MG XYZF"]',f'Fraccionados «F»: pegada o separada; no toca nombres que no terminan en forma farmacéutica ({r})')
        paq=f"""(()=>{{const wb=XLSX.utils.book_new();const add=(n,aoa)=>XLSX.utils.book_append_sheet(wb,XLSX.utils.aoa_to_sheet(aoa),n);
          add('Paquete',[['Pingüino Lotes — paquete de bodegas'],['Bodega','Fecha toma AVIS'],['Botiquín','02/11/2026'],['Bodega central','02/11/2026'],['SAPU','01/11/2026']]);
          add('Botiquín',{toma!r});add('Bodega central',[['Nombre Artículo','Vencimiento','Lote','Stock Sist.'],['IBUPROFENO 400 MG COMPRIMIDO','01/05/2028','BC1','300.00']]);
          add('SAPU',[['Nombre Artículo','Vencimiento','Lote','Stock Sist.'],['INSULINA CRISTALINA 100 UI/ML SOLUCIÓN INYECTABLEF','30/06/2028','BF1','1.00']]);
          const buf=XLSX.write(wb,{{type:'array',bookType:'xlsx'}});const dt=new DataTransfer();dt.items.add(new File([buf],'Paquete_bodegas.xlsx'));
          const el=document.getElementById('pkb-fi-s');el.files=dt.files;el.dispatchEvent(new Event('change',{{bubbles:true}}));}})()""".replace('None','null')
        await pg.evaluate(paq); await pg.wait_for_timeout(900)
        r=await pg.evaluate("""(()=>{const R=_repoCfg();return{inv:(inv['PARACETAMOL 500 MG COMPRIMIDO']||[]).length,bod:R.bodega['IBUPROFENO 400 MG COMPRIMIDO'][0].stock,
          sapu:R.sapuStock['INSULINA CRISTALINA 100 UI/ML SOLUCIÓN INYECTABLE'][0].stock,fecha:R.sapuStockFecha,st:[...document.querySelectorAll('.pkb-st')].map(e=>e.textContent.slice(0,2))}})()""")
        ok(r['inv']==2 and r['bod']==300 and r['sapu']==1 and r['fecha']=='2026-11-01' and r['st']==['✓ ','✓ '],f'Paquete de bodegas: carga Botiquín, Bodega central y SAPU de una vez ({r})')
        # Anexo «Pedido del jueves»: encabezados solo con el día de la semana y FERIADO
        pg2,errs2=await nueva(b)
        await pg2.evaluate("switchMode('sapu')")
        semana=[['ARTICULO','SABADO','DOMINGO','LUNES','MARTES','FERIADO','STOCK'],['PARACETAMOL 500 MG COMPRIMIDO',6,4,1,2,5,99],['IBUPROFENO 400 MG COMPRIMIDO',0,0,0,0,0,10]]
        await pg2.evaluate(f"({SUBIR})('sp-dia-fi',{semana!r},'semana.xlsx')".replace('None','null')); await pg2.wait_for_timeout(700)
        await pg2.evaluate(f"({SUBIR})('sp-sst-fi',{toma!r},'toma.xlsx')".replace('None','null')); await pg2.wait_for_timeout(700)
        r=await pg2.evaluate("""(()=>{sapuSwitch('quincenal');const c=_sdCfg();const p=QN_RES.rows.find(x=>x.name==='PARACETAMOL 500 MG COMPRIMIDO');
          return{ini:c.diarioRel.inicio,fer:c.diarioFeriados,dias:c.diarioDias.length,mW:Math.round(p.mW*100)/100,mD:p.mD,mn:p.mn,st:p.st,ibu:QN_RES.rows.find(x=>x.name==='IBUPROFENO 400 MG COMPRIMIDO').tipo,
            tabla:!!document.querySelector('#qn-tabla table'),visible:document.getElementById('sp-quincenal').style.display}})()""")
        # fin de semana = sáb, dom y feriado (6,4,5 → 5/día); hábil = lun, mar (1,2 → 1,5/día); mínimo = ceil(1,5 × 2 × 5) = 15
        ok(r['ini']=='2026-10-10' and r['fer']==['2026-10-14'] and r['dias']==5 and r['mW']==5 and r['mD']==1.5 and r['mn']==15 and r['st']==1237 and r['ibu']=='sin consumo' and r['tabla'] and r['visible']=='block',
           f'Pedido del jueves: días por nombre (SABADO…FERIADO), feriado como fin de semana, mínimo y stock AVIS ({r})')
        ok(not errs2,f'Pedido del jueves sin errores ({errs2})')
        ok(not errs,f'Escenario AVIS / diario relativo sin errores ({errs})')
        await b.close()
    print('\nRESULTADO:', 'TODO OK' if not fallas else f'{len(fallas)} FALLA(S)')
    sys.exit(1 if fallas else 0)
asyncio.run(main())
