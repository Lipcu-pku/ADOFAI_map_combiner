import os, json, wave, contextlib, shutil
from ffmpeg import audio
from pydub import AudioSegment

N=int(input('合谱数量: '))
if N<=1:
    exit()

while True:
    breaktime=float(input('请输入间隔时间, 单位秒: '))
    if breaktime>0: break

if breaktime!=0:
    breakpitch=5.006479166666667/breaktime
    audio.a_speed("./break.wav",breakpitch,"./actualbreak.wav")
    ab=AudioSegment.from_wav("./actualbreak.wav")
else:
    ab=None

pathDatatrans={'R':0, 'p':15, 'J':30, 'E':45, 'T':60, 'o':75, 'U':90, 'q':105, 'G':120, 'Q':135, 'H':150, 'W':165, 'L': 180, 'x':195, 'N':210, 'Z':225, 'F':240, 'V':255, 'D':270, 'Y':285, 'B':300, 'C':315, 'M':330, 'A':345, '5':555, '6':666, '7':777, '8':888, '!':999}

def wav_converter(filepath):
    fname,fmt=os.path.splitext(filepath)
    if fmt=='.wav': song=AudioSegment.from_wav(filepath)
    elif fmt=='.ogg': song=AudioSegment.from_ogg(filepath)
    elif fmt=='.mp3': song=AudioSegment.from_mp3(filepath)
    return song

def read(path):
    cor={
        ", }": "}",
        ",  }": "}",
        "]\n\t\"decorations\"": "],\n\t\"decorations\"",
        "],\n}": "]\n}",
        ",,": ",",
        "}\n\t\t{":"},\n\t\t{",
        "},\n\t]": "}\n\t]"
    }
    f=open(path, encoding='utf-8-sig')
    contents=f.read()
    # 把adofai文件里的json语法错误改掉
    for c in cor:
        contents=contents.replace(c,cor[c])
    contents=json.loads(contents)
    if 'pathData' in contents:
        pathData=list(contents['pathData'])
        angleData=[pathDatatrans[i] for i in pathData]
        for i,angle in enumerate(angleData):
            lastangle=angleData[i-1] if i>=1 else 0
            if angle==555: angleData[i]=(lastangle+72)%360
            if angle==666: angleData[i]=(lastangle-72)%360
            if angle==777: angleData[i]=(lastangle+360/7)%360
            if angle==888: angleData[i]=(lastangle-360/7)%360
        del contents["pathData"]
        contents["angleData"]=angleData
    else: angleData=contents["angleData"]
    n=len(angleData)
    settings=contents["settings"]
    for setting in settings:
        if settings[setting]=="Enabled": settings[setting]=True
        if settings[setting]=="Disabled": settings[setting]=False
    contents["settings"]=settings
    actions=[]
    for action in contents["actions"]:
        for key in action:
            if action[key]=="Enabled":
                action[key]=True
            elif action[key]=="Disabled":
                action[key]=False
        if action["eventType"] in ["MoveTrack", "RecolorTrack"]:
            if action["startTile"][1]=="Start":
                action["startTile"][0]-=action["floor"]
            elif action["startTile"][1]=="End":
                action["startTile"][0]=n-action["floor"]-action["startTile"][0]
            if action["endTile"][1]=="Start":
                action["endTile"][0]-=action["floor"]
            elif action["endTile"][1]=="End":
                action["endTile"][0]=n-action["floor"]-action["endTile"][0]
            action["startTile"][1]="ThisTile"
            action["endTile"][1]="ThisTile"
        if action["eventType"]=="PositionTrack":
            if "relativeTo" in action:
                if action["relativeTo"][1]=="Start":
                    action["relativeTo"][0]-=action["floor"]
                elif action["relativeTo"][1]=="End":
                    action["relativeTo"][0]=n-action["floor"]-action["relativeTo"][0]
                action["relativeTo"][1]="ThisTile"
        if action["eventType"]=="MoveCamera":
            if "dontDisable" in action: del action["dontDisable"]
            if "minVfxOnly" in action: del action["minVfxOnly"]
        if action["eventType"]=="CustomBackground":
            action["imageSmoothing"]=action.get("imageSmoothing",True)
            if "unscaledSize" in action: 
                action["scalingRatio"]=action["unscaledSize"]
                del action["unscaledSize"]
        if action["eventType"]=="SetSpeed":
            action["speedType"]=action.get("speedType","Bpm")
            action["angleOffset"]=action.get("angleOffset",0)
        if action["eventType"]=="MoveTrack":
            if "maxVfxOnly" in action: del action["maxVfxOnly"]
        if action["eventType"]=="ShakeScreen":
            action["ease"]=action.get("ease","Linear")
        if action["eventType"]=="RepeatEvents":
            action["repeatType"]=action.get("repeatType","Beat")
            action["floorCount"]=action.get("floorCount",1)
            action["executeOnCurrentFloor"]=action.get("executeOnCurrentFloor",False)
        if action["eventType"] in ["AddDecoration","MoveDecorations"]:
            continue
        else:
            actions.append(action)
    contents["actions"]=actions
    return contents

