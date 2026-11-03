(()=>{
  const out={casos:0,fallas:[]};
  const rng=(()=>{let a=12345;return()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};})();
  const arts=ARTS.filter(a=>!ARTS_DINAMICOS[a]).slice(0,60);
  const c=_sapuCfg();const R=_repoCfg();
  const bak={inv:JSON.stringify(inv),cons:JSON.stringify(cons_map),prog:JSON.stringify(prog),R:JSON.stringify(R),ap:c.apertura,diario:JSON.stringify(c.diario||{}),dd:JSON.stringify(c.diarioDias||[]),cms:JSON.stringify(c.consMensualSapu||{})};
  c.diario={};c.diarioDias=[];c.consMensualSapu={};
  for(let caso=0;caso<(window.__FUZZ_N||300);caso++){
    inv={};cons_map={};prog={};R.bodega={};R.mm={};R.excl={};
    R.frec=rng()<0.5?'semanal':'mensual';R.reserva=[0,1,2,3][Math.floor(rng()*4)];R.dia=1+Math.floor(rng()*28);
    const hoy=new Date();c.apertura=(()=>{const d=new Date(hoy.getFullYear(),hoy.getMonth()+Math.floor(rng()*5)-2,1);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0');})();
    const elegidos=arts.filter(()=>rng()<0.15);
    elegidos.forEach(a=>{
      const cm=Math.round(rng()*500);if(rng()<0.6)cons_map[a]=Math.round(rng()*2000);
      const venc=()=>{const d=new Date(hoy.getFullYear(),hoy.getMonth()+Math.floor(rng()*14)-2,1);return String(d.getMonth()+1).padStart(2,'0')+'/'+d.getFullYear();};
      if(rng()<0.7)inv[a]=[...Array(1+Math.floor(rng()*3))].map((_,i)=>({lote:'F'+i,venc:venc(),stock:Math.round(rng()*3000)}));
      if(rng()<0.6)R.bodega[a]=[...Array(1+Math.floor(rng()*3))].map((_,i)=>({lote:'B'+i,venc:venc(),stock:Math.round(rng()*300)}));
      const mn=Math.round(rng()*100),mx=mn+Math.round(rng()*200);
      R.mm[a]={min:mn,max:mx,excl:rng()<0.4?true:(rng()<0.5?false:null),stock:rng()<0.5?Math.round(rng()*mx):null,cons:cm};
      if(rng()<0.5){const y=hoy.getFullYear();prog[a]={origen:'CENABAST',años:{[y]:{},[y+1]:{}},origenPorAño:{},desglose:{}};MESES.forEach(m=>{prog[a].años[y][m]=Math.round(rng()*800);prog[a].años[y+1][m]=Math.round(rng()*800);});}
    });
    const hasta=new Date(hoy);hasta.setDate(hasta.getDate()+7*(4+Math.floor(rng()*20)));
    const sim=repoSimular(hasta);out.casos++;
    Object.values(sim.res).forEach(r=>{
      const P=r.P;const reserva=(+R.reserva||0)*(c.usarCesfam?P.cC:0);
      r.filas.forEach(f=>{
        const suma=f.picks.reduce((s,p)=>s+p.cant,0);
        const err=m=>{if(out.fallas.length<25)out.fallas.push(m+' | '+r.art.slice(0,30)+' sem '+f.ws.toISOString().slice(0,10));};
        if(Math.abs(suma-f.env)>1e-6)err('env≠Σpicks '+f.env+' vs '+suma);
        if(f.env>f.need+1e-6)err('env>need');
        if(f.need>0&&Math.abs(f.need-f.env-f.falt)>1e-6)err('need≠env+falt');
        if(f.picks.some(p=>Math.abs(p.cant-Math.round(p.cant))>1e-9))err('picking no entero '+f.picks.map(p=>p.cant).join(','));
        if(f.bodFin<-1e-9||f.farmFin<-1e-9||f.sFin<-1e-9)err('stock negativo');
        if(P.excl&&f.lleg.some(l=>l.destino!=='Bodega central'))err('llegada de exclusivo fuera de bodega');
        if(!P.excl&&f.lleg.some(l=>l.destino!=='Farmacia'))err('llegada de no exclusivo fuera de farmacia');
        const desdeF=f.picks.filter(p=>p.origen==='Farmacia').reduce((s,p)=>s+p.cant,0);
        if(desdeF>0&&f.farmPostPick!==undefined&&f.farmPostPick<reserva-1e-6)err('farmacia bajo reserva '+f.farmPostPick+' < '+reserva);
      });
    });
  }
  inv=JSON.parse(bak.inv);cons_map=JSON.parse(bak.cons);prog=JSON.parse(bak.prog);Object.assign(R,JSON.parse(bak.R));c.apertura=bak.ap;c.diario=JSON.parse(bak.diario);c.diarioDias=JSON.parse(bak.dd);c.consMensualSapu=JSON.parse(bak.cms);
  return out;
})()
