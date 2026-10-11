// Unit probes for the shipped recorder state machine; not a microphone/browser test.
import assert from 'node:assert/strict';
import {MicrophoneInput,PauseDetector,isStopRequest} from '../src/physical_ai_lab/dume/web/voice-input.mjs';

const element=()=>({textContent:'',hidden:false,disabled:false,setAttribute(){}});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const probes=[];
function setup({permission,fetchAudio,useDefaultFetch=false,text='Bring me the screwdriver.',monitor,converse=false,echo=false,onDuringWork}={}) {
  let releases=0,submitted=[],stops=0,paused=null;
  const stream={getTracks:()=>[{stop:()=>releases++}]};
  class Recorder {
    static isTypeSupported(){return true;}
    constructor(){this.mimeType='audio/webm';this.state='inactive';}
    start(){this.state='recording';}
    stop(){this.state='inactive';this.ondataavailable({data:new Blob(['recording'])});this.onstop();}
  }
  const ui={button:element(),cancel:element(),note:element(),heard:element()};
  const mic=new MicrophoneInput({...ui,mediaDevices:{getUserMedia:permission||(()=>Promise.resolve(stream))},
    Recorder,fetchAudio:useDefaultFetch?undefined:fetchAudio||(()=>Promise.resolve({ok:true,json:async()=>({text,likely_echo:echo})})),
    onDuringWork:onDuringWork||(converse?async text=>submitted.push(text):undefined),
    monitor:monitor||((stream,detector,onPause)=>{paused=onPause;return ()=>{};}),onStop:async()=>stops++,stopSpeech:async()=>{},onText:async text=>submitted.push(text),onError:message=>ui.error=message});
  mic.setReady(true);
  probes.push(mic);
  return {mic,ui,stream,submitted,releases:()=>releases,stops:()=>stops,pause:()=>paused()};
}

const happy=setup();await happy.mic.start();assert.equal(happy.mic.mode,'recording');
happy.mic.finish();await tick();assert.deepEqual(happy.submitted,['Bring me the screwdriver.']);
assert.equal(happy.releases(),1);assert.equal(happy.mic.mode,'idle');

// Browser fetch is a Window method: exercise the actual default, not only injected arrows.
const originalFetch=globalThis.fetch;
try {
  globalThis.fetch=function() {
    assert.ok(this===globalThis,'Default fetch must retain its browser receiver');
    return Promise.resolve({ok:true,json:async()=>({text:'Bring me the screwdriver.'})});
  };
  const browserFetch=setup({useDefaultFetch:true});
  await browserFetch.mic.start();browserFetch.mic.finish();await tick();
  assert.deepEqual(browserFetch.submitted,['Bring me the screwdriver.'],browserFetch.ui.error);
} finally {globalThis.fetch=originalFetch;}

let grant;const pending=setup({permission:()=>new Promise(resolve=>grant=resolve)});
const starting=pending.mic.start();await tick();pending.mic.abort();grant(pending.stream);await starting;
assert.equal(pending.releases(),1);assert.equal(pending.mic.mode,'idle');assert.equal(pending.submitted.length,0);

let resolveAudio;const late=setup({fetchAudio:()=>new Promise(resolve=>resolveAudio=resolve)});
await late.mic.start();late.mic.finish();late.mic.abort();
resolveAudio({ok:true,json:async()=>({text:'Bring me the screwdriver.'})});await tick();
assert.equal(late.submitted.length,0);assert.equal(late.releases(),1);

const denied=setup({permission:async()=>{throw Object.assign(Error('denied'),{name:'NotAllowedError'});}});
await denied.mic.start();assert.match(denied.ui.error,/denied/);assert.equal(denied.mic.mode,'idle');
const failed=setup({fetchAudio:async()=>({ok:false,json:async()=>({detail:'No speech heard'})})});
await failed.mic.start();failed.mic.finish();await tick();
assert.equal(failed.submitted.length,0);assert.equal(failed.ui.error,'No speech heard');
console.log('PASS: recognized text, default browser fetch receiver, track release, pending permission cancellation, late ASR cancellation, denied mic, no-speech errors.');