def copy_bgimg(path):
    bgimgs=[]
    fpath,fname=os.path.split(path)
    contents=read(path)
    settings=contents["settings"]
    bgimg=settings["bgImage"]
    if bgimg!="" and bgimg not in bgimgs:
        bgimgs.append(bgimg)
    actions=contents["actions"]
    for action in actions:
        if action["eventType"]=="CustomBackground":
            bgimg=action["bgImage"]
            if bgimg!="" and bgimg not in bgimgs:
                bgimgs.append(bgimg)
    for bgimg in bgimgs:
        shutil.copy(fpath+'\\'+bgimg,"./output")

def get_game_duration(path):
    contents=read(path)
    angleData=contents["angleData"]
    offset=contents['settings']['offset']
    actions=contents['actions']
    Twirlsdic={}
    bpmchangedic={}
    basebpm=contents['settings']['bpm']
    bpmchangedic[0]=basebpm
    pausedic={}
    holds={}
    multiplanets={0:2}
    for action in actions:
        if action['eventType']=='Twirl':
            Twirlsdic[action['floor']]=1
        if action['eventType']=='SetSpeed':
            # 没有更新SetSpeed的AngleOffset参数
            if action['speedType']=='Bpm':
                basebpm=bpmchangedic[action['floor']]=action['beatsPerMinute']
            else:
                basebpm=bpmchangedic[action['floor']]=basebpm*action['bpmMultiplier']
        if action['eventType']=='Pause':
            pausedic[action['floor']]=action['duration']
        if action['eventType']=='Hold':
            holds[action['floor']]=action['duration']
        if action['eventType']=='MultiPlanet':
            multiplanets[action['floor']]=3 if action['planets']=='ThreePlanets' else 2
    time=offset/1000
    totalfloor=len(angleData)
    reverse=1
    bpm=bpmchangedic[0]
    ball=2
    for i in range(1,totalfloor):
        if angleData[i-1]==999: angleData[i-1]=angleData[i-2]-180 # 中旋
        pause=0
        hold=0
        if i in Twirlsdic: reverse=-reverse # 旋转
        if i in multiplanets: ball=multiplanets[i] # 星球数变化
        angle=(reverse*(180+angleData[i-1]-angleData[i]))%360 if ball==2 else (reverse*(180+angleData[i-1]-angleData[i])-60)%360
        if i in bpmchangedic: bpm=bpmchangedic[i] # 变速
        if i in pausedic: pause=pausedic[i] # 暂停
        if angle<=0.01: angle=360 # 如果算出在[0,0.01]度就是发卡弯360度
        if angleData[i]==999: continue # 中旋方块直接跳过
        if i in holds:
            hold=holds[i] # 长按
        time+=(angle+180*(pause+hold*2))/bpm/3
    return time

def get_wav_duration(filepath):
    with contextlib.closing(wave.open(filepath, 'r')) as f:
        frames=f.getnframes()
        rate=f.getframerate()
        duration=frames/float(rate)
    return duration
breaktime=get_wav_duration("./actualbreak.wav")

