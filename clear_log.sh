#! /bin/bash
path="$(cd "$(dirname $0)" && pwd)"

ID=`ps -ef | grep -v grep| grep python3`
#echo $ID{1}
OLD_IFS="$IFS"
ifs=" "
arr=($ID)
#for id in $ID;
#do
#kill -9 $id
#echo "kill ${id[0]}"
#done

kill -9 ${arr[1]}
echo "kill ${arr[1]}"

cd "${path}/logs/" && rm-rf *
cd "${path}/" && sh startup.sh