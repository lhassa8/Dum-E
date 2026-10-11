// Shipped voice controller + actual local ASR + original task bus + native physics.
// Audio capture is a deterministic saved-speech fixture; real browser capture is checked separately.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {MicrophoneInput} from '../src/physical_ai_lab/dume/web/voice-input.mjs';

const output=process.argv[2];assert.ok(output,'Pass a fresh evidence directory');
fs.mkdirSync(output,{recursive:false});
const base='http://127.0.0.1:8766';
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function request(route,options={}) {
 const response=await fetch(base+route,options),result=await response.json();
 assert.ok(response.ok,JSON.stringify(result));return result;
}
const post=(route,data={})=>request(route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
const state=()=>request('/state');
for(let i=0;;i++){const s=await state();if(s.model_status==='ready'&&s.speech_input.status==='ready'&&!s.busy)break;assert.ok(i<300,'Models not ready');await sleep(100);}
await post('/reset');
function audio(name,text) {
 const txt=path.join(output,name+'.txt'),aiff=path.join(output,name+'.aiff'),wav=path.join(output,name+'.wav');
 fs.writeFileSync(txt,text+'\n');
 for(const [command,args] of [['/usr/bin/say',['-o',aiff,'-f',txt]],['ffmpeg',['-nostdin','-v','error','-i',aiff,'-af','apad=pad_dur=1','-ar','16000','-ac','1',wav]]]){
   const result=spawnSync(command,args);assert.equal(result.status,0,result.stderr?.toString());
 }
 const raw=spawnSync('ffmpeg',['-nostdin','-v','error','-i',wav,'-f','f32le','pipe:1']);assert.equal(raw.status,0);
 const pcm=new Float32Array(raw.stdout.buffer.slice(raw.stdout.byteOffset,raw.stdout.byteOffset+raw.stdout.byteLength));
 return {bytes:fs.readFileSync(wav),pcm};
}
const fixtures={request:audio('request','Bring me the screwdriver, please.'),negative:audio('negative',"Don't stop."),stop:audio('stop','Stop.')};
const element=()=>({textContent:'',hidden:false,disabled:false,setAttribute(){}});
let mic,taskId=null,allowInterrupt=false,interruptClip=0,stops=0,negations=0,captureReleases=0;
let currentFixture,stopStarted=null,voiceStopPosted=null;
let stopLastSpeech=null;
const recognized=[],trace=[],errors=[];
class Recorder {
 static isTypeSupported(){return true;}
 constructor(){this.mimeType='audio/wav';this.state='inactive';this.fixture=currentFixture;}
 start(){this.state='recording';}
 stop(){this.state='inactive';this.ondataavailable({data:new Blob([this.fixture.bytes])});this.onstop();}
}
mic=new MicrophoneInput({button:element(),cancel:element(),note:element(),heard:element(),
 mediaDevices:{getUserMedia:async()=>{currentFixture=mic.kind==='request'?fixtures.request:interruptClip===0?fixtures.negative:fixtures.stop;return {getTracks:()=>[{stop:()=>captureReleases++}]};}},
 Recorder,
 fetchAudio:async(route,options)=>{
  const result=await fetch(base+route,options);
  if(result.ok){const r=await result.clone().json();recognized.push(r);if(mic.kind==='interrupt'&&interruptClip===0){assert.match(r.text.toLowerCase(),/don.t stop/);negations++;interruptClip++;assert.ok((await state()).busy,'Negation stopped motion');}}
  return result;
 },
 monitor:(stream,detector,onPause)=>{
  const fixture=currentFixture;let offset=0;
  const timer=setInterval(()=>{
   if(mic.kind==='interrupt'&&!allowInterrupt){detector.sample(0,performance.now());return;}
   if(mic.kind==='interrupt'&&interruptClip>0&&stopStarted===null)stopStarted=performance.now();
   const values=fixture.pcm.subarray(offset,offset+640);offset+=640;
   const rms=values.length?Math.sqrt(values.reduce((n,v)=>n+v*v,0)/values.length):0;
   if(mic.kind==='interrupt'&&interruptClip>0&&rms>=detector.threshold)stopLastSpeech=performance.now();
   if(detector.sample(rms,performance.now()))onPause();
  },40);
  return ()=>clearInterval(timer);
 },
 stopSpeech:()=>post('/speech-stop'),
 onText:async text=>{assert.equal(taskId,null,'Unexpected second motion request');taskId=(await post('/chat',{message:text})).task_id;},
 onStop:async()=>{const before=await state();assert.ok(before.busy,'Stop must interrupt active work');voiceStopPosted=performance.now();await post('/stop');stops++;},
 onError:text=>{if(text)errors.push(text);},
});
mic.setReady(true);await mic.start();
const deadline=performance.now()+90000;
let final;
while(performance.now()<deadline){
 const s=await state();trace.push({phase:s.phase,busy:s.busy,joints:s.robot_joints});
 if(s.phase==='Lifting tool')allowInterrupt=true;
 mic.setWorking(s.busy);mic.setReady(s.speech_input.status==='ready'&&!s.speech_input.busy);
 const task=s.tasks.find(t=>t.task_id===taskId);
 if(task?.status==='cancelled'&&!s.busy&&s.phase==='Stopped'){final=s;break;}
 await sleep(100);
}
mic.close();assert.ok(final,'Voice Stop failed to cancel the real task');
assert.equal(stops,1);assert.equal(negations,1);assert.equal(errors.length,0,errors.join('\n'));
assert.equal(final.phase,'Stopped');assert.equal(final.last_result.physical_success,false);
assert.equal(final.last_result.status,'cancelled');
await sleep(500);const settled=(await state()).robot_joints;await sleep(600);const later=await state();
assert.equal(later.tasks.find(t=>t.task_id===taskId).status,'cancelled');
const drift=Math.max(...settled.map((v,i)=>Math.abs(v-later.robot_joints[i])));assert.ok(drift<.03,'Arm did not settle after Stop');
const evidence={capture:'saved native speech plus actual waveform pause detection, not live microphone',
 recognized,task_id:taskId,negative_stop_ignored:negations,stop_commands:stops,capture_releases:captureReleases,
 stop_speech_to_post_ms:Math.round(voiceStopPosted-stopStarted),settled_joint_drift_rad:drift,
 stop_end_to_post_ms:Math.round(voiceStopPosted-stopLastSpeech),
 final_result:final.last_result,phases:[...new Set(trace.map(t=>t.phase))],trace};
fs.writeFileSync(path.join(output,'verification.json'),JSON.stringify(evidence,null,2));
assert.ok(stopLastSpeech!==null&&evidence.stop_end_to_post_ms<=1000,'Spoken Stop exceeded 1 second after its last voiced sample');
console.log(`PASS: automatic request -> actual motion; "don't stop" ignored; spoken Stop cancels via shipped controller. ${evidence.stop_speech_to_post_ms} ms speech-to-stop request; ${drift.toFixed(5)} rad settled drift.`);
