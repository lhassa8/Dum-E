// The public page's message polling and LocalSpeech output, with local test telemetry.
import {LocalSpeech} from '/local-speech.mjs';

export class PhysicalSpeech {
 constructor(request,post){
  this.request=request;this.post=post;this.records=[];this.errors=[];this.count=0;this.running=false;
  this.speech=new LocalSpeech({post:async(path,body)=>{
   const record=path==='/speak'?this.records.filter(r=>r.text===body.message&&!r.api).at(-1):null;
   if(record)record.posted_ms=performance.now();
   const result=await post(path,body);if(record)record.api=result;return result;
  },onError:message=>this.errors.push(message)});
 }
 async initialize(){const state=await this.request('/api/state');this.count=state.messages.length;
  if(state.speech.backend!=='windows-sapi'||state.speech.status!=='ready')throw Error('Native Windows output is not ready.');
  this.timer=setInterval(()=>this.poll(),100);
 }
 async poll(){if(this.running)return;this.running=true;try{this.observe(await this.request('/api/state'));}
  catch(error){this.errors.push(error.message);}finally{this.running=false;}}
 observe(state){
  // A delayed poll may contain an older message list. Each case starts a new
  // observer, so reducing the count here would replay already handled replies.
  if(state.messages.length<this.count)return;
  if(state.messages.length>this.count){const replies=state.messages.slice(this.count).filter(m=>m.role==='assistant');this.count=state.messages.length;
   if(replies.length)this.say(replies.at(-1).content,'reply');}
 }
 say(text,kind='reply',completedMs=null){
  const record={text,kind,requested_ms:performance.now(),completed_ms:completedMs,posted_ms:null,playing_ms:null,ended_ms:null,cancelled_ms:null,api:null};
  this.records.push(record);
  this.speech.speak(text,{onStart:()=>{
   for(const prior of this.records)if(prior!==record&&prior.playing_ms!==null&&prior.ended_ms===null&&prior.cancelled_ms===null)prior.cancelled_ms=performance.now();
   record.playing_ms=performance.now();record.playing_position_s=this.speech.audio?.currentTime;
   record.media_duration_s=this.speech.audio?.duration;
  },onEnd:()=>{record.ended_ms=performance.now();record.ended_position_s=this.speech.audio?.currentTime;}})
   .then(()=>{if(!record.api&&record.playing_ms===null&&record.cancelled_ms===null){record.cancelled_ms=performance.now();record.cancellation_reason='Superseded before speech API dispatch';}})
   .catch(error=>{record.error=error.message;this.errors.push(error.message);});
 }
 endpoint({completedAtMs}){this.say('Let me check.','acknowledgment',completedAtMs);}
 stop(){
  const now=performance.now();for(const record of this.records)if(record.ended_ms===null&&record.cancelled_ms===null)record.cancelled_ms=now;
  this.speech.stop();
 }
 async stopSignal(){this.stop();await this.post('/speech-stop');}
 async settled(limit=15000){
  const deadline=performance.now()+limit;
  await this.poll();
  while(performance.now()<deadline){
   if(this.errors.length)throw Error(this.errors.join('; '));
   if(this.records.every(r=>r.ended_ms!==null||r.cancelled_ms!==null)){await new Promise(r=>setTimeout(r,150));await this.poll();
    if(this.records.every(r=>r.ended_ms!==null||r.cancelled_ms!==null))return;}
   await new Promise(r=>setTimeout(r,20));
  }
  throw Error('Spoken confirmation did not finish.');
 }
 close(){clearInterval(this.timer);this.stop();}
}
