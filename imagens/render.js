const { chromium } = require('playwright');
const fs=require('fs'), path=require('path');
(async()=>{
  const b=await chromium.launch();
  for (const f of fs.readdirSync('html')) {
    const nome=f.replace('.html','');
    const p=await b.newPage({viewport:{width:1080,height:1350},deviceScaleFactor:2});
    await p.goto('file://'+path.resolve('html',f)); await p.evaluate(()=>document.fonts.ready); await p.waitForTimeout(400);
    const els=await p.$$('.slide');
    fs.mkdirSync('png',{recursive:true});
    for (let i=0;i<els.length;i++) await els[i].screenshot({path:`png/${nome}-${String(i+1).padStart(2,'0')}.png`});
    if (els.length>1) await p.pdf({path:`png/${nome}.pdf`,width:'1080px',height:'1350px',printBackground:true});
    await p.close();
  }
  await b.close();
})();
