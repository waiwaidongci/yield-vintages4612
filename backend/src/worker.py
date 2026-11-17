import time,traceback
from pathlib import Path
from src.config.database import Base,engine,Session
from src.models import identity,source,run
from src.services.pipeline import process,pending_ids
from src.services.queue import dequeue,enqueue
from src.services.delivery import tick
Base.metadata.create_all(engine)
def requeue(older_than=None):
 """恢复排队：启动时捞起所有中断任务；运行中周期拣出停滞任务兜底（处理幂等，可安全重复入队）。"""
 with Session() as db:
  for run_id in pending_ids(db,older_than):enqueue(run_id)
requeue()
n=0
while True:
 Path('/tmp/worker-heartbeat').write_text(str(time.time()))
 try:
  item=dequeue()
  if item:
   with Session() as db:process(db,int(item))
  else:time.sleep(1)
  with Session() as db:tick(db)
  n+=1
  if n%15==0:requeue(time.time()-15)
 except Exception:traceback.print_exc()
