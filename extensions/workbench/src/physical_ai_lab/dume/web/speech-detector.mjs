// Pretrained Silero probabilities; local assets, no microphone access during loading.
export function createSpeechMonitor({getVAD=()=>globalThis.vad,
  Audio=globalThis.AudioContext||globalThis.webkitAudioContext}={}) {
  let pending=null,cleanup=Promise.resolve(),framesDone=Promise.resolve(),active=null;
  function prepare(){
    if(!pending)pending=Promise.resolve().then(()=>{
      const library=getVAD();
      if(!library?.MicVAD)throw Error('Local speech detector assets unavailable. Run scripts/prepare_speech_vad.py.');
      return library.MicVAD.new({model:'v5',startOnLoad:false,
        baseAssetPath:'/speech-vad/',onnxWASMBasePath:'/speech-vad/',
        ortConfig:ort=>{ort.env.wasm.numThreads=1;ort.env.logLevel='error';},
        // MicrophoneInput owns acquisition and tracks; this library never asks for access.
        getStream:async()=>{if(!active)throw Error('No active capture');return active.stream;},
        resumeStream:async()=>{if(!active)throw Error('No active capture');return active.stream;},
        pauseStream:async()=>{},
        onFrameProcessed:probs=>{
          const capture=active;if(!capture||capture.signal?.aborted)return;
          capture.frames++;
          if(capture.detector.sampleProbability(probs.isSpeech,capture.frames*32))capture.onPause();
        },
      });
    }).then(value=>{
      // Serialize recurrent inference and reject frames from a cancelled capture.
      value.processFrame=frame=>{
        const capture=active;
        framesDone=framesDone.then(async()=>{
          if(!capture||active!==capture||capture.signal?.aborted)return;
          await value.frameProcessor.process(frame,value.handleFrameProcessorEvent);
        }).catch(error=>{if(active===capture)capture.onFailure(error);});
        return framesDone;
      };
      return value;
    });
    return pending;
  }
  async function monitor(stream,detector,onPause,signal,onFailure=()=>{}){
    const loaded=await prepare();await cleanup;
    if(signal?.aborted)return ()=>{};
    if(active)throw Error('A speech capture is already active');
    if(!Audio)throw Error('Audio capture is unavailable in this browser');
    if(loaded.initializationState==='uninitialized')loaded.options.audioContext=new Audio();
    const capture={stream,detector,onPause,signal,onFailure,frames:0};active=capture;
    let stopped=false;
    const stop=()=>{
      if(stopped)return;stopped=true;
      if(active===capture)active=null;
      cleanup=Promise.resolve(loaded.pause()).then(()=>framesDone).then(()=>loaded.frameProcessor.reset());
    };
    try {
      await loaded.start();await loaded.getAudioInstances().audioContext.resume();
      if(signal?.aborted)stop();
      return stop;
    } catch(error){stop();throw error;}
  }
  async function close(){
    if(!pending)return;
    await cleanup;
    const loaded=await prepare();
    if(loaded.initializationState==='uninitialized')await loaded.model.release();
    else await loaded.destroy();
    // The application owns an explicitly supplied audio context.
    await loaded.options.audioContext?.close();pending=null;
  }
  return {prepare,monitor,close};
}
