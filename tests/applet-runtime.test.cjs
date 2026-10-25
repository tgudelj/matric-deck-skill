// Standard Node test runner; no npm packages, MATRIC connection or system actions.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.join(__dirname,'../skills/matric-decks/assets/applet-starter');
function environment(id='instance-1'){
 const handlers={},sent=[];
 const parent={postMessage:(data,origin)=>sent.push({data,origin})};
 const window={parent,location:{hash:'#'+id},addEventListener:(name,handler)=>handlers[name]=handler,
               removeEventListener:(name,handler)=>{if(handlers[name]===handler)delete handlers[name];}};
 const ctx={window};vm.createContext(ctx);
 for(const file of ['bridge.js','history.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),ctx);
 return {window,parent,handlers,sent};
}
test('bridge uses control identity, exposes event payload and scopes requests',()=>{
 const e=environment();const bridge=new e.window.MatricApplet({});
 bridge.requestVariables('demo_signal');bridge.emit('select-sample',{value:0,index:0});bridge.release('select-sample');
 assert.equal(e.sent[0].data.messageId,'cce-instance-1');
 assert.equal(e.sent[0].data.payload.Data.variablePrefixes[0],'demo_signal');
 assert.equal(e.sent[1].data.payload.Data.value,0);
 assert.equal(e.sent[2].data.payload.EventName,'select-sample-release');
 const other=environment('instance-2');new other.window.MatricApplet({}).requestVariables();
 assert.equal(other.sent[0].data.messageId,'cce-instance-2');
});
test('host feedback accepts only parent messages, preserving zero and false without emitting',()=>{
 const e=environment();const received=[];
 const bridge=new e.window.MatricApplet({params:p=>received.push(p),variables:v=>received.push(v),resize:r=>received.push(r)});
 for(const messageId of ['PARAMSUPDATE','VARIABLESUPDATE','RESIZE']){
  e.handlers.message({source:{},origin:'https://foreign.invalid',data:{messageId,payload:{value:9}}});
  e.handlers.message({source:e.parent,origin:'http://host.test',data:{messageId,payload:{value:0,enabled:false}}});
 }
 assert.equal(received.length,3);assert.equal(received[0].value,0);assert.equal(received[1].enabled,false);
 assert.equal(e.sent.length,0);bridge.emit('select-sample',{});assert.equal(e.sent[0].origin,'http://host.test');
 bridge.dispose();assert.equal(e.handlers.message,undefined);
});
test('invalid bridge payloads and standalone view cannot trigger actions',()=>{
 const e=environment();let calls=0;new e.window.MatricApplet({params:()=>calls++});
 for(const payload of [null,[],3,'bad'])e.handlers.message({source:e.parent,data:{messageId:'PARAMSUPDATE',payload}});
 assert.equal(calls,0);
 const standalone=environment('');new standalone.window.MatricApplet({}).emit('select-sample',{});
 assert.equal(standalone.sent.length,0);
});
test('history preserves zero, rejects unavailable/boolean/non-finite values and bounds growth',()=>{
 const model=new (environment().window.HistoryModel)();
 model.configure({SampleLimit:3});assert.equal(model.update({skill_demo_signal:0}),true);
 for(const value of [null,undefined,false,'',{},Infinity,'NaN'])assert.equal(model.update({skill_demo_signal:value}),false);
 assert.equal(model.update({skill_demo_signal:0}),false);
 for(const value of [10,20,30,40])model.update({skill_demo_signal:value});
 assert.equal(JSON.stringify(model.values),'[20,30,40]');
 assert.equal(model.select(-100).value,20);assert.equal(model.select(999).value,40);
 assert.equal(model.select(NaN),null);
});
test('parameter changes retain false/zero semantics, clear old signal data and clamp lengths',()=>{
 const model=new (environment().window.HistoryModel)();
 model.update({skill_demo_signal:7});model.configure({ShowValues:false,SampleLimit:0});
 assert.equal(model.settings.ShowValues,false);assert.equal(model.settings.SampleLimit,3);
 assert.equal(model.configure({SignalVariable:'another'}),true);assert.equal(model.values.length,0);
 assert.equal(model.update({skill_demo_signal:8}),false);assert.equal(model.update({another:'0'}),true);
 model.configure({SampleLimit:10000});assert.equal(model.settings.SampleLimit,120);
});
test('auto and percent chart geometry is finite and remains within the plot',()=>{
 const model=new (environment().window.HistoryModel)();
 assert.equal(model.points().length,0);model.update({skill_demo_signal:5});
 assert.equal(model.points()[0][0],300);assert.equal(model.points()[0][1],120);
 model.configure({Scale:'percent'});for(const value of [-30,40,140])model.update({skill_demo_signal:value});
 for(const [x,y]of model.points()){assert.ok(Number.isFinite(x)&&Number.isFinite(y));assert.ok(x>=24&&x<=576&&y>=24&&y<=216);}
});
test('finite extreme signal ranges do not overflow plot geometry',()=>{
 const model=new (environment().window.HistoryModel)();
 for(const value of [-Number.MAX_VALUE,0,Number.MAX_VALUE])model.update({skill_demo_signal:value});
 for(const [x,y]of model.points())assert.ok(Number.isFinite(x)&&Number.isFinite(y));
});
