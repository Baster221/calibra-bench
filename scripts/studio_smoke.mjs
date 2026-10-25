// MUTATING: fresh gasless StudioNet benchmark, ephemeral signers and salts.
import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';
import {demo,digest} from './network.mjs';

const d=await demo('contracts/calibra_bench.py',4);
const tag='sealed-workshop-v1';
const questions=[
 'Does the notice offer support on Saturdays?',
 'Does the notice require attendees to register before entering?',
 'Is admission to the workshop free?',
];
const reference='The notice offers support Monday through Friday only. Support is not offered on Saturdays or Sundays. Attendees must register before entering the workshop.';
const documentSalt=randomBytes(32).toString('hex');
const documentDigest=digest({protocol:'Calibra/document/v1',chain_id:61999,contract:d.address,
 curator:d.accounts[0].address,tag,questions,document:reference,salt:documentSalt});
await d.write(0,'create',[tag,JSON.stringify(questions),JSON.stringify(d.accounts.slice(1,3).map(a=>a.address)),
 documentDigest,3600,3600,3600],'open benchmark with sealed reference and fixed roster');
const forecasts=[[1000,9000,5000],[9000,1000,0]];
const salts=[randomBytes(32).toString('hex'),randomBytes(32).toString('hex')];
for(let i=0;i<2;i++){
 const commitment=digest({protocol:'Calibra/forecast/v1',chain_id:61999,contract:d.address,round_id:1,
  participant:d.accounts[i+1].address,probabilities:forecasts[i],salt:salts[i]});
 await d.write(i+1,'commit_forecast',[1,commitment],'seal forecast '+(i+1));
}
const sealed=await d.read('get_round',[1]);
assert.equal(sealed.reference,'');
assert(sealed.players.every(p=>p.probabilities.length===0));
await d.write(3,'advance',[1],'close committed cohort before prediction reveal');
for(let i=0;i<2;i++)await d.write(i+1,'reveal_forecast',[1,JSON.stringify(forecasts[i]),salts[i]],'reveal forecast '+(i+1));
await d.write(3,'advance',[1],'lock all revealed forecasts before opening reference');
const locked=await d.read('get_round',[1]);
assert.equal(locked.phase,'ANSWER');
assert.equal(locked.reference,'');
await d.write(0,'reveal_reference',[1,reference,documentSalt],'reveal hash-matched precommitted reference');
await d.write(3,'resolve',[1],'consensus answer vector and exact quadratic scoring');
const final=await d.read('get_round',[1]);
assert.equal(final.phase,'SCORED');
assert.deepEqual(final.outcomes,['NO','YES','UNKNOWN']);
assert.deepEqual(final.scored_questions,[0,1]);
assert.deepEqual(final.leaderboard.map(r=>r.squared_error),[2000000,162000000]);
assert.deepEqual(final.leaderboard.map(r=>r.score_bps),[9900,1900]);
const result=await d.read('result_commitment',[1]);
if(d.record)d.save('evidence/state.json',{sealed,locked,final,result,
 roles:{curator:d.accounts[0].address,forecasters:d.accounts.slice(1,3).map(a=>a.address),keeper:d.accounts[3].address}});
console.log('Calibra Bench passed with frozen forecasts, one void column and exact ranks at '+d.address);
