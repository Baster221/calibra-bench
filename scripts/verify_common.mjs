// Read-only deployment verification: no account, no transaction submission.
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {createClient} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';
import {readRetry,digest} from './network.mjs';
export {digest};
export async function verifyBase(){
 const root=resolve(import.meta.dirname,'..');
 const manifest=JSON.parse(readFileSync(resolve(root,'deployment.json')));
 const receipts=JSON.parse(readFileSync(resolve(root,'evidence/network.json')));
 const state=JSON.parse(readFileSync(resolve(root,'evidence/state.json')));
 const client=createClient({chain:studionet});
 assert.equal(manifest.network,'studionet');
 assert.equal(manifest.chain_id,61999);
 assert.equal(receipts[0].hash,manifest.deployment_transaction);
 const local=readFileSync(resolve(root,manifest.source_path));
 const remote=Buffer.from(await readRetry(()=>client.getContractCode(manifest.address)));
 assert(local.equals(remote),'Deployed source differs byte-for-byte');
 const sha=createHash('sha256').update(local).digest('hex');
 assert.equal(sha,manifest.source_sha256);
 assert.equal(sha,manifest.deployed_source_sha256);
 for(const item of receipts){
  const tx=await readRetry(()=>client.getTransaction({hash:item.hash}));
  assert.equal(tx.status_name??tx.statusName,'FINALIZED',item.label);
  assert.equal(tx.consensus_data?.leader_receipt?.[0]?.execution_result??tx.txExecutionResultName,'SUCCESS',item.label);
  assert.equal(tx.recipient.toLowerCase(),manifest.address.toLowerCase());
  console.log(item.label+': FINALIZED / SUCCESS '+item.hash);
 }
 const read=(functionName,args)=>readRetry(()=>client.readContract({address:manifest.address,functionName,args,jsonSafeReturn:true}));
 console.log('Remote source SHA-256 matches: '+sha);
 return {manifest,state,read};
}
