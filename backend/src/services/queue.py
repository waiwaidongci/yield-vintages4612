import redis
from src.config.settings import REDIS_URL
QUEUE='report-jobs'
_client=None
def client():
 global _client
 if _client is None:_client=redis.Redis.from_url(REDIS_URL)
 return _client
def enqueue(run_id):client().rpush(QUEUE,run_id)
def dequeue():return client().lpop(QUEUE)
