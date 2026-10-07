const {test}=require('node:test');
const assert=require('node:assert/strict');
const {FrameIndex}=require('../bilibili-recipe-controls.user.js');
const u32=n=>{const b=Buffer.alloc(4);b.writeUInt32BE(n>>>0);return b;};
const u64=n=>{const b=Buffer.alloc(8);b.writeBigUInt64BE(BigInt(n));return b;};
const box=(type,...parts)=>{const body=Buffer.concat(parts);return Buffer.concat([u32(body.length+8),Buffer.from(type),body]);};
const full=(v,f)=>Buffer.from([v,(f>>>16)&255,(f>>>8)&255,f&255]);
function init({scale=1000,defaultDuration=0,edit=null}={}){
 const tkhd=box('tkhd',full(0,0),u32(0),u32(0),u32(1)),mdhd=box('mdhd',full(0,0),u32(0),u32(0),u32(scale)),hdlr=box('hdlr',full(0,0),u32(0),Buffer.from('vide'));
 const edts=edit===null?Buffer.alloc(0):box('edts',box('elst',full(0,0),u32(1),u32(0),u32(edit),Buffer.from([0,1,0,0])));
 return box('moov',box('trak',tkhd,edts,box('mdia',mdhd,hdlr)),box('mvex',box('trex',full(0,0),u32(1),u32(1),u32(defaultDuration),u32(0),u32(0))));
}
function fragment(start,durations,offsets=null,{version=0,tfdt64=false,explicitDuration=true,tfhdDuration=0}={}){
 const flags=(explicitDuration?0x100:0)|(offsets?0x800:0),parts=[];
 for(let n=0;n<durations.length;n++){if(explicitDuration)parts.push(u32(durations[n]));if(offsets)parts.push(u32(offsets[n]));}
 return box('moof',box('traf',box('tfhd',full(0,tfhdDuration?8:0),u32(1),...(tfhdDuration?[u32(tfhdDuration)]:[])),box('tfdt',full(tfdt64?1:0,0),tfdt64?u64(start):u32(start)),box('trun',full(version,flags),u32(durations.length),...parts)));
}
test('variable frame durations choose exactly adjacent presentation intervals',()=>{
 const i=new FrameIndex();i.push(Buffer.concat([init(),fragment(0,[40,80,20,100])]));
 assert.equal(i.locate(.05,-1).pts,0);assert.equal(i.locate(.05,1).pts,.12);assert.equal(i.locate(.13,1).pts,.14);
 assert.throws(()=>i.locate(0,-1),/相邻/);assert.throws(()=>i.locate(.15,1),/相邻/);
});
test('signed composition offsets reorder B frames without guessing FPS',()=>{
 const i=new FrameIndex();i.push(Buffer.concat([init(),fragment(0,[40,40,40],[0,40,-40],{version:1})]));
 assert.deepEqual(i.groups()[0].frames.map(f=>f.pts),[0,.04,.08]);assert.equal(i.locate(.01,1).pts,.04);
});
test('trex and tfhd duration defaults, 64-bit decode time and timestampOffset',()=>{
 const i=new FrameIndex();i.push(init({defaultDuration:40}));i.push(fragment(5000,[0,0],null,{tfdt64:true,explicitDuration:false}),{offset:-5});
 assert.ok(Math.abs(i.locate(.01,1).pts-.04)<1e-9);
 const j=new FrameIndex();j.push(init());j.push(fragment(0,[0,0],null,{explicitDuration:false,tfhdDuration:80}));assert.equal(j.locate(.01,1).pts,.08);
});
test('single rate-one edit transforms media time to presentation time',()=>{
 const i=new FrameIndex();i.push(init({edit:100}));i.push(fragment(100,[40,40]));assert.equal(i.locate(.01,1).pts,.04);
});
test('out-of-order contiguous fragments connect, missing fragments never connect',()=>{
 const i=new FrameIndex();i.push(init());i.push(fragment(160,[40,40]));i.push(fragment(0,[40,40]));
 assert.throws(()=>i.locate(.05,1),/相邻/);i.push(fragment(80,[40,40]));assert.equal(i.locate(.05,1).pts,.08);
});
test('re-appending overlapping metadata replaces rather than duplicates samples',()=>{
 const i=new FrameIndex();i.push(init());const f=fragment(0,[40,40]);i.push(f);i.push(f);assert.equal(i.groups()[0].frames.length,2);
});
test('arbitrary chunk boundaries and large mdat are handled without retaining media',()=>{
 const data=Buffer.concat([init(),fragment(0,[40,40]),box('mdat',Buffer.alloc(100000)),fragment(80,[40,40])]);
 for(const size of [1,7,13,128,4096]){const i=new FrameIndex();for(let p=0;p<data.length;p+=size)i.push(data.subarray(p,p+size));assert.equal(i.locate(.05,1).pts,.08);assert.equal(i.box,null);assert.equal(i.header.length,0);}
});
test('new initialization invalidates the old quality timeline',()=>{
 const i=new FrameIndex();i.push(Buffer.concat([init(),fragment(0,[40,40])]));i.push(init({scale:2000}));assert.throws(()=>i.locate(.01),/帧时间表/);
 i.push(fragment(0,[40,40]));assert.equal(i.locate(.001,1).pts,.02);
});
test('malformed, oversized, unsupported or unsafe time tables fail instead of jumping seconds',()=>{
 assert.throws(()=>new FrameIndex().push(Buffer.concat([u32(4),Buffer.from('moov')])));
 assert.throws(()=>new FrameIndex().push(Buffer.concat([u32(3*1024*1024),Buffer.from('moov')])));
 assert.throws(()=>new FrameIndex().push(init(),{mode:'sequence'}),/不支持/);
 assert.throws(()=>new FrameIndex().push(init(),{end:10}),/不支持/);
 assert.throws(()=>new FrameIndex().push(fragment(0,[40])),/初始化/);
 const i=new FrameIndex();i.push(init());assert.throws(()=>i.push(fragment(0,[0])),/样本/);
 const j=new FrameIndex();j.push(init());assert.throws(()=>j.push(fragment(Number.MAX_SAFE_INTEGER,[40],null,{tfdt64:true})),/样本/);
 const k=new FrameIndex();k.push(init());k.push(fragment(0,[40,40],[40,0]));assert.throws(()=>k.locate(.05),/非唯一/);
});
