import asyncio
# from common import pg_aioredis
import redis_util as pg_aioredis
import json
import re

LOOP = asyncio.new_event_loop()

host = '198.11.176.126'
password = 'EQC6vrLaQ5rdRMHU'
client = pg_aioredis.Client(host=host, password=password, loop=LOOP)


async def main():
    data = {}
    key_pre = 'tg:'
    i = 0
    for key in await client.keys(f'{key_pre}*'):
        i += 1
        # channel = re.findall(r'tg_input_channel_handle:(.*?)', key)
        # if channel:
        #     tel = key[-11:]
        #     data[channel[0]] = tel
        print(key)
    # data = json.dumps(data)
    # with open('new_channel_tel.json', 'w') as json_file:
    #     json_file.write(data)
    print(i)

if __name__ == "__main__":
    # asyncio.run(main())
    LOOP.run_until_complete(main())