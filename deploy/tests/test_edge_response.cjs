const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync(require('node:path').join(__dirname,'../edge-functions/authelia-edge-auth.js'),'utf8');
async function run(path,fetchMock,opts){const c={URL,Headers,Request,Response,console:{log(){},error(){}},addEventListener(){},fetch:fetchMock};vm.createContext(c);vm.runInContext(code,c);return c.handleRequest(new Request('https://nas.wttliou.top'+path,opts));}
(async()=>{
 for(const encoding of ['br','gzip','identity']){
  let n=0;const r=await run('/authelia/static/js/main.js',async(req,opts)=>{n++;assert.equal(opts.headers.get('Accept-Encoding'),'identity');assert.equal(opts.redirect,'manual');return new Response('const ok = true;', {headers:{'content-encoding':encoding,'content-length':'5','content-type':'text/javascript','content-security-policy':"default-src 'none'",'alt-svc':'h3=":5009"'}})});
  assert.equal(n,1);assert.equal(await r.text(),'const ok = true;');assert.equal(r.headers.get('content-encoding'),null);assert.equal(r.headers.get('content-length'),null);assert.equal(r.headers.get('alt-svc'),null);assert.equal(r.headers.get('content-security-policy'),"default-src 'none'");
 }
 let calls=0;let r=await run('/private',async()=>{calls++;return new Response(null,{status:401})});assert.equal(calls,1);assert.equal(r.status,302);
 calls=0;r=await run('/private',async()=>{calls++;return calls===1?new Response(null,{status:200}):new Response('private')});assert.equal(calls,2);assert.equal(await r.text(),'private');
 r=await run('/device-api/v1/transcriptions',async(req,opts)=>{assert.equal(req.method,'POST');assert.equal(await req.text(),'test-body');assert.equal(opts.headers.get('Authorization'),'Bearer test-only');return new Response('unauthorized',{status:401})},{method:'POST',body:'test-body',headers:{Authorization:'Bearer test-only'}});assert.equal(r.status,401);assert.equal(await r.text(),'unauthorized');assert.equal(r.headers.get('cache-control'),'private, no-store');
 r=await run('/device-api/v1/transcriptions',async()=>{throw new Error('private secret')});assert.equal(r.status,502);const b=await r.text();assert.ok(!b.includes('private secret'));assert.ok(b.includes('unknown'));
 console.log('7 scenarios passed: identity/br/gzip headers, auth deny/allow, POST+401 preservation, safe 502');
})().catch(e=>{console.error(e);process.exitCode=1});
