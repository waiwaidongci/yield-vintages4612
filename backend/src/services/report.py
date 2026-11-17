import time
from fastapi import HTTPException
from sqlalchemy import func,text
from src.models.source import Policy,SourceVersion
from src.models.run import Run
from src.services.audit import log
from src.services.queue import enqueue
def backfill_versions(db):
 """为历史遗留底稿一次性补登记版本行（集合操作在数据库端完成，进程内存O(1)，幂等）。"""
 db.execute(text('INSERT INTO yield_lot_versions (lot_id,natural_key,data,deleted,created) SELECT l.id,l.natural_key,l.data,0,:now FROM yield_lots l LEFT JOIN yield_lot_versions v ON v.lot_id=l.id WHERE v.id IS NULL'),{'now':time.time()})
def submit(db,user,body):
 """排队：只记录口径与一致性边界freeze_seq，不复制底稿数据，进程额外内存O(1)。"""
 policy=db.get(Policy,body.policy_id)
 if not policy: raise HTTPException(404,'口径版本不存在')
 backfill_versions(db)
 freeze_seq=db.query(func.max(SourceVersion.id)).scalar() or 0
 if not freeze_seq: raise HTTPException(422,'所选期间没有底稿')
 snapshot={'policy':policy.data,'period':body.period,'freeze_seq':freeze_seq}
 obj=Run(name=body.name,status='queued',snapshot=snapshot,checksum='',created=time.time(),updated=time.time(),approved=False,freeze_cursor=0,progress_total=0,progress_done=0,lot_count=0,chunks=[],calc_index=0)
 db.add(obj);db.flush()
 log(db,user.email,'run.queue',body.name);db.commit()
 enqueue(obj.id)
 return obj
def approve(db,user,id,note):
 obj=db.get(Run,id)
 if not obj: raise HTTPException(404,'报告不存在')
 if obj.status!='completed': raise HTTPException(409,'仅可复核已完成报告')
 if obj.approved: raise HTTPException(409,'报告已经复核')
 obj.approved=True;obj.review=note;log(db,user.email,'run.approve',id);db.commit();return obj
def retry(db,user,id):
 """失败任务重试：保留冻结游标与计算检查点，从断点续跑，不漏批、不重复计入。"""
 obj=db.get(Run,id)
 if not obj: raise HTTPException(404,'报告不存在')
 if obj.status!='failed': raise HTTPException(409,'仅失败的任务可重试')
 obj.status='queued';obj.error=None;obj.updated=time.time()
 log(db,user.email,'run.retry',id);db.commit();enqueue(obj.id);return obj
