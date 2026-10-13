import assert from 'node:assert/strict';
import {LocalSpeech} from '../src/physical_ai_lab/dume/web/local-speech.mjs';
let complete, played=[], cancelled=0;
const synthesis={cancel(){cancelled++},getVoices(){return [{lang:'en-US',localService:true}]},speak(u){played.push(u)}};
const speech=new LocalSpeech({synthesis,Utterance:class {constructor(text){this.text=text}},post:()=>new Promise(r=>complete=r)});
const pending=speech.speak('Late reply'); speech.stop(); complete({browser:true,generation:1}); await pending;
assert.equal(played.length,0,'Stop must reject an in-flight speech reply');
const current=speech.speak('Current reply'); complete({browser:true,generation:2}); await current;
assert.equal(played.length,1); assert.equal(played[0].text,'Current reply');
speech.stop(); assert.ok(cancelled>=3);
let finished=false;
const remote=new LocalSpeech({synthesis:{cancel(){},getVoices(){return [{lang:'en-US',localService:false}]}},Utterance:class{},post:async path=>{if(path.startsWith('/speech-finished/'))finished=true;return {browser:true,generation:3}}});
await assert.rejects(remote.speak('Local only'),/No installed local/); assert.ok(finished);
console.log('PASS: local voice selection, speech cancellation, and stale reply rejection.');
let starts=0,ends=0,startedReports=0;
const observed=new LocalSpeech({synthesis,Utterance:class {constructor(text){this.text=text}},
 post:async path=>{if(path.startsWith('/speech-started/'))startedReports++;return {browser:true,generation:4};}});
await observed.speak('Let me check.',{onStart:()=>starts++,onEnd:()=>ends++});
const active=played.at(-1);active.onstart();await Promise.resolve();assert.equal(starts,1);assert.equal(startedReports,1);
active.onend();assert.equal(ends,1);
await observed.speak('Cancelled acknowledgment',{onStart:()=>starts++,onEnd:()=>ends++});
const stale=played.at(-1);observed.stop();stale.onstart();stale.onend();await Promise.resolve();
assert.equal(starts,1);assert.equal(ends,1);assert.equal(startedReports,1);
console.log('PASS: playback-event timing callbacks reject cancelled/stale utterances.');
let player,resolvePlay,audioStarts=0;
class AudioProbe{constructor(url){this.url=url;player=this;}pause(){this.paused=true;}play(){return new Promise(resolve=>resolvePlay=resolve);}}
const cached=new LocalSpeech({Audio:AudioProbe,synthesis,post:async()=>({audio:'/acknowledgment.wav',generation:5})});
const awaitingAudio=cached.speak('Let me check.',{onStart:()=>audioStarts++});await Promise.resolve();
assert.equal(player.url,'/acknowledgment.wav');player.onplaying();player.onplaying();assert.equal(audioStarts,1);
cached.stop();assert.ok(player.paused);player.onplaying();resolvePlay();await awaitingAudio;assert.equal(audioStarts,1);
const rejected=new LocalSpeech({Audio:class{play(){return Promise.reject(Error('Autoplay denied'));}},synthesis,post:async()=>({audio:'/acknowledgment.wav',generation:6})});
await assert.rejects(rejected.speak('Let me check.'),/Autoplay denied/);
console.log('PASS: cached local audio start, cancellation, repeated/stale event rejection, and denied playback.');
let queuedPlayer;
class QueuedAudio{constructor(){queuedPlayer=this;}pause(){}async play(){}}
const serial=new LocalSpeech({Audio:QueuedAudio,synthesis,Utterance:class{constructor(text){this.text=text}},
 post:async(path,body)=>path==='/speak'&&body.message==='Let me check.'?{audio:'/acknowledgment.wav',generation:7}:{browser:true,generation:8}});
await serial.speak('Let me check.');const beforeReplies=played.length;
const oldReply=serial.speak('Old reply'),newReply=serial.speak('Newest reply');
await Promise.resolve();assert.equal(played.length,beforeReplies,'Reply truncated the acknowledgment');
queuedPlayer.onended();await Promise.all([oldReply,newReply]);assert.equal(played.at(-1).text,'Newest reply');
await serial.speak('Let me check.');const beforeCancelled=played.length;
const cancelledReply=serial.speak('Do not play after Stop');serial.stop();await cancelledReply;
assert.equal(played.length,beforeCancelled);
console.log('PASS: newest reply waits for acknowledgment completion; Stop cancels queued speech immediately.');
