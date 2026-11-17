import hashlib,json,time
from sqlalchemy import func,select
from src.config.settings import ARTIFACT_DIR,FREEZE_BATCH
from src.models.run import Run
from src.models.source import SourceVersion
from src.services.calculation import accumulate,build_result,calculate
from src.services.validation import validate_policy
ACTIVE=('queued','freezing','frozen','calculating','running')
def run_dir(run_id):
 d=ARTIFACT_DIR/'runs'/str(run_id);d.mkdir(parents=True,exist_ok=True);return d
def pending_ids(db,older_than=None):
 """待恢复任务：排队中或处于可续跑阶段。older_than用于拣出停滞任务兜底重排。"""
 q=db.query(Run.id).filter(Run.status.in_(ACTIVE))
 if older_than is not None:q=q.filter(Run.updated<older_than)
 return [i for (i,) in q.order_by(Run.id).all()]
def process(db,run_id):
 """处理一个核算任务；每块一个事务，崩溃后从游标/检查点精确续跑，不漏批、不重复计入。"""
 run=db.get(Run,run_id)
 if not run or run.status not in ACTIVE:return
 try:
  if 'sources' in (run.snapshot or {}):legacy(db,run);return  # 旧版全量快照：原算法收尾，保持原值
  if run.status=='queued':begin(db,run)
  while run.status=='freezing':freeze_chunk(db,run)
  while run.status in ('frozen','calculating'):
   run.status='calculating';calc_chunk(db,run)
 except Exception as exc:
  db.rollback();run=db.get(Run,run_id)
  if run:run.status='failed';run.error=str(exc);run.updated=time.time();db.commit()
def legacy(db,run):
 if run.status not in ('queued','running'):return
 try:
  run.status='running';run.updated=time.time();db.commit()
  run.result=calculate(run.snapshot['sources'],run.snapshot['policy']);run.status='completed'
 except Exception as exc:run.status='failed';run.error=str(exc)
 run.updated=time.time();db.commit()
def begin(db,run):
 """queued→freezing：统计冻结边界内的待扫描批数（MySQL端聚合，进程内存O(1)）。"""
 run.status='freezing'
 run.progress_total=db.query(func.count(func.distinct(SourceVersion.lot_id))).filter(SourceVersion.id<=run.snapshot['freeze_seq']).scalar() or 0
 run.updated=time.time();db.commit()
def freeze_chunk(db,run):
 """按lot_id键集分页解析发起时刻（freeze_seq）的同版底稿，写入确定性命名的块文件。
 块文件tmp+rename原子替换，同名同内容可安全重写；游标与清单同事务提交，重试幂等。"""
 seq=run.snapshot['freeze_seq'];period=run.snapshot['period'];cursor=run.freeze_cursor or 0
 resolved=db.execute(select(SourceVersion.lot_id,func.max(SourceVersion.id)).where(SourceVersion.id<=seq,SourceVersion.lot_id>cursor).group_by(SourceVersion.lot_id).order_by(SourceVersion.lot_id).limit(FREEZE_BATCH)).all()
 if not resolved:finish_freeze(db,run);return
 versions={v.lot_id:v for v in db.query(SourceVersion).filter(SourceVersion.id.in_([mid for _,mid in resolved]))}
 lines=[]
 for lot_id,_ in resolved:
  v=versions[lot_id]
  if v.deleted or not v.data:continue
  if period!='全部' and v.data.get('period')!=period:continue
  lines.append(json.dumps(v.data,ensure_ascii=False,sort_keys=True))
 manifest=list(run.chunks or [])
 if lines:
  payload=('\n'.join(lines)+'\n').encode()
  name=f'lots-{cursor:012d}.jsonl';directory=run_dir(run.id)
  tmp=directory/('.tmp-'+name);tmp.write_bytes(payload);tmp.replace(directory/name)
  manifest.append({'file':name,'lots':len(lines),'sha256':hashlib.sha256(payload).hexdigest()})
 run.chunks=manifest
 run.progress_done=(run.progress_done or 0)+len(resolved)
 run.freeze_cursor=resolved[-1][0]
 run.updated=time.time();db.commit()
def finish_freeze(db,run):
 manifest=list(run.chunks or []);total=sum(m['lots'] for m in manifest)
 digest=hashlib.sha256(json.dumps({'policy':run.snapshot['policy'],'period':run.snapshot['period'],'freeze_seq':run.snapshot['freeze_seq'],'chunks':[m['sha256'] for m in manifest]},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 snapshot=dict(run.snapshot);snapshot['lot_count']=total;snapshot['chunk_count']=len(manifest)
 run.snapshot=snapshot;run.lot_count=total;run.checksum=digest
 if total:run.status='frozen'
 else:run.status='failed';run.error='所选期间没有底稿'
 run.updated=time.time();db.commit()
def calc_chunk(db,run):
 """逐块流式累加；透视累加器规模=期间×试制线×班次（有界），与底稿批数无关。
 每块落一次检查点（calc_state+calc_index同事务），中断后按块续算。"""
 policy=run.snapshot['policy'];validate_policy(policy)
 state=run.calc_state or {'pivot':[],'lots':0}
 pivot={(p,d,s):[n,de,c] for p,d,s,n,de,c in state['pivot']}
 manifest=run.chunks or []
 if run.calc_index<len(manifest):
  chunk=manifest[run.calc_index]
  with open(run_dir(run.id)/chunk['file'],encoding='utf-8') as f:
   for line in f:
    if line.strip():accumulate(pivot,json.loads(line),policy)
  state['lots']+=chunk['lots']
  run.calc_state={'pivot':[[k[0],k[1],k[2],v[0],v[1],v[2]] for k,v in pivot.items()],'lots':state['lots']}
  run.calc_index+=1
 if run.calc_index>=len(manifest):
  run.result=build_result(pivot,policy,state['lots']);run.status='completed'
 run.updated=time.time();db.commit()
