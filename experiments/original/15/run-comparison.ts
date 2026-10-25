import {writeFileSync} from 'node:fs';
import {samplePlan} from '../../../src/algorithms/sampling.ts';
import {armEnvironment} from '../../../src/algorithms/environments.ts';
const env=armEnvironment(.15),rows=[];
for(const seed of [1,7,42])for(const algorithm of ['rrt','connect','star','informed'] as const){
 let last;for(const f of samplePlan({algorithm,env,seed,iterations:1200,step:Math.PI/18,radius:35*Math.PI/180,goalBias:.05}))last=f;
 if(!last)throw Error('No frame');
 const p=last.path??[];const valid=p.length>1&&p.every(q=>env.clearance(q)>0)&&p.slice(1).every((q,i)=>env.edge(p[i],q));
 if(p.length&&!valid)throw Error('Returned path failed independent edge recheck');
 rows.push({algorithm,seed,stats:last.stats,path:p,edgeRecheck:valid});
}
writeFileSync('experiments/original/15/comparison.json',JSON.stringify({conditions:{scene:'same static 2R arm',obstacleRadiusM:.15,iterations:1200,stepDeg:10,radiusDeg:35,goalBias:.05,seeds:[1,7,42]},scope:'Equal iteration budget, not equal elapsed time or collision checks. No new planners executed.',rows},null,2));
console.log(rows.map(r=>({algorithm:r.algorithm,seed:r.seed,checks:r.stats.checks,cost:r.stats.cost,valid:r.edgeRecheck})));
