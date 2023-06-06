import asyncio
import aioredis


class Client:

    # def __init__(self, host='172.93.162.131', password='Uubt800959632', port=26800, loop=None, encoding='utf-8', db=2):
    def __init__(self, host='127.0.0.1', password=None, port=6379, loop=None, encoding='utf-8', db=1):
        self.host = host
        self.password = password
        self.port = port
        self.encoding = encoding
        self.db = db

        self._client: aioredis.commands.Redis = None
        self.loop = loop or asyncio.get_event_loop()
        self.loop.run_until_complete(self.__init_client())

    async def __init_client(self):
        self._client = await aioredis.create_redis_pool(f'redis://{self.host}:{self.port}',
                                                        password=self.password,
                                                        encoding=self.encoding)

    async def close(self):
        self._client.close()
        await self._client.wait_closed()

    async def get(self, key):
        return await self._client.get(key)

    async def get_str(self, key):
        return await self._client.get(key, encoding='utf-8')

    async def get_int(self, key):
        value = await self._client.get(key)
        return int(value) if value else 0

    # def get_json(self, key):
    #     value = self._client.get(key)
    #     return json.loads(value) if value else value

    async def set(self, key, value, ex=24 * 60 * 60):
        await self._client.set(key, value, expire=ex)

    # def set_json(self, key, obj, ex=24 * 60 * 60):
    #     self.set(key, json.dumps(obj), ex)

    async def delete(self, key):
        return await self._client.delete(key)

    async def llen(self, key):
        return await self._client.llen(key)

    async def keys(self, key):
        return await self._client.keys(key)

    def lpop(self, key, encoding='utf-8'):
        return self._client.lpop(key, encoding=encoding)

    def lrange(self, key, start, stop, encoding='utf-8'):
        return self._client.lrange(key, start, stop, encoding=encoding)

    def rpop(self, key, encoding='utf-8'):
        return self._client.rpop(key, encoding=encoding)

    def lpush(self, key, value):
        return self._client.lpush(key, value)

    def rpush(self, key, value):
        return self._client.rpush(key, value)

    # def rpoplpush(self, queue):
    #     return self.__to_str(self._client.rpoplpush(queue, queue))

    # def incr(self, key, amount=1):
    #     return self._client.incr(key, amount=amount)

    # def decr(self, key, amount=1):
    #     return self._client.decr(key, amount=amount)

    async def hlen(self, key):
        return await self._client.hlen(key)

    async def hset(self, key, field, value):
        await self._client.hset(key, field, value)

    async def hdel(self, key, field):
        await self._client.hdel(key, field)

    async def hget(self, key, field):
        return await self._client.hget(key, field)

    async def hgetall(self, key):
        return await self._client.hgetall(key)

    async def zadd(self, key, value, score):
        await self._client.zadd(key, score, value)

    async def zpopmin(self, key):
        return await self._client.zpopmin(key)

    async def zcount(self, key):
        return await self._client.zcount(key)

    async def script_load(self, script):
        return await self._client.script_load(script)

    async def script_eval(self, digest, keys=None, args=None):
        return await self._client.evalsha(digest, keys or [], args or [])

    # def get_client(self) -> redis.Redis:
    #     return self._client


REDIS_CLIENT = Client()
