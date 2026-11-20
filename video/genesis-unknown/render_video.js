const { chromium } = require('playwright'); const fs=require('fs'), path=require('path');
(async()=>{
  const FPS=24, T=46, b=await chromium.launch(); const p=await b.newPage({viewport:{width:1080,height:1350},deviceScaleFactor:1});
  await p.goto('file://'+path.resolve('video.html')); await p.evaluate(()=>document.fonts.ready); await p.waitForTimeout(500);
  fs.mkdirSync('frames',{recursive:true}); const N=FPS*T;
  for(let i=0;i<N;i++){ await p.evaluate(t=>window.setT(t), i/FPS); await p.screenshot({path:`frames/f${String(i).padStart(5,'0')}.png`}); if(i%100===0) console.log('quadro',i,'de',N); }
  await b.close(); console.log('ok');
})();
