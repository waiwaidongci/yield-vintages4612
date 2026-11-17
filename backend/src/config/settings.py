import os,json
from pathlib import Path
CONFIG=json.loads((Path(__file__).resolve().parents[2]/'project.json').read_text())
DATABASE_URL=os.environ['DATABASE_URL']
REDIS_URL=os.getenv('REDIS_URL','redis://redis:6379/0')
SECRET=os.environ['JWT_SECRET']
ARTIFACT_DIR=Path(os.getenv('ARTIFACT_DIR','/app/artifacts'))
FREEZE_BATCH=int(os.getenv('FREEZE_BATCH','2000'))
