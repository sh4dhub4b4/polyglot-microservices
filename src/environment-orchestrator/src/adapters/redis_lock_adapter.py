import os
import redis
from domain.ports import ILockManager

class RedisLockAdapter(ILockManager):
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "redis-svc.eci-system.svc.cluster.local")
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=6379, 
            db=0, 
            decode_responses=True
        )

    def acquire_lock(self, lock_key: str, ttl_seconds: int = 60) -> bool:
        try:
            return bool(self.redis_client.set(lock_key, "leased", ex=ttl_seconds, nx=True))
        except Exception as e:
            print(f"⚠️ Redis lock acquisition failed for {lock_key}: {e}")
            return False

    def release_lock(self, lock_key: str) -> None:
        try:
            self.redis_client.delete(lock_key)
            print(f"   🔓 Redis lock released for {lock_key}")
        except Exception as e:
            print(f"   ⚠️ Redis lock release failed for {lock_key}: {e}")
