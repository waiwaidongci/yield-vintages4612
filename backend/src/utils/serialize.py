def row(obj):
 return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}
def run_view(obj):
 """报告视图：剔除内部断点状态，补充块计数，避免向页面传输大字段。"""
 d=row(obj)
 d.pop('calc_state',None)
 d['chunk_count']=len(d.pop('chunks',None) or [])
 return d
