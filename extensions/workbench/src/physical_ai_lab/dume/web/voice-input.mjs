// Local pause detection and bounded motion-only listening. ASR remains on the Mac.
export function isStopRequest(text) {
  const words=text.toLowerCase().replace(/[^a-z\s]/g,' ').replace(/\s+/g,' ').trim();
  return /^(?:(?:please|dum e|dume|dummy|can you|could you) )?(?:stop|halt|cancel)(?: (?:moving|the arm|everything))?(?: (?:please|now))?$/.test(words);
}

export class PauseDetector {
  constructor({pauseMs=900, minimumSpeechMs=120, threshold=.008}={}) {
    Object.assign(this,{pauseMs,minimumSpeechMs,threshold});
    this.lastTime=null;this.speechMs=0;this.lastSpeech=null;
  }
  sample(rms,now) {
    const delta=this.lastTime===null?0:Math.min(100,Math.max(0,now-this.lastTime));
    this.lastTime=now;
    if(rms>=this.threshold){this.speechMs+=delta;this.lastSpeech=now;}
    return this.speechMs>=this.minimumSpeechMs && now-this.lastSpeech>=this.pauseMs;
  }
  get heardSpeech(){return this.speechMs>=this.minimumSpeechMs;}
  sampleProbability(probability,now){
    if(!Number.isFinite(probability))return false;
    return this.sample(probability>=.3?this.threshold:0,now);
  }
}

export function monitorMicrophone(stream,detector,onPause) {
  const Audio=globalThis.AudioContext||globalThis.webkitAudioContext;
  if(!Audio)throw Error('Automatic speech completion is unavailable in this browser.');
  const context=new Audio();
  const source=context.createMediaStreamSource(stream),analyser=context.createAnalyser();
  analyser.fftSize=1024;source.connect(analyser);
  const samples=new Float32Array(analyser.fftSize);
  context.resume().catch(()=>{});
  const timer=setInterval(()=>{
    analyser.getFloatTimeDomainData(samples);
    const rms=Math.sqrt(samples.reduce((sum,v)=>sum+v*v,0)/samples.length);
    if(detector.sample(rms,performance.now()))onPause();
  },40);
  return ()=>{clearInterval(timer);source.disconnect();context.close().catch(()=>{});};
}

