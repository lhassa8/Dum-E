// Real saved speech, shipped capture controller, pending local inference and MuJoCo Stop.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {MicrophoneInput} from '../src/physical_ai_lab/dume/web/voice-input.mjs';

const output=process.argv[2];assert.ok(output,'Usage: node scripts/verify_pending_voice_stop.mjs OUTPUT');
fs.mkdirSync(output,{recursive:false});
const base='http://127.0.0.1:8766';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function request(route,options={}) {
  const r=await fetch(base+route,options),data=await r.json();
  assert.ok(r.ok,JSON.stringify(data));return data;
}
const post=(route,data={})=>request(route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
async function nativeState(){
  const r=await fetch('http://127.0.0.1:8765/state');assert.ok(r.ok);const s=await r.json();
  assert.ok(Array.isArray(s.robot_joints)&&s.robot_joints.length===7,'Native robot_joints contract missing');return s;
}
async function wait(predicate,limit=90000) {
  const end=performance.now()+limit;
  while(performance.now()<end){const s=await request('/state');if(predicate(s))return s;await sleep(40);}
  throw Error('State wait timed out');
}
function fixture(name,text) {
  const aiff=path.join(output,name+'.aiff'),wav=path.join(output,name+'.wav');
  for(const [cmd,args] of [['/usr/bin/say',['-o',aiff,text]],['ffmpeg',['-nostdin','-v','error','-i',aiff,'-af','apad=pad_dur=1','-ar','16000','-ac','1',wav]]]){
    const r=spawnSync(cmd,args);assert.equal(r.status,0,r.stderr?.toString());
  }
  const raw=spawnSync('ffmpeg',['-nostdin','-v','error','-i',wav,'-f','f32le','pipe:1']);assert.equal(raw.status,0);
  return {bytes:fs.readFileSync(wav),pcm:new Float32Array(raw.stdout.buffer.slice(raw.stdout.byteOffset,raw.stdout.byteOffset+raw.stdout.byteLength))};
}
const clips=[fixture('question','Explain your limitations.'),fixture('stop','Stop.')];
await wait(s=>s.model_status==='ready'&&s.speech_input.status==='ready'&&!s.busy);
await nativeState(); // Validate the physical-state contract before any test movement.
await post('/reset');await wait(s=>s.phase==='Ready'&&s.last_intent===null);
const tid=(await post('/interact',{message:'Bring me the screwdriver.'})).task_id;
await wait(s=>s.phase==='Lifting tool'&&s.objects.screwdriver[2]>.13);
const element=()=>({textContent:'',hidden:false,disabled:false,setAttribute(){}});
let nextClip=0,activeClip,lastStopSpeech,stopPosted,questionStarted,questionResolved,questionResult;
let dialoguePromise,stops=0,captures=0,releases=0;
const recognized=[],errors=[];
class Recorder {
  static isTypeSupported(){return true;}
  constructor(){this.mimeType='audio/wav';this.state='inactive';this.fixture=activeClip;}
  start(){this.state='recording';}
  stop(){this.state='inactive';this.ondataavailable({data:new Blob([this.fixture.bytes])});this.onstop();}
}
const mic=new MicrophoneInput({button:element(),cancel:element(),note:element(),heard:element(),Recorder,
  mediaDevices:{getUserMedia:async()=>{assert.ok(nextClip<2,'Unexpected third capture');activeClip=clips[nextClip++];captures++;return {getTracks:()=>[{stop:()=>releases++}]};}},
  monitor:(stream,detector,onPause)=>{
    const clip=activeClip,isStop=clip===clips[1];let offset=0;
    const timer=setInterval(()=>{
      const values=clip.pcm.subarray(offset,offset+640);offset+=640;
      const rms=values.length?Math.sqrt(values.reduce((n,v)=>n+v*v,0)/values.length):0;
      const now=performance.now();if(isStop&&rms>=detector.threshold)lastStopSpeech=now;
      if(detector.sample(rms,now))onPause();
    },40);
    return ()=>clearInterval(timer);
  },
  fetchAudio:async(route,options)=>{const r=await fetch(base+route,options);if(r.ok)recognized.push(await r.clone().json());return r;},
  stopSpeech:()=>post('/speech-stop'),
  onText:()=>{throw Error('Unexpected idle request capture');},
  onDuringWork:text=>{
    assert.equal(dialoguePromise,undefined);questionStarted=performance.now();
    dialoguePromise=post('/interact',{message:text,source:'voice'}).then(r=>{questionResolved=performance.now();questionResult=r;return r;});
    return dialoguePromise;
  },
  onStop:async()=>{stopPosted=performance.now();stops++;await post('/stop');},
  onError:e=>{if(e)errors.push(e);},
});
mic.setReady(true);mic.setWorking(true);
let settled;
try {
  const deadline=performance.now()+20000;
  while(performance.now()<deadline&&!stops&&!errors.length){mic.setReady(true);await sleep(40);}
  assert.equal(stops,1,JSON.stringify(errors));assert.ok(!errors.length,JSON.stringify(errors));
  assert.ok(questionStarted&&stopPosted&&!questionResolved,'Reply resolved before Stop; pending-reply criterion not exercised');
  settled=await wait(s=>!s.busy&&s.phase==='Stopped');mic.setWorking(false);mic.close();
  await dialoguePromise;
  assert.equal(questionResult.mode,'superseded');assert.equal(questionResult.accepted,false);
  assert.equal(settled.tasks.find(t=>t.task_id===tid).status,'cancelled');
  const physical=await nativeState(),joints=physical.robot_joints;
  await sleep(600);const later=await request('/state');
  const laterPhysical=await nativeState();
  const drift=Math.max(...joints.map((q,i)=>Math.abs(q-laterPhysical.robot_joints[i])));
  assert.ok(drift<.02);assert.equal(laterPhysical.gripper_command,physical.gripper_command);
  assert.ok(!later.tasks.some(t=>t.status==='pending'||t.status==='running'));
  const evidence={scope:'Saved synthetic speech, real-time shipped pause controller, local ASR/inference and actual MuJoCo; not live room audio.',
    task_id:tid,captures,releases,recognized,errors,question_result:questionResult,
    question_to_stop_ms:stopPosted-questionStarted,end_of_stop_to_post_ms:stopPosted-lastStopSpeech,
    pending_reply_resolved_after_stop_ms:questionResolved-stopPosted,settled_joint_drift_rad:drift,
    retained_gripper_command:laterPhysical.gripper_command,stopped_task_status:later.tasks.find(t=>t.task_id===tid).status};
  fs.writeFileSync(path.join(output,'verification.json'),JSON.stringify(evidence,null,2));console.log('PASS',JSON.stringify(evidence,null,2));
} catch(error) {
  fs.writeFileSync(path.join(output,'failure.json'),JSON.stringify({error:String(error),recognized,questionResult,questionStarted,questionResolved,stopPosted,errors},null,2));
  throw error;
} finally {mic.close();await post('/stop');}
