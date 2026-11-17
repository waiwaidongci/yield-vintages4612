from sqlalchemy import Column,Integer,String,JSON,Text,Float,Boolean
from src.config.database import Base
class Run(Base):
 __tablename__='yield_runs'
 id=Column(Integer,primary_key=True); name=Column(String(120)); status=Column(String(20)); snapshot=Column(JSON); checksum=Column(String(64)); result=Column(JSON); error=Column(Text); created=Column(Float); approved=Column(Boolean,default=False); review=Column(Text,default='')
 # 分块冻结/流式计算进度与断点（新列均有默认值，既有报告行不受影响）
 freeze_cursor=Column(Integer,default=0)   # 已扫描到的底稿lot_id游标
 progress_total=Column(Integer,default=0)  # 冻结边界内待扫描批数
 progress_done=Column(Integer,default=0)   # 已扫描批数
 lot_count=Column(Integer,default=0)       # 实际入册（冻结）批数
 chunks=Column(JSON,default=list)          # 块清单：[{file,lots,sha256}]
 calc_index=Column(Integer,default=0)      # 已计算块数（断点续算游标）
 calc_state=Column(JSON)                   # 计算检查点：透视累加器
 updated=Column(Float,default=0)
class Schedule(Base):
 __tablename__='delivery_schedules'
 id=Column(Integer,primary_key=True); name=Column(String(120)); run_id=Column(Integer); interval_seconds=Column(Integer); next_at=Column(Float); enabled=Column(Boolean,default=True)
class Delivery(Base):
 __tablename__='deliveries'
 id=Column(Integer,primary_key=True); schedule_id=Column(Integer); run_id=Column(Integer); due_key=Column(String(120),unique=True); created=Column(Float); payload=Column(JSON)
