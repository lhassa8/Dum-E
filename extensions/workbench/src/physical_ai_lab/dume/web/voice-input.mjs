// Click-to-talk capture. Cancel/Stop invalidates pending permission and ASR results.
export class MicrophoneInput {
  constructor({button, cancel, note, heard, onText, onError, stopSpeech,
               mediaDevices=navigator.mediaDevices, Recorder=globalThis.MediaRecorder,
               fetchAudio=(...args)=>globalThis.fetch(...args)}) {
    Object.assign(this, {button,cancel,note,heard,onText,onError,stopSpeech,
                        mediaDevices,Recorder,fetchAudio});
    this.mode='idle'; this.ready=false; this.generation=0;
    button.onclick=()=>this.mode==='recording'?this.finish():this.start();
    cancel.onclick=()=>this.abort();
    this.paint();
  }
  setReady(ready, message='Click Speak, say your request, then Finish.') {
    this.ready=ready;
    if(this.mode==='idle')this.note.textContent=message;
    this.paint();
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
    clearTimeout(this.timer);
    this.stream?.getTracks().forEach(track=>track.stop());
    this.stream=null;
  }
  abort() {
    this.generation++;
    this.abortRequest?.abort();
    if(this.recorder?.state==='recording')this.recorder.stop();
    this.release(); this.mode='idle';
    this.note.textContent='Recording cancelled. Click Speak to try again.';
    this.paint();
  }
  async start() {
    if(!this.ready||this.mode!=='idle')return;
    if(!this.mediaDevices?.getUserMedia||!this.Recorder) {
      this.onError('Microphone capture is unavailable in this browser. Open this same address in Chrome or Safari.');
      return;
    }
    const generation=++this.generation;
    this.mode='requesting';this.note.textContent='Allow microphone access when prompted…';
    this.heard.textContent='';this.paint();
    try {
      await this.stopSpeech();
      if(generation!==this.generation)return;
      const stream=await this.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
      if(generation!==this.generation){stream.getTracks().forEach(t=>t.stop());return;}
      this.stream=stream;
      const mime=['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus']
        .find(type=>this.Recorder.isTypeSupported(type));
      this.recorder=new this.Recorder(stream,mime?{mimeType:mime}:{});
      const chunks=[];
      this.recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
      this.recorder.onerror=()=>{if(generation===this.generation){this.abort();this.onError('Recording failed. Please try again.');}};
      this.recorder.onstop=()=>this.recognize(new Blob(chunks,{type:this.recorder.mimeType||'audio/webm'}),generation);
      this.recorder.start(); this.mode='recording';
      this.note.textContent='Listening… say “bring me the screwdriver,” then click Finish.';
      this.paint();this.timer=setTimeout(()=>this.finish(),12000);
    } catch(error) {
      if(generation!==this.generation)return;
      this.release();this.mode='idle';this.paint();
      const message=error.name==='NotAllowedError'?
        'Microphone access was denied. Allow it for this page in your browser settings, or keep typing.':
        error.name==='NotFoundError'?'No microphone found. Connect or enable a microphone, or keep typing.':
        'Could not start the microphone: '+error.message;
      this.note.textContent=message;this.onError(message);
    }
  }
  finish() {
    if(this.mode!=='recording')return;
    this.mode='transcribing';this.note.textContent='Recognizing your words locally…';
    this.paint();this.recorder.stop();this.release();
  }
  async recognize(blob,generation) {
    if(generation!==this.generation)return;
    try {
      this.abortRequest=new AbortController();
      const response=await this.fetchAudio('/transcribe',{
        method:'POST',headers:{'Content-Type':blob.type},body:blob,
        signal:this.abortRequest.signal,
      });
      const result=await response.json();
      if(generation!==this.generation)return;
      if(!response.ok)throw Error(result.detail||'Transcription failed.');
      const text=result.text?.trim();
      if(!text)throw Error('I didn’t hear a request. Please try again.');
      this.mode='idle';this.paint();this.heard.textContent='Heard: “'+text+'”';
      this.note.textContent='Request recognized. Sending to Dum-E…';
      await this.onText(text);
    } catch(error) {
      if(generation!==this.generation||error.name==='AbortError')return;
      this.mode='idle';this.paint();this.note.textContent=error.message;this.onError(error.message);
    }
  }
}
