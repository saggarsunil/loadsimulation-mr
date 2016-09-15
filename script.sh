#/bin/bash

#Parse the commandline arguements
while getopts "t:f:" opt;
do
  case $opt in
    t)rtime=$OPTARG
      ;;
    f)file_list=$OPTARG
      ;;
   esac
done

sleep $rtime
echo $rtime
echo $file_list

