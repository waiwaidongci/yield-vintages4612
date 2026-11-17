from sqlalchemy import Column,Integer,BigInteger,String,JSON,Float,Boolean
from src.config.database import Base
class Period(Base):
 __tablename__='yield_periods'
 id=Column(Integer,primary_key=True); name=Column(String(120),unique=True); description=Column(String(250))
class Source(Base):
 __tablename__='yield_lots'
 id=Column(Integer,primary_key=True); natural_key=Column(String(120),unique=True); data=Column(JSON,nullable=False)
class Policy(Base):
 __tablename__='denominator_policies'
 id=Column(Integer,primary_key=True); version=Column(String(120),unique=True); data=Column(JSON,nullable=False)
class SourceVersion(Base):
 """底稿版本流水：只追加不改写。自增id即全局序列，核算以其为一致性边界；
 删除为tombstone（data为空、deleted=True），使已删批次仍可按发起时原值入册。"""
 __tablename__='yield_lot_versions'
 id=Column(BigInteger().with_variant(Integer,'sqlite'),primary_key=True,autoincrement=True)
 lot_id=Column(Integer,index=True,nullable=False)
 natural_key=Column(String(120))
 data=Column(JSON,nullable=True)
 deleted=Column(Boolean,default=False,nullable=False)
 created=Column(Float,nullable=False)
