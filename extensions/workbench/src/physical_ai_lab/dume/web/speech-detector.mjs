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
        if(capture){
          capture.queued++;
          capture.detector.processingMetrics.max_pending_frames=Math.max(
            capture.detector.processingMetrics.max_pending_frames,capture.queued);
        }
        framesDone=framesDone.then(async()=>{
          try {
            if(!capture||active!==capture||capture.signal?.aborted)return;
            const started=performance.now();
            await value.frameProcessor.process(frame,value.handleFrameProcessorEvent);
            capture.detector.processingMetrics.max_inference_ms=Math.max(
              capture.detector.processingMetrics.max_inference_ms,performance.now()-started);
          } finally {if(capture)capture.queued--;}
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
    detector.processingMetrics={max_pending_frames:0,max_inference_ms:0};
    const capture={stream,detector,onPause,signal,onFailure,frames:0,queued:0};active=capture;
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
