// Use installed local voices only. A generation prevents late network replies
// from starting sound after Stop, mute, a new utterance, or page departure.
export class LocalSpeech {
  constructor({post, onError, synthesis=globalThis.speechSynthesis, Utterance=globalThis.SpeechSynthesisUtterance}) {
    this.post=post; this.synthesis=synthesis; this.Utterance=Utterance; this.epoch=0;
    this.onError=onError;
  }
  stop() { this.epoch++; this.synthesis?.cancel(); }
  async speak(text) {
    this.stop(); const epoch=this.epoch;
    const result=await this.post('/speak',{message:text});
    if(epoch!==this.epoch) return;
    if(!result.browser) return;
    const voice=this.synthesis?.getVoices().find(v=>v.localService&&v.lang.startsWith('en'));
    if(!voice) {
      await this.post('/speech-finished/'+result.generation);
      throw Error('No installed local English voice is available in this browser.');
    }
    const utterance=new this.Utterance(text); utterance.voice=voice;
    utterance.onstart=()=>this.post('/speech-started/'+result.generation).catch(()=>{});
    utterance.onend=()=>this.post('/speech-finished/'+result.generation).catch(()=>{});
    utterance.onerror=event=>{
      utterance.onend();
      if(epoch===this.epoch)this.onError?.('Local voice playback failed: '+event.error);
    };
    this.synthesis.speak(utterance);
  }
}
