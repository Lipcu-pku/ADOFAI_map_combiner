import os
import json
from ffmpeg import audio

filepath=input('请输入adofai文件地址: ').strip('\"')
with open(filepath, encoding="utf-8-sig") as filedic:
    contents=json.loads(filedic.read().replace(', }','}'))

pitch=float(input('请输入倍数: '))
contents["settings"]["bpm"]*=pitch
for action in contents["actions"]:
    if action["eventType"]=="SetSpeed":
        if action["speedType"]=="Bpm":
            action["beatsPerMinute"]*=pitch
musicname=contents["settings"]["songFilename"]
contents["settings"]["offset"]/=pitch
fpath,fname=os.path.split(filepath)
musicpath=fpath+'\\'+musicname
print(musicpath)
music_suffix=musicname.split('.')[-1]
print(music_suffix)
musicname_new=musicname.replace(f'.{music_suffix}',f'({pitch}x).{music_suffix}')
print(musicname_new)
musicpath_new=fpath+'\\'+musicname_new
audio.a_speed(f'\"{musicpath}\"',pitch,f'\"{musicpath_new}\"')
contents["settings"]["songFilename"]=musicname_new
file_new=json.dumps(contents,indent=4)
path_new=filepath.rstrip('.adofai')+f'({pitch}x).adofai'
fn=open(path_new,'w')
print(file_new, file=fn)
fn.close()
