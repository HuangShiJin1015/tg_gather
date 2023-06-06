import asyncio

from common import redis_util

LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)

CLIENT = redis_util.Client()


async def main():
    # await CLIENT.lpush('Age', '12')
    # l = await CLIENT.llen('Age')
    # r = await CLIENT.lrange('Age', 0, l)
    # print(r)
    # if await CLIENT.get('tg_media_handle/10025+25') is None:
    #     await CLIENT.set('tg_media_handle/10025+25', '1', )
    # else:
    #     print('跳过下载')
    # r = await CLIENT.get('tg_input_channel_handle:nedoviazam_net->+85252666459')
    # 循环模糊删除redis数据
    r = await CLIENT.keys('tg_input_channel_handle*+85265868027')
    x = 1
    for i in r:
        await CLIENT.delete(i)
        print(x)
        x += 1


    # await CLIENT.delete('test')
    # assert (await CLIENT.get_str('Name')) == '123'

    # key = 'test_list'
    # for i in range(5):
    #     await CLIENT.zadd(key, f'{i}', 111 + i)
    # assert (await CLIENT.zpopmin(key))[0] == '0'
    # assert (await CLIENT.zpopmin(key))[0] == '1'
    # assert (await CLIENT.zpopmin(key))[0] == '2'
    # assert (await CLIENT.zpopmin(key))[0] == '3'

    # script_key = await CLIENT.script_load("""
    # local c = redis.call('ZCOUNT', '{0}', 0, ARGV[1])
    # if (c > 0) then
    #     return redis.call('ZPOPMIN', '{0}')[1]
    # end
    # return nil
    # """.format(key))
    # assert (await CLIENT.script_eval(script_key, args=[100000])) == '4'
    #
    # await CLIENT.delete(key)

    # key = 'test_hash'
    # # await CLIENT.delete(key)
    # assert (await CLIENT.hlen(key)) == 0
    # await CLIENT.hset(key, 'hello', 'world')
    # assert (await CLIENT.hget(key, 'hello')) == 'world'
    #
    # assert (await CLIENT.hlen(key)) == 1
    # await CLIENT.hset(key, 'hello', 'world2')
    # assert (await CLIENT.hget(key, 'hello')) == 'world2'
    #
    # assert (await CLIENT.hlen(key)) == 1
    # await CLIENT.hset(key, 'hello2', 'world2')
    # assert (await CLIENT.hget(key, 'hello2')) == 'world2'
    #
    # assert (await CLIENT.hlen(key)) == 2
    # assert len(await CLIENT.hgetall(key)) == 2
    # all_data = await CLIENT.hgetall(key)
    # assert all_data['hello'] == 'world2'
    # assert all_data['hello2'] == 'world2'
    #
    # await CLIENT.hdel(key, 'hello2')
    # assert (await CLIENT.hlen(key)) == 1
    # await CLIENT.delete(key)
    # assert (await CLIENT.hlen(key)) == 0
    #
    # lkey = 'lkey'
    # await CLIENT.lpush(lkey, '你好')
    # await CLIENT.lpush(lkey, '2')
    # await CLIENT.lpush(lkey, '3')
    #
    # assert await CLIENT.rpop(lkey) == '你好'
    # assert await CLIENT.rpop(lkey) == '2'
    # assert await CLIENT.rpop(lkey) == '3'
    #
    # assert await CLIENT.llen(lkey) == 0
    #
    # await CLIENT.rpush(lkey, '1')
    # await CLIENT.rpush(lkey, '2')
    #
    # assert await CLIENT.llen(lkey) == 2
    #
    # assert await CLIENT.lpop(lkey) == '1'
    # assert await CLIENT.lpop(lkey) == '2'
    #
    # assert await CLIENT.lpop(lkey) is None
    #
    # await CLIENT.close()


if __name__ == "__main__":
    LOOP.run_until_complete(main())
