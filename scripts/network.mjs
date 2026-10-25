// Public demo infrastructure. Signing keys stay only in process memory.
import {readFileSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {createClient,createAccount} from 'genlayer-js';
import {studionet} from 'genlayer-js/chains';

export const canonical = value => {
  const sort = x => Array.isArray(x) ? x.map(sort) : x && typeof x==='object' ? Object.fromEntries(Object.keys(x).sort().map(k=>[k,sort(x[k])])) : x;
  return JSON.stringify(sort(value)).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
};
export const digest = value => createHash('sha256').update(canonical(value)).digest('hex');
export async function readRetry(operation){
  for(let attempt=0;;attempt++){
    try{return await operation();}
    catch(error){
      if(attempt>=2)throw error;
      console.log('Read-only RPC interrupted; retrying.');
      await new Promise(r=>setTimeout(r,2000*(attempt+1)));
    }
  }
}
export async function demo(sourcePath,count){
  const root=resolve(import.meta.dirname,'..');
  const code=readFileSync(resolve(root,sourcePath),'utf8');
  const accounts=Array.from({length:count},()=>createAccount());
  const clients=accounts.map(account=>createClient({chain:studionet,account}));
  const record=process.argv.includes('--record');
  const save=(name,obj)=>writeFileSync(resolve(root,name),JSON.stringify(obj,(_,v)=>typeof v==='bigint'?v.toString():v,2)+'\n');
  const evidence=[];
  async function receipt(hash,label){
    console.log('submitted '+label+': '+hash);
    const tx=await clients[0].waitForTransactionReceipt({hash,status:'FINALIZED',interval:6500,retries:100});
    const status=tx.status_name??tx.statusName;
    const leader=tx.consensus_data?.leader_receipt?.[0];
    const execution=leader?.execution_result??tx.txExecutionResultName;
    assert.equal(status,'FINALIZED',label);
    assert.equal(execution,'SUCCESS',label+': '+JSON.stringify(leader?.genvm_result));
    evidence.push({label,hash,status,execution,result:tx.result_name??tx.resultName,
      votes:tx.consensus_data?.votes,leader_result:leader?.result,eq_outputs:leader?.eq_outputs});
    if(record)save('evidence/network.json',evidence);
    console.log('finalized '+label);
    return tx;
  }
  const deploymentHash=await clients[0].deployContract({code,args:[]});
  const deployed=await receipt(deploymentHash,'deploy');
  const address=deployed.recipient;
  assert.equal(await readRetry(()=>clients[0].getContractCode(address)),code);
  if(record){
    const hash=createHash('sha256').update(code).digest('hex');
    save('deployment.json',{network:'studionet',chain_id:61999,rpc:'https://studio.genlayer.com/api',address,
      explorer:'https://explorer-studio.genlayer.com/address/'+address,deployment_transaction:deploymentHash,
      deployer:accounts[0].address,source_path:sourcePath,source_sha256:hash,deployed_source_sha256:hash,
      byte_for_byte_match:true,runner:'py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6',
      deployment_status:'FINALIZED',deployment_execution:'SUCCESS',verified_at:new Date().toISOString()});
  }
  return {address,accounts,record,save,
    read:(functionName,args)=>readRetry(()=>clients[0].readContract({address,functionName,args,jsonSafeReturn:true})),
    write:async(index,functionName,args,label=functionName)=>receipt(await clients[index].writeContract({address,functionName,args,value:0n}),label)};
}
