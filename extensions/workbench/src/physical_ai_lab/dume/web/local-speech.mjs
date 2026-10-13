// Use installed local voices only. A generation prevents late network replies
// from starting sound after Stop, mute, a new utterance, or page departure.
export class LocalSpeech {
  constructor({post, onError, synthesis=globalThis.speechSynthesis, Utterance=globalThis.SpeechSynthesisUtterance, Audio=globalThis.Audio}) {
    this.post=post; this.synthesis=synthesis; this.Utterance=Utterance; this.epoch=0;
    this.onError=onError;
    this.Audio=Audio;this.audio=null;
    this.audioFinished=null;this.finishAudio=null;this.queuedReply=0;
  }
  stop() {
    this.epoch++;this.queuedReply++;this.synthesis?.cancel();
    if(this.audio){this.audio.pause();this.audio=null;}
    this.finishAudio?.();this.finishAudio=null;this.audioFinished=null;
  }
  async speak(text,{onStart,onEnd}={}) {
    if(text!=='Let me check.'&&this.audioFinished){
      const epoch=this.epoch,reply=++this.queuedReply;
      let timer;await Promise.race([this.audioFinished,new Promise(resolve=>timer=setTimeout(resolve,2000))]);clearTimeout(timer);
      if(epoch!==this.epoch||reply!==this.queuedReply)return;
    }
    this.stop(); const epoch=this.epoch;
    const result=await this.post('/speak',{message:text});
    if(epoch!==this.epoch) return;
    if(result.audio){
      if(!this.Audio)throw Error('Local audio playback is unavailable.');
      const audio=this.audio=new this.Audio(result.audio);let started=false;
      this.audioFinished=new Promise(resolve=>this.finishAudio=resolve);
      const settle=this.finishAudio;
      const finished=()=>this.post('/speech-finished/'+result.generation).catch(()=>{});
      audio.onplaying=()=>{
        if(epoch!==this.epoch||started)return;started=true;
        onStart?.();this.post('/speech-started/'+result.generation).catch(()=>{});
      };
      audio.onended=()=>{settle();if(epoch===this.epoch)onEnd?.();finished();};
      audio.onerror=()=>{settle();finished();if(epoch===this.epoch)this.onError?.('Local acknowledgment audio failed.');};
      try{await audio.play();}catch(error){settle();finished();if(epoch===this.epoch)throw error;}
      return;
    }
    if(!result.browser) return;
    const voice=this.synthesis?.getVoices().find(v=>v.localService&&v.lang.startsWith('en'));
    if(!voice) {
      await this.post('/speech-finished/'+result.generation);
      throw Error('No installed local English voice is available in this browser.');
    }
    const utterance=new this.Utterance(text); utterance.voice=voice;
    utterance.onstart=()=>{
      if(epoch!==this.epoch)return;
      onStart?.();this.post('/speech-started/'+result.generation).catch(()=>{});
    };
    utterance.onend=()=>{
      if(epoch===this.epoch)onEnd?.();
      this.post('/speech-finished/'+result.generation).catch(()=>{});
    };
    utterance.onerror=event=>{
      utterance.onend();
      if(epoch===this.epoch)this.onError?.('Local voice playback failed: '+event.error);
    };
    this.synthesis.speak(utterance);
  }
}
