import json

import redis


class CacheClient(object):

    def __init__(self):
        self.redis_client: redis.StrictRedis = None
        self.default_cache_time = 600

    def connect(self, url):
        self.redis_client = redis.StrictRedis.from_url(url)

    def get(self, key):
        data = self.redis_client.get(key)
        if data is None:
            return None
        return json.loads(data)

    def scan(self, match):
        cursor = '0'
        while cursor != 0:
            cursor, keys = self.redis_client.scan(cursor=cursor, match=match,
                                                  count=1000)  # Do we keep count hardcoded to 1000?
            for key in keys:
                item = self.get(key)
                if item is None:
                    continue
                yield key, item

    def pipeline(self):
        return self.redis_client.pipeline()

    def set(self, key, data, ex=None):
        if ex is None:
            ex = self.default_cache_time
        return self.redis_client.set(key, json.dumps(data), ex=ex)

    def delete(self, key):
        return self.redis_client.delete(key)
