import time,uuid
from fastapi import HTTPException
from src.models.source import Source,Policy,Period,SourceVersion
from src.services.validation import validate_source,validate_policy
from src.services.audit import log
def save_source(db,user,data,id=None):
 validate_source(data)
 obj=db.get(Source,id) if id else Source(natural_key='user-'+uuid.uuid4().hex)
 if not obj: raise HTTPException(404,'底稿不存在')
 obj.data=data;db.add(obj);db.flush()
 db.add(SourceVersion(lot_id=obj.id,natural_key=obj.natural_key,data=data,deleted=False,created=time.time()))
 if not db.query(Period).filter_by(name=data['period']).first():db.add(Period(name=data['period'],description='业务来源自动登记期间'))
 log(db,user.email,'source.update' if id else 'source.create',obj.natural_key);db.commit();return obj
def delete_source(db,user,id):
 obj=db.get(Source,id)
 if not obj: raise HTTPException(404,'底稿不存在')
 db.add(SourceVersion(lot_id=obj.id,natural_key=obj.natural_key,data=None,deleted=True,created=time.time()))
 db.delete(obj);log(db,user.email,'source.delete',id);db.commit();return id
def save_policy(db,user,data):
 validate_policy(data)
 if db.query(Policy).filter_by(version=data['version']).first(): raise HTTPException(409,'版本名已存在，请另建版本保留历史')
 obj=Policy(version=data['version'],data=data);db.add(obj);log(db,user.email,'policy.version',data['version']);db.commit();return obj
