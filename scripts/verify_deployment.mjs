import assert from 'node:assert/strict';
import {verifyBase,digest} from './verify_common.mjs';
const {manifest,state,read}=await verifyBase();
const current=await read('get_round',[1]);
const result=await read('result_commitment',[1]);
assert.deepEqual(current,state.final);
assert.deepEqual(result,state.result);
assert.equal(result.digest,digest(result.payload));
assert.equal(current.phase,'SCORED');
assert.equal(current.reference_digest,digest({protocol:'Calibra/document/v1',chain_id:61999,
 contract:manifest.address,curator:current.curator,tag:current.tag,questions:current.questions,
 document:current.reference,salt:current.reference_salt}));
const indices=current.outcomes.flatMap((outcome,i)=>outcome==='UNKNOWN'?[]:[i]);
assert.deepEqual(indices,current.scored_questions);
const expected=[];
const maximum=BigInt(indices.length)*100000000n;
for(const p of current.players){
 if(!p.revealed)continue;
 assert.equal(p.commitment,digest({protocol:'Calibra/forecast/v1',chain_id:61999,contract:manifest.address,
  round_id:1,participant:p.participant,probabilities:p.probabilities,salt:p.salt}));
 let loss=0n;
 for(const i of indices){
  const difference=BigInt(p.probabilities[i])-(current.outcomes[i]==='YES'?10000n:0n);
  loss+=difference*difference;
 }
 expected.push({participant:p.participant,squared_error:Number(loss),score_bps:Number((maximum-loss)*10000n/maximum)});
}
expected.sort((a,b)=>a.squared_error-b.squared_error||a.participant.toLowerCase().localeCompare(b.participant.toLowerCase()));
for(const row of expected)row.rank=1+expected.filter(other=>other.squared_error<row.squared_error).length;
assert.deepEqual(expected,current.leaderboard);
console.log('All reference/forecast commitments, common void mask, integer losses and exact ranks recomputed.');
console.log('Verified Calibra Bench '+manifest.address+' against current live state.');
