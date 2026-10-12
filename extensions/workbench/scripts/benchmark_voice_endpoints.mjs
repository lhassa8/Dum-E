// Recorded PCM -> shipped pause gate. Virtual time, not microphone or latency proof.
import fs from 'node:fs';
import path from 'node:path';
import {PauseDetector} from '../src/physical_ai_lab/dume/web/voice-input.mjs';

const folder=process.argv[2];
if(!folder)throw Error('Pass the frozen generated clip directory');
const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json'),'utf8'));
const rows=[];
for(const item of manifest.cases){
 const bytes=fs.readFileSync(path.join(folder,item.file));
 const pcm=new Float32Array(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength));
 const gate=new PauseDetector({pauseMs:item.pause_ms});let completed=null;
 for(let offset=0;offset<pcm.length;offset+=640){
  const frame=pcm.subarray(offset,offset+640);
  const rms=Math.sqrt(frame.reduce((n,v)=>n+v*v,0)/frame.length);
  if(gate.sample(rms,(offset+frame.length)/16)){completed=(offset+frame.length)/16;break;}
 }
 const forced=completed===null&&gate.heardSpeech;
 const premature=item.expected_speech&&completed!==null&&completed<item.last_clean_voiced_ms-40;
 const passed=item.expected_speech?completed!==null&&!premature:completed===null&&!forced;
 rows.push({id:item.id,expected_speech:item.expected_speech,completed_ms:completed,
            forced_submit_at_limit:forced,premature,passed,
            completion_after_clean_voice_ms:completed===null||item.last_clean_voiced_ms===null?null:completed-item.last_clean_voiced_ms});
}
const report={scope:'Actual shipped energy pause gate, frozen recorded PCM, virtual clock. No ASR, microphone or robot jobs.',
 protocol_sha256:manifest.protocol_sha256,rows,count:rows.length,failures:rows.filter(r=>!r.passed).length,
 noise_only_false_submissions:rows.filter(r=>!r.expected_speech&&(r.completed_ms!==null||r.forced_submit_at_limit)).length};
fs.writeFileSync(path.join(folder,'energy-baseline.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({count:report.count,failures:report.failures,noise_only_false_submissions:report.noise_only_false_submissions}));