def chart_combine(path1,path2,first):
    content1=read(path1)
    content2=read(path2)
    n=len(content1["angleData"])
    lastangle=content1["angleData"][-1]
    if lastangle==999: lastangle=(content1["angleData"][-2]-180)%360
    angleData=content1["angleData"]+content2["angleData"]
    bpm=content1["settings"]["bpm"]
    Twirl=0
    ball=2
    endactions=[]
    for i,action in enumerate(content1["actions"]):
        if action["eventType"]=="Twirl":
            Twirl^=1
            if action["floor"]==n:
                Twirl^=1
                endactions.append(i)
        elif action["eventType"]=="SetSpeed":
            if action["speedType"]=="Bpm": bpm=action["beatsPerMinute"]
            else: bpm*=action["bpmMultiplier"]
            if action["floor"]==n: endactions.append(i)
        elif action["eventType"]=="MultiPlanet":
            if action["floor"]==n and action["planets"]=="ThreePlanets": endactions.append(i)
            else: ball=3 if action["planets"]=="ThreePlanets" else 2
        elif action["floor"]==n: endactions.append(i)
    
    # 合并音乐
    fpath1,fname1=os.path.split(path1)
    aname1=content1["settings"]["songFilename"]
    apath1=fpath1+'\\'+aname1
    a1=wav_converter(apath1)
    a1.export("./output/audio1.wav",format="wav")
    fpath2,fname2=os.path.split(path2)
    aname2=content2["settings"]["songFilename"]
    apath2=fpath2+'\\'+aname2
    a2=wav_converter(apath2)
    if ab==None:
        Audio=a1+a2
    else:
        Audio=a1+ab+a2
    if os.path.exists("./output/audio.wav"): os.remove("./output/audio.wav")
    Audio.export("./output/audio.wav",format="wav")
    
    # 处理结尾的其他事件：直接删除
    while endactions:
        i=endactions.pop()
        del content1["actions"][i]

    # 看要不要在结尾放旋转
    if Twirl:
        content1["actions"].append({"floor":n,"eventType":"Twirl"})
    
    # 在结尾变速为后一个关卡的基础BPM并利用暂停节拍实现停顿
    angle=(180+lastangle)%360 if ball==2 else (120+lastangle)%360
    if angle<=0.01: angle=360
    breakduration=breaktime+content2["settings"]["offset"]/1000+get_wav_duration("./output/audio1.wav")-get_game_duration(path1)
    # time=angle/180*60/bpm=angle/bpm/3
    # angle=3*time*bpm
    # bpm=angle/time/3
    bpm=content2["settings"]["bpm"]
    breakangle=bpm*3*breakduration
    pausebeats=(breakangle-angle)/180
    countdownTicks=content2["settings"]["countdownTicks"]
    content1["actions"].append({"floor":n,"eventType":"SetSpeed","speedType":"Bpm","beatsPerMinute":bpm,"bpmMultiplier":1,"angleOffset":0})
    content1["actions"].append({"floor":n,"eventType":"Pause","duration":pausebeats,"countdownTicks":countdownTicks,"angleCorrectionDir":-1})
    if os.path.exists("./output/audio1.wav"): os.remove("./output/audio1.wav")

    # 如果结尾为三球那就转为双球
    if ball==3: content1["actions"].append({"floor":n,"eventType":"MultiPlanet","planets":"TwoPlanets"})
    
    # 在结尾关闭滤镜绽放镜厅等效果
    # 关闭闪光
    content1["actions"].append({"floor":n,"eventType":"Flash","duration":0,"plane":"Background","startColor":"000000","startOpacity":0,"endColor":"000000","endOpacity":0,"angleOffset":0,"ease":"Linear","eventTag":""})
    content1["actions"].append({"floor":n,"eventType":"Flash","duration":0,"plane":"Foreground","startColor":"000000","startOpacity":0,"endColor":"000000","endOpacity":0,"angleOffset":0,"ease":"Linear","eventTag":""})
    # 关闭滤镜
    content1["actions"].append({"floor":n,"eventType":"SetFilter","filter":"Grayscale","enabled":False,"intensity":100,"duration":0,"ease":"Linear","disableOthers":True,"angleOffset":0,"eventTag":""})
    # 关闭绽放
    content1["actions"].append({"floor":n,"eventType":"Bloom","enabled":False,"threshold":50,"intensity":100,"color":"ffffff","duration":0,"ease":"Linear","angleOffset":0,"eventTag":""})
    # 关闭镜厅
    content1["actions"].append({"floor":n,"eventType":"HallOfMirrors","enabled":False,"angleOffset":0,"eventTag":""})
    # 关闭screentile
    content1["actions"].append({"floor":n,"eventType":"ScreenTile","duration":0,"tile":[1,1],"angleOffset":0,"ease":"Linear","eventTag":""})
    # 关闭ScreenScroll
    content1["actions"].append({"floor":n,"eventType":"ScreenScroll","scroll":[0,0],"angleOffset":0,"eventTag":""})
    # 设置判定区间与星球半径星球大小轨道大小透明度等初始化
    content1["actions"].append({"floor":n,"eventType":"ScaleMargin","scale":100})
    content1["actions"].append({"floor":n,"eventType":"ScaleRadius","scale":100})
    content1["actions"].append({"floor":n,"eventType":"ScalePlanets","duration":0,"targetPlanet":"All","scale":100,"angleOffset":0,"ease":"Linear","eventTag":""})
    
    # 隐藏之前的所有砖块
    content1["actions"].append({"floor":n,"eventType":"MoveTrack","startTile":[-n,"ThisTile"],"endTile":[-1,"ThisTile"],"gapLength":0,"duration":0,"positionOffset":[None,None],"opacity":0,"angleOffset":0,"ease":"Linear","eventTag":""})

    # 将后一个关卡的设定写为第零个砖块上的事件（即上一个关卡的最后一个砖块）
    settings=content2["settings"]
    # 打击音
    hitsound=settings["hitsound"]
    hitsoundVolume=settings["hitsoundVolume"]
    content1["actions"].append({"floor":n,"eventType":"SetHitsound","gameSound":"Hitsound","hitsound":hitsound,"hitsoundVolume":hitsoundVolume})
    # 轨道样式
    trackColorType=settings["trackColorType"]
    trackColor=settings["trackColor"]
    secondaryTrackColor=settings["secondaryTrackColor"]
    trackColorAnimDuration=settings["trackColorAnimDuration"]
    trackColorPulse=settings["trackColorPulse"]
    trackPulseLength=settings["trackPulseLength"]
    trackStyle=settings["trackStyle"]
    trackTexture=settings.get("trackTexture","")
    trackTextureScale=settings.get("trackTextureScale",1)
    trackGlowIntensity=settings.get("trackGlowIntensity",100)
    floorIconOutlines=settings.get("floorIconOutlines",False)
    content1["actions"].append({"floor":n,"eventType":"ColorTrack","trackColorType":trackColorType,"trackColor":trackColor,"secondaryTrackColor":secondaryTrackColor,"trackColorAnimDuration":trackColorAnimDuration,"trackColorPulse":trackColorPulse,"trackPulseLength":trackPulseLength,"trackStyle":trackStyle,"trackTexture":trackTexture,"trackTextureScale":trackTextureScale,"trackGlowIntensity":trackGlowIntensity,"floorIconOutlines":floorIconOutlines})
    # 粘性方块
    stickToFloors=settings["stickToFloors"]
    content1["actions"].append({"floor":n,"eventType":"PositionTrack","positionOffset":[0,0],"relativeTo":[0,"ThisTile"],"rotation":0,"scale":100,"opacity":100,"justThisTile":False,"editorOnly":False,"stickToFloors":stickToFloors})
    # 轨道动画
    trackAnimation=settings["trackAnimation"]
    beatsAhead=settings["beatsAhead"]
    trackDisappearAnimation=settings["trackDisappearAnimation"]
    beatsBehind=settings["beatsBehind"]
    content1["actions"].append({"floor":n,"eventType":"AnimateTrack","trackAnimation":trackAnimation,"beatsAhead":beatsAhead,"trackDisappearAnimation":trackDisappearAnimation,"beatsBehind":beatsBehind})
    content1["actions"].append({"floor":n,"eventType":"PositionTrack","positionOffset":[0,0],"relativeTo":[0,"ThisTile"],"rotation":0,"scale":100,"opacity":100,"justThisTile":False,"editorOnly":False,"stickToFloors":True})
    # 设置背景
    backgroundColor=settings["backgroundColor"]
    bgImage=settings["bgImage"]
    bgImageColor=settings["bgImageColor"]
    parallax=settings["parallax"]
    bgDisplayMode=settings["bgDisplayMode"]
    imageSmoothing=settings.get(True,"imageSmoothing")
    lockRot=settings["lockRot"]
    loopBG=settings["loopBG"]
    scalingRatio=settings.get("scalingRatio",settings.get("unscaledSize",100))
    if "unscaledSize" in settings: del settings["unscaledSize"]
    content1["actions"].append({"floor":n,"eventType":"CustomBackground","color":backgroundColor,"bgImage":bgImage,"imageColor":bgImageColor,"parallax":parallax,"bgDisplayMode":bgDisplayMode,"imageSmoothing":imageSmoothing,"lockRot":lockRot,"loopBG":loopBG,"scalingRatio":scalingRatio,"angleOffset":0,"eventTag":""})
    # 摄像头设置
    relativeTo=settings["relativeTo"]
    position=settings["position"]
    rotation=settings["rotation"]
    zoom=settings["zoom"]
    content1["actions"].append({"floor":n,"eventType":"MoveCamera","duration":0,"relativeTo":relativeTo,"position":position,"rotation":rotation,"zoom":zoom,"angleOffset":0,"ease":"Linear","eventTag":""})
    # 设置星球轨道
    planetEase=settings["planetEase"]
    planetEaseParts=settings["planetEaseParts"]
    planetEasePartBehavior=settings.get("planetEasePartBehavior","Mirror")
    content1["actions"].append({"floor":n,"eventType":"SetPlanetRotation","ease":planetEase,"easeParts":planetEaseParts,"easePartBehavior":planetEasePartBehavior})

    # 对后一个关卡的事件进行处理
    startbpm=content2["settings"]["bpm"]
    bpmchanged=False
    for action in content2["actions"]:
        # 处理后一个关卡开头的变速
        if action["floor"]==1 and action["eventType"]=="SetSpeed":
            bpmchanged=True
            if action["speedType"]=="Multiplier":
                action["beatsPerMinute"]=content2["settings"]["bpm"]*action["bpmMultiplier"]
                action["speedType"]="Bpm"
        # 把后一个关卡的所有事件砖块数加n
        action["floor"]+=n
    if not bpmchanged:
        content1["actions"].append({"floor":n+1,"eventType":"SetSpeed","speedType":"Bpm","beatsPerMinute":startbpm,"bpmMultiplier":1,"angleOffset":0})
    
    # 合并事件
    actions=content1["actions"]+content2["actions"]
    actions.sort(key=lambda x:x["floor"])

    # 合并装饰
    decorations=[]
    if "decorations" in content1:
        decorations=content1["decorations"]
    if "decorations" in content2:
        for decoration in content2["decorations"]:
            if "floor" in decoration: decoration["floor"]+=n
        decorations+=content2["decorations"]

    # 更新设置内容
    settings=content1["settings"]
    settings["songFilename"]="audio.wav"
    settings["version"]=13
    settings["speedTrialAim"]=settings.get("speedTrialAim",0)
    settings["trackTexture"]=settings.get("trackTexture","")
    settings["trackTextureScale"]=settings.get("trackTextureScale",1)
    settings["showDefaultBGTile"]=settings.get("showDefaultBGTile",True)
    settings["defaultBGTileColor"]=settings.get("defaultBGTileColor","101121")
    settings["defaultBGShapeType"]=settings.get("defaultBGShapeType","Default")
    settings["defaultBGShapeColor"]=settings.get("defaultBGShapeColor","ffffff")
    settings["imageSmoothing"]=settings.get("imageSmoothing",True)
    scalingRatio=settings.get("scalingRatio",settings.get("unscaledSize",100))
    if "unscaledSize" in settings: del settings["unscaledSize"]
    if "startCamLowVFX" in settings: del settings["startCamLowVFX"]
    if "customClass" in settings: del settings["customClass"]
    settings["defaultTextColor"]=settings.get("defaultTextColor","ffffff")
    settings["defaultTextShadowColor"]=settings.get("defaultTextShadowColor","00000050")
    settings["congratsText"]=settings.get("congratsText","")
    settings["perfectText"]=settings.get("perfectText","")

    # 写为json格式
    content={"angleData":angleData,"settings":settings,"actions":actions,"decorations":[]}
    new_content=json.dumps(content,indent=4)
    new_path="./output/combined.adofai"
    filen=open(new_path,'w',encoding='utf-8')
    print(new_content,file=filen)
    filen.close()

# 先删除output文件夹，并新建output文件夹
if os.path.exists("./output/"): shutil.rmtree("./output/")
os.makedirs("./output/")

# 逐个输入关卡文件并进行合并
path1=input('请输入第1个关卡文件地址: ').strip('\"')
copy_bgimg(path1)
first=True
for i in range(N-1):
    path2=input(f'请输入第{i+2}个关卡文件地址: ').strip('\"')
    copy_bgimg(path2)
    chart_combine(path1,path2,first)
    first=False
    path1="./output/combined.adofai"
os.remove("./actualbreak.wav")

# 压缩音频
contents=read("./output/combined.adofai")
contents["settings"]["songFilename"]="audio.ogg"
contents["settings"]["artist"]="<size=50>Various Artists"
contents["settings"]["song"]=f"<color=#FF0000>{input('请输入合并曲名: ')}</color></size>"
contents["settings"]["author"]=""
song=AudioSegment.from_wav("./output/audio.wav")
song.export("./output/audio.ogg",'ogg')
os.remove("./output/audio.wav")
f=open("./output/combined.adofai",'w')
print(json.dumps(contents,indent=4),file=f)
f.close()

print('已合并完成. ')
