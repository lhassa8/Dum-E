// Race checks for the test observer; no microphone, speaker or simulator access.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const speechURL=new URL('../src/physical_ai_lab/dume/web/local-speech.mjs',import.meta.url).href;
const source=(await readFile(new URL('../integrations/speech-vad/physical-speech.mjs',import.meta.url),'utf8'))
 .replace("'/local-speech.mjs'",JSON.stringify(speechURL));
const {PhysicalSpeech}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const tick=()=>new Promise(resolve=>setImmediate(resolve));let player,generation=0;
globalThis.Audio=class{constructor(){player=this;this.currentTime=0;this.duration=1.64;}pause(){}async play(){this.onplaying();}};
globalThis.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
globalThis.speechSynthesis={cancel(){},getVoices(){return [{localService:true,lang:'en-US'}];},speak(utterance){utterance.onstart();utterance.onend();}};
const post=async(path,body)=>path==='/speak'?{browser:true,generation:++generation,...(body.message==='Let me check.'?{audio:'/acknowledgment.wav'}:{})}:{};
const observer=new PhysicalSpeech(async()=>({messages:[]}),post);
observer.endpoint({completedAtMs:performance.now()});await tick();
observer.say('Older queued reply');observer.say('Latest queued reply');await tick();
player.currentTime=1.64;player.onended();await tick();
assert.equal(observer.records[1].api,null);
assert.equal(observer.records[1].cancellation_reason,'Superseded before speech API dispatch');
assert.ok(observer.records[2].ended_ms!==null);await observer.settled();observer.close();
const stale=new PhysicalSpeech(async()=>({messages:[]}),post);
const messages=[{role:'user',content:'Question'},{role:'assistant',content:'Answer'}];
stale.observe({messages});stale.observe({messages:messages.slice(0,1)});stale.observe({messages});
await tick();assert.equal(stale.records.length,1);stale.close();
console.log('PASS: queued supersession settles; stale shorter polls never replay an old reply.');