export class MicrophoneInput {
  constructor({button,cancel,note,heard,onText,onStop,onDuringWork,onError,stopSpeech,
               mediaDevices=navigator.mediaDevices,Recorder=globalThis.MediaRecorder,
               fetchAudio=(...args)=>globalThis.fetch(...args),monitor=monitorMicrophone}) {
    Object.assign(this,{button,cancel,note,heard,onText,onStop,onDuringWork,onError,stopSpeech,
                       mediaDevices,Recorder,fetchAudio,monitor});
    this.mode='idle';this.ready=false;this.generation=0;this.working=false;
    this.interruptEnabled=true;this.held=false;this.closed=false;this.kind='request';
    button.onclick=()=>this.mode==='recording'?this.finish():this.start();
    cancel.onclick=()=>this.abort();this.paint();
  }
  setReady(ready,message='Click Speak and talk. I’ll finish when you pause.') {
    this.ready=ready;
    if(this.mode==='idle')this.note.textContent=message;
    this.paint();this.maybeListen();
  }
  setWorking(working) {
    const ended=this.working&&!working;this.working=working;
    if(ended){
      this.held=false;
      if(this.kind==='interrupt'&&this.mode!=='idle') {
        if(this.onDuringWork&&this.mode==='recording'&&this.detector?.heardSpeech)this.finish();
        else if(!(this.onDuringWork&&this.mode==='transcribing'))this.abort(false);
      }
    }
    this.maybeListen();
  }
  setInterruptEnabled(enabled) {
    this.interruptEnabled=enabled;
    if(!enabled&&this.kind==='interrupt'&&this.mode!=='idle')this.abort(false);
    if(enabled)this.held=false;
    this.maybeListen();
  }
  maybeListen() {
    if(this.working&&this.interruptEnabled&&this.ready&&!this.held&&!this.closed&&this.mode==='idle')
      this.start('interrupt');
  }
  paint() {
    this.button.textContent=this.mode==='recording'?'Finish':
      this.mode==='transcribing'?'Transcribing…':'🎙 Speak';
    this.button.setAttribute('aria-label',this.mode==='recording'?'Finish recording':'Speak a request');
    this.button.setAttribute('aria-pressed',String(this.mode==='recording'));
    this.button.disabled=this.mode==='idle'?!this.ready:this.mode!=='recording';
    this.cancel.hidden=this.mode==='idle';
  }
  release() {
    this.monitorRequest?.abort();
    clearTimeout(this.timer);this.stopMonitor?.();this.stopMonitor=null;
    this.stream?.getTracks().forEach(track=>track.stop());this.stream=null;
  }
  abort(hold=true) {
    this.generation++;if(hold&&this.working)this.held=true;
    this.abortRequest?.abort();
    if(this.recorder?.state==='recording')this.recorder.stop();
    this.release();this.mode='idle';
    this.note.textContent=this.held?'Voice stop paused for this movement. Click Speak to listen again.':
      'Recording cancelled. Click Speak to try again.';
    this.paint();
  }
  close(){this.closed=true;this.abort();}
  async start(kind=this.working?'interrupt':'request') {
    if(!this.ready||this.mode!=='idle'||this.closed)return;
    if(!this.mediaDevices?.getUserMedia||!this.Recorder) {
      this.held=true;
      this.onError('Microphone capture is unavailable. Open this same address in Chrome or Safari.');return;
    }
    this.held=false;this.kind=kind;
    const generation=++this.generation;
    this.mode='requesting';this.note.textContent='Opening microphone…';this.paint();
    if(kind==='request'){this.heard.textContent='';this.onError('');}
    try {
      if(kind==='request')await this.stopSpeech();
      if(generation!==this.generation)return;
      const stream=await this.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
      if(generation!==this.generation){stream.getTracks().forEach(t=>t.stop());return;}
      this.stream=stream;
      const mime=['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus']
        .find(type=>this.Recorder.isTypeSupported(type));
      const recorder=this.recorder=new this.Recorder(stream,mime?{mimeType:mime}:{});
      const chunks=[];
      recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
      recorder.onerror=()=>{if(generation===this.generation){this.abort();this.onError('Recording failed. Please try again.');}};
      recorder.onstop=()=>this.recognize(new Blob(chunks,{type:recorder.mimeType||'audio/webm'}),generation,kind);
      this.detector=new PauseDetector({pauseMs:kind==='interrupt'?350:900});
      recorder.start();this.mode='recording';
      this.monitorRequest=new AbortController();
      this.timer=setTimeout(()=>{
        if(generation!==this.generation)return;
        this.abort();this.onError('Speech detection did not start. Click Speak to try again.');
      },5000);
      const stopMonitor=await this.monitor(stream,this.detector,()=>this.finish(),this.monitorRequest.signal,error=>{
        if(generation!==this.generation)return;
        this.abort();this.onError('Speech detection failed: '+error.message);
      });
      if(generation!==this.generation||this.mode!=='recording'){stopMonitor();return;}
      clearTimeout(this.timer);
      this.stopMonitor=stopMonitor;
      this.note.textContent=kind==='interrupt'?(this.onDuringWork?'Listening while I work. Ask a question, change tools, or say “stop”…':'Listening for “stop” while the arm works…'):
        'Listening… speak normally. I’ll finish when you pause.';
      this.paint();
      this.timer=setTimeout(()=>{
        if(this.detector.heardSpeech)this.finish();
        else {this.abort(false);this.note.textContent=kind==='interrupt'?'Listening for “stop”…':'No speech heard. Click Speak to try again.';
          if(kind==='request')this.onError('No speech heard. Check your microphone and try again.');}
      },12000);
    } catch(error) {
      if(generation!==this.generation)return;
      this.held=true;this.abort(false);
      const message=error.name==='NotAllowedError'?
        'Microphone access was denied. Allow it for this page, or keep typing.':
        error.name==='NotFoundError'?'No microphone found. Enable a microphone, or keep typing.':
        'Could not start the microphone: '+error.message;
      this.note.textContent=message;this.onError(message);
    }
  }
  finish() {
    if(this.mode!=='recording')return;
    this.mode='transcribing';this.note.textContent='Recognizing your words locally…';
    this.paint();this.recorder.stop();this.release();
  }
  dispatchDuringWork(callback,text) {
    // Waiting for a model reply must not hold the recorder in transcribing mode.
    // The server invalidates pending dialogue on Stop; resume listening now.
    Promise.resolve().then(()=>callback.call(this,text)).catch(error=>{
      if(!this.closed)this.onError(error.message||String(error));
    });
  }
  async recognize(blob,generation,kind) {
    if(generation!==this.generation)return;
    try {
      this.abortRequest=new AbortController();
      const response=await this.fetchAudio('/transcribe',{
        method:'POST',headers:{'Content-Type':blob.type,'X-Dume-Voice-Mode':kind},body:blob,
        signal:this.abortRequest.signal,
      });
      const result=await response.json();
      if(generation!==this.generation)return;
      if(!response.ok)throw Error(result.detail||'Transcription failed.');
      const text=result.text?.trim();if(!text)throw Error('I didn’t hear a request. Please try again.');
      if(result.likely_echo&&!isStopRequest(text)) {
        this.note.textContent='Listening while working…';this.mode='idle';this.paint();return;
      }
      if(kind==='request'||isStopRequest(text)||this.onDuringWork)this.heard.textContent='Heard: “'+text+'”';
      if(isStopRequest(text)) {
        this.held=true;this.note.textContent='Stopping the arm…';
        await this.onStop();
      } else if(kind==='request') {
        this.note.textContent='Request recognized. Sending to Dum-E…';
        if(this.working)this.dispatchDuringWork(this.onText,text);else await this.onText(text);
      } else if(this.onDuringWork) {
        this.note.textContent='Request recognized. Responding while working…';
        this.dispatchDuringWork(this.onDuringWork,text);
      } else {this.note.textContent='Only “stop” is accepted while the arm is working.';}
      if(generation===this.generation){this.mode='idle';this.paint();this.maybeListen();}
    } catch(error) {
      if(generation!==this.generation||error.name==='AbortError')return;
      this.mode='idle';this.paint();this.note.textContent=error.message;
      if(kind==='request'||this.onDuringWork)this.onError(error.message);
    }
  }
}
