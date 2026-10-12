// Contract checks for the pretrained-library adapter, not real model accuracy.
import assert from 'node:assert/strict';
import {createSpeechMonitor} from '../src/physical_ai_lab/dume/web/speech-detector.mjs';
import {PauseDetector} from '../src/physical_ai_lab/dume/web/voice-input.mjs';
let acquisitions=0,loads=0,releases=0,pauses=0,resets=0,processed=0,callbacks=0,resolveFrame;
let engine;
class Audio {async resume(){}async close(){}}
const monitor=createSpeechMonitor({Audio,getVAD:()=>({MicVAD:{new:async options=>{
 loads++;assert.equal(options.startOnLoad,false);
 engine={options,initializationState:'uninitialized',model:{release:async()=>releases++},
  frameProcessor:{reset:()=>resets++,process:async(frame,callback)=>{
   processed++;if(frame==='delay')await new Promise(resolve=>resolveFrame=resolve);
   callback({isSpeech:.9});
  }},
  handleFrameProcessorEvent:probs=>options.onFrameProcessed(probs),
  start:async()=>{
   acquisitions++;await (engine.initializationState==='uninitialized'?options.getStream():options.resumeStream());
   engine.initializationState='initialized';
  },pause:async()=>{pauses++;},getAudioInstances:()=>({audioContext:options.audioContext}),destroy:async()=>releases++};return engine;
}}})});
await Promise.all([monitor.prepare(),monitor.prepare()]);assert.equal(loads,1);assert.equal(acquisitions,0);
const cancelled=new AbortController();cancelled.abort();
await monitor.monitor({},new PauseDetector(),()=>callbacks++,cancelled.signal);
assert.equal(acquisitions,0);
const signal=new AbortController(),gate=new PauseDetector();
const stop=await monitor.monitor({},gate,()=>callbacks++,signal.signal);
const processing=engine.processFrame('delay');await Promise.resolve();
engine.processFrame('discard');signal.abort();stop();
const nextGate=new PauseDetector();let nextStarted=false;
const next=monitor.monitor({},nextGate,()=>callbacks++).then(cleanup=>{nextStarted=true;return cleanup;});
await Promise.resolve();assert.equal(nextStarted,false);
resolveFrame();await processing;const stopNext=await next;
assert.equal(processed,1,'Cancelled queued frame was processed');
assert.equal(gate.speechMs,0);assert.equal(nextGate.speechMs,0,'Old frame leaked into next capture');
assert.ok(resets>0);assert.equal(callbacks,0);stopNext();await monitor.close();
assert.equal(pauses,2);assert.equal(releases,1);
const preloadOnly=createSpeechMonitor({Audio,getVAD:()=>({MicVAD:{new:async options=>({options,initializationState:'uninitialized',model:{release:async()=>releases++}})}})});
await preloadOnly.prepare();await preloadOnly.close();assert.equal(releases,2);
console.log('PASS: preload never acquires audio; late/cancelled frames cannot reach next capture; cleanup waits for recurrent inference; unused model released.');
