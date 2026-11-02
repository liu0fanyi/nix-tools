// Real backend + immutable frontend. No API fulfil/mocking and no user profile.
const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
(async()=>{
 const f=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
 const {createTagCore}=await import(pathToFileURL(f.bridge_module).href);
 const {instance}=await WebAssembly.instantiate(fs.readFileSync(f.bridge),{});
 const core=createTagCore(instance.exports);
 assert.notEqual(core.fileKey('node-a','/cards'),core.fileKey('node-b','/cards'));
 assert.equal(core.fileKey('node-a','/cards'),core.fileKey('node-a','/cards'));
 console.log('PASS shared_wasm');
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH,headless:true,args:['--no-sandbox']});
 const deadline=setTimeout(()=>{console.error('Combination browser deadline exceeded');browser.close().finally(()=>{process.exitCode=1;});},90000);
 try {
  for(const mode of ['fresh','aliases_content_reload','progress_conflict','unknown_operation']) {
   const context=await browser.newContext({httpCredentials:{username:f.username,password:f.password}});
   try {
    await context.route('**/*',route=>new URL(route.request().url()).origin===f.base?route.continue():route.abort());
    await context.addInitScript(({mode,base})=>{
     if(location.origin!==base||localStorage.getItem('fixture-seeded'))return;
     localStorage.setItem('fixture-seeded','1');
     if(['aliases_content_reload','progress_conflict'].includes(mode)) {
      for(const storage of [localStorage,sessionStorage]) {
       storage.setItem('dufs-plus:view-mode:/cards','grid');storage.setItem('dufs-plus:view-mode:/cards/','waterfall');
       storage.setItem('dufs:progress:location:default:/cards','page:9');
       storage.setItem('dufs:progress:location:default:/cards/',mode==='progress_conflict'?'page:10':'page:9');
      }
     }
     if(mode==='unknown_operation')localStorage.setItem('dufs-plus.pending-metadata-repairs.v1','[{"Unknown":{}}]');
    },{mode,base:f.base});
    const page=await context.newPage();const writes=[];
    page.on('request',r=>{if(!['GET','HEAD','OPTIONS'].includes(r.method()))writes.push(r.url());});
    const receipt='dufs-plus:workspace-namespace:v1';
    await page.goto(f.base+'/?tagbrowser=content&tagbrowserSession=bundle-fixture#/library/book.md?location=default');
    if(['progress_conflict','unknown_operation'].includes(mode)) {
     await page.getByText('工作区暂未就绪',{exact:true}).waitFor();
     assert.equal(await page.evaluate(key=>localStorage.getItem(key),receipt),null);
     assert.equal(writes.length,0);
     if(mode==='progress_conflict') {
      const body=await page.locator('body').innerText();assert(body.includes('阅读进度')&&body.includes('localStorage'));
      assert(!body.includes('page:9')&&!body.includes('page:10'));
      assert.deepEqual(await page.evaluate(()=>[localStorage.getItem('dufs:progress:location:default:/cards'),localStorage.getItem('dufs:progress:location:default:/cards/')]),['page:9','page:10']);
     }
    }else{
     await page.waitForFunction(key=>localStorage.getItem(key)==='canonical-v2:bundle-fixture',receipt);
     assert.equal(await page.getByText('工作区暂未就绪',{exact:true}).count(),0);
     await page.getByRole('heading',{name:'Synthetic original file',exact:true}).waitFor();
     if(mode==='aliases_content_reload') {
      const verify=()=>{
       for(const storage of [localStorage,sessionStorage]) {
        const backups=Object.keys(storage).filter(k=>k.startsWith('dufs-plus:workspace-namespace-alias-backup:v1:')).map(k=>JSON.parse(storage.getItem(k)));
        for(const [key,value] of [['dufs-plus:view-mode:/cards','grid'],['dufs-plus:view-mode:/cards/','waterfall'],['dufs:progress:location:default:/cards','page:9'],['dufs:progress:location:default:/cards/','page:9']]) {
         if(!backups.some(b=>b.key===key&&b.value===value))throw new Error('Exact original backup missing');
        }
        if(backups.length!==4||storage.getItem('dufs:progress:location:default:/dufs/cards')!=='page:9'||storage.getItem('dufs-plus:view-mode:/dufs/cards')!=='grid')throw new Error('Alias result mismatch');
       }
      };
      await page.evaluate(verify);await page.reload();
      await page.waitForFunction(key=>localStorage.getItem(key)==='canonical-v2:bundle-fixture',receipt);await page.evaluate(verify);
     }
    }
    console.log('PASS '+mode);
   }finally{await context.close();}
  }
 }finally{clearTimeout(deadline);await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