// Energy traces: quiet alone, short pauses and genuinely completed utterances.
const gate=new PauseDetector();
for(let t=0;t<=1500;t+=40)assert.equal(gate.sample(0,t),false);
for(let t=1540;t<=1940;t+=40)assert.equal(gate.sample(.03,t),false);
assert.equal(gate.sample(0,2500),false);assert.equal(gate.sample(0,2840),true);
const fast=new PauseDetector({pauseMs:350});
for(let t=0;t<=200;t+=40)assert.equal(fast.sample(.03,t),false);
assert.equal(fast.sample(0,520),false);assert.equal(fast.sample(0,560),true);
for(const text of ['Stop!','Please stop.','Dum-E stop','stop now','cancel'])assert.ok(isStopRequest(text));
for(const text of ["don't stop",'do not stop','when will you stop','bring me a tool','stopwatch'])assert.equal(isStopRequest(text),false);
const automatic=setup();await automatic.mic.start();automatic.pause();await tick();
assert.equal(automatic.submitted.length,1);assert.equal(automatic.releases(),1);
const interrupt=setup({text:'Stop!'});interrupt.mic.setWorking(true);await tick();
assert.equal(interrupt.mic.kind,'interrupt');assert.equal(interrupt.mic.mode,'recording');
interrupt.pause();await tick();assert.equal(interrupt.stops(),1);assert.equal(interrupt.submitted.length,0);
interrupt.mic.setReady(true);await tick();assert.equal(interrupt.mic.mode,'idle');
const unrelated=setup({text:'Bring me the wrench.'});unrelated.mic.setWorking(true);await tick();
unrelated.pause();await tick();assert.equal(unrelated.submitted.length,0);assert.equal(unrelated.stops(),0);
unrelated.mic.setReady(true);await tick();assert.equal(unrelated.mic.mode,'recording');
unrelated.mic.abort();unrelated.mic.setReady(true);await tick();assert.equal(unrelated.mic.mode,'idle');
const lateStop=setup({fetchAudio:()=>new Promise(resolve=>resolveAudio=resolve)});
lateStop.mic.setWorking(true);await tick();lateStop.pause();lateStop.mic.abort();
resolveAudio({ok:true,json:async()=>({text:'Stop!'})});await tick();assert.equal(lateStop.stops(),0);
const switched=setup();switched.mic.setWorking(true);await tick();switched.mic.setInterruptEnabled(false);
assert.equal(switched.mic.mode,'idle');assert.equal(switched.releases(),1);
const ended=setup();ended.mic.setWorking(true);await tick();ended.mic.setWorking(false);
assert.equal(ended.mic.mode,'idle');assert.equal(ended.releases(),1);
console.log('PASS: pause thresholds, automatic Finish, strict Stop, motion-only rearming, non-stop suppression, cancel, disable and task-end cleanup.');

const conversation=setup({text:'What are you doing?',converse:true});
conversation.mic.setWorking(true);await tick();conversation.pause();await tick();
assert.deepEqual(conversation.submitted,['What are you doing?']);
assert.equal(conversation.releases(),1);assert.equal(conversation.stops(),0);
const spokenEcho=setup({text:"I'll bring you the wrench.",converse:true,echo:true});
spokenEcho.mic.setWorking(true);await tick();spokenEcho.pause();await tick();
assert.equal(spokenEcho.submitted.length,0);
const stopThroughEcho=setup({text:'Stop!',converse:true,echo:true});
stopThroughEcho.mic.setWorking(true);await tick();stopThroughEcho.pause();await tick();
assert.equal(stopThroughEcho.stops(),1);
let lateAnswer;
const finishedSpeech=setup({converse:true,fetchAudio:()=>new Promise(r=>lateAnswer=r)});
finishedSpeech.mic.setWorking(true);await tick();finishedSpeech.pause();finishedSpeech.mic.setWorking(false);
lateAnswer({ok:true,json:async()=>({text:'Bring me the hammer.'})});await tick();
assert.deepEqual(finishedSpeech.submitted,['Bring me the hammer.']);
assert.equal(finishedSpeech.releases(),1);assert.equal(finishedSpeech.mic.mode,'idle');
console.log('PASS: opt-in conversation during movement, echo rejection with independent Stop, and pending recognition preserved when work ends.');

// Hold a conversation response indefinitely, then recognize Stop before it resolves.
let releaseDialogue,dialogueStarted=false;
const thinking=setup({text:'Tell me a joke.',onDuringWork:function(){
  assert.ok(this.working,'Deferred callback lost its receiver');
  dialogueStarted=true;return new Promise(resolve=>releaseDialogue=resolve);
}});
thinking.mic.setWorking(true);await tick();thinking.pause();await tick();
assert.ok(dialogueStarted);assert.equal(thinking.mic.mode,'recording','Reply blocks Stop listening');
thinking.mic.fetchAudio=async()=>({ok:true,json:async()=>({text:'Stop.'})});
thinking.pause();await tick();assert.equal(thinking.stops(),1);
assert.equal(thinking.mic.mode,'idle');
releaseDialogue();await tick();assert.equal(thinking.mic.mode,'idle','Late reply rearmed after Stop');
thinking.mic.close();
console.log('PASS: spoken Stop remains reachable while a conversation response is pending.');
for(const mic of probes)mic.close();
