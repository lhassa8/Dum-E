// Unit probes for the shipped recorder state machine; not a microphone/browser test.
import assert from 'node:assert/strict';
import {MicrophoneInput} from '../src/physical_ai_lab/dume/web/voice-input.mjs';

const element=()=>({textContent:'',hidden:false,disabled:false,setAttribute(){}});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function setup({permission,fetchAudio,useDefaultFetch=false}={}) {
  let releases=0,submitted=[];
  const stream={getTracks:()=>[{stop:()=>releases++}]};
  class Recorder {
    static isTypeSupported(){return true;}
    constructor(){this.mimeType='audio/webm';this.state='inactive';}
    start(){this.state='recording';}
    stop(){this.state='inactive';this.ondataavailable({data:new Blob(['recording'])});this.onstop();}
  }
  const ui={button:element(),cancel:element(),note:element(),heard:element()};
  const mic=new MicrophoneInput({...ui,mediaDevices:{getUserMedia:permission||(()=>Promise.resolve(stream))},
    Recorder,fetchAudio:useDefaultFetch?undefined:fetchAudio||(()=>Promise.resolve({ok:true,json:async()=>({text:'Bring me the screwdriver.'})})),
    stopSpeech:async()=>{},onText:async text=>submitted.push(text),onError:message=>ui.error=message});
  mic.setReady(true);
  return {mic,ui,stream,submitted,releases:()=>releases};
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
