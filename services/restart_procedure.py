import os
# 获取到该进程的id
pid = int(os.popen("ps aux |grep telegram-client/start.py |grep -v grep|awk '{print $2}'").
          read().replace('\n', '').replace('\r', ''))
# 用kill命令杀死该进程
os.system('kill -9 {}'.format(pid))

# 重新启动程序
os.system('sh /home/telegram-client/startup.sh')
