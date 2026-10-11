// Saved speech -> shipped pause detector/capture -> real ASR -> original bus/native decision.
// Measures decision latency, not audible response onset or completed physical placement.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {MicrophoneInput} from '../src/physical_ai_lab/dume/web/voice-input.mjs';

const output=process.argv[2], fixtureDir=process.argv[3];
assert.ok(output&&fixtureDir,'Usage: node scripts/benchmark_responsiveness.mjs OUTPUT FIXTURES');
fs.mkdirSync(output,{recursive:false});fs.mkdirSync(fixtureDir,{recursive:true});
const cases=[
 ['screwdriver','Bring me the screwdriver, please.','fetch','screwdriver','common'],
 ['wrench','Could you hand me the wrench?','fetch','wrench','common'],
 ['hammer','Hand me the hammer, please.','fetch','hammer','common'],
 ['return','Put the screwdriver back in its rack.','return','screwdriver','common'],
 ['return-wrench','Return the wrench to its rack, please.','return','wrench','common'],
 ['wave','Wave hello, please.','gesture',null,'common'],
 ['help','What can you help me with?','answer',null,'general'],
 ['semantic','I need something for turning screws.','fetch','screwdriver','general'],
 ['negative',"Don't bring me the wrench.",'answer|clarify|unsupported',null,'guard'],
 ['multiple','Bring me the wrench and the hammer.','clarify',null,'guard'],
];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function request(base,route,options={}) {
 const response=await fetch(base+route,options),result=await response.json();
 assert.ok(response.ok,JSON.stringify(result));return result;
}
const base='http://127.0.0.1:8766',native='http://127.0.0.1:8765';
const post=(route,data={})=>request(base,route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
async function wait(predicate,limit=30000){const end=performance.now()+limit;while(performance.now()<end){const s=await request(base,'/state');if(predicate(s))return s;await sleep(40);}throw Error('State wait timed out');}
const fixtures=new Map();
for(const [name,text] of cases){
 const wav=path.join(fixtureDir,name+'.wav'),txt=path.join(fixtureDir,name+'.txt'),aiff=path.join(fixtureDir,name+'.aiff');
 if(!fs.existsSync(wav)){
  fs.writeFileSync(txt,text+'\n');
  for(const [cmd,args] of [['/usr/bin/say',['-o',aiff,'-f',txt]],['ffmpeg',['-nostdin','-v','error','-i',aiff,'-af','apad=pad_dur=1.2','-ar','16000','-ac','1',wav]]]){const r=spawnSync(cmd,args);assert.equal(r.status,0,r.stderr?.toString());}
 }
 assert.equal(fs.readFileSync(txt,'utf8').trim(),text,'Fixture changed');
 const raw=spawnSync('ffmpeg',['-nostdin','-v','error','-i',wav,'-f','f32le','pipe:1']);assert.equal(raw.status,0);
 fixtures.set(name,{bytes:fs.readFileSync(wav),pcm:new Float32Array(raw.stdout.buffer.slice(raw.stdout.byteOffset,raw.stdout.byteOffset+raw.stdout.byteLength))});
}
await wait(s=>s.model_status==='ready'&&s.speech_input.status==='ready'&&!s.busy,90000);
const rows=[];
for(let repeat=0;repeat<3;repeat++)for(const [name,text,action,object,category] of cases){
 await post('/reset');await wait(s=>!s.busy&&s.phase==='Ready'&&s.last_intent===null);
 const previous=(await request(native,'/state')).job_id, fixture=fixtures.get(name);
 let lastSpeech,paused,asrStart,asrEnd,submitted,recognized,taskId,error;
 const element=()=>({textContent:'',hidden:false,disabled:false,setAttribute(){}});
 class Recorder{static isTypeSupported(){return true;}constructor(){this.mimeType='audio/wav';this.state='inactive';}start(){this.state='recording';}stop(){this.state='inactive';this.ondataavailable({data:new Blob([fixture.bytes])});this.onstop();}}
 const mic=new MicrophoneInput({button:element(),cancel:element(),note:element(),heard:element(),Recorder,
  mediaDevices:{getUserMedia:async()=>({getTracks:()=>[{stop(){}}]})},
  monitor:(stream,detector,onPause)=>{let offset=0;const timer=setInterval(()=>{const values=fixture.pcm.subarray(offset,offset+640);offset+=640;const rms=values.length?Math.sqrt(values.reduce((n,v)=>n+v*v,0)/values.length):0;const now=performance.now();if(rms>=detector.threshold)lastSpeech=now;if(detector.sample(rms,now)){paused=now;onPause();}},40);return()=>clearInterval(timer);},
  fetchAudio:async(route,options)=>{asrStart=performance.now();const r=await fetch(base+route,options);asrEnd=performance.now();recognized=await r.clone().json();return r;},
  stopSpeech:()=>post('/speech-stop'),onStop:()=>{error='Unexpected Stop interpretation';},
  onText:async transcript=>{submitted=performance.now();taskId=(await post('/chat',{message:transcript})).task_id;},onError:e=>{if(e)error=e;},
 });
 mic.setInterruptEnabled(false);mic.setReady(true);await mic.start();
 let decided,observed;const end=performance.now()+90000;
 while(performance.now()<end&&!error){const s=await request(native,'/state');if(s.job_id!==previous&&s.last_intent){observed=s;decided=performance.now();break;}await sleep(40);}
 mic.close();
 const intent=observed?.last_intent;
 const correct=!!intent&&action.split('|').includes(intent.action)&&intent.object===object;
 const row={repeat,name,text,category,recognized:recognized?.text,intent,correct,error:error||(!decided?'Decision timeout':null),task_id:taskId,
  pause_ms:paused-lastSpeech,asr_ms:asrEnd-asrStart,submit_to_decision_ms:decided-submitted,end_of_speech_to_decision_ms:decided-lastSpeech,
  timing:'last voiced 40ms RMS sample -> native intent observed by 40ms HTTP polling; real-time saved audio, not live microphone; audible speech and placement excluded'};
 rows.push(row);fs.appendFileSync(path.join(output,'rows.jsonl'),JSON.stringify(row)+'\n');
 console.log(`${rows.length}/30 ${name}: ${Math.round(row.end_of_speech_to_decision_ms)} ms (${Math.round(row.submit_to_decision_ms)} decision) ${correct?'correct':'FAIL'}`);
 await post('/stop');await wait(s=>!s.busy&&!s.tasks.some(t=>t.status==='pending'||t.status==='running'));
 // The bridge also issues native Stop when it observes cancellation. Let that
 // acknowledgement settle before resetting the next trial's scene.
 await sleep(500);
}
const stats=group=>{const r=rows.filter(group),a=r.map(x=>x.end_of_speech_to_decision_ms).filter(Number.isFinite).sort((a,b)=>a-b);return{count:r.length,failures:r.filter(x=>!x.correct||x.error).length,median_ms:(a[Math.floor((a.length-1)/2)]+a[Math.floor(a.length/2)])/2,p95_ms:a[Math.ceil(a.length*.95)-1]};};
const summary={capture:'saved native speech + shipped automatic pause controller + actual local ASR and task bus',model_state:'already loaded; first sample reported separately, no model-load cold-start claim',first_sample:rows[0],overall:stats(()=>true),common:stats(r=>r.category==='common'),general:stats(r=>r.category==='general'),guards:stats(r=>r.category==='guard'),rows};
fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify({...summary,rows:undefined},null,2));
await post('/reset');await wait(s=>!s.busy&&s.phase==='Ready');
