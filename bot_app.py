import random
import collections
import os
import errno
import sys
import tempfile
import json
import logging
import stat
import subprocess
import cv2
import numpy as np
from argparse import ArgumentParser
from Timelette_Dashboard import Timelette_dashboard

from flask import Flask, request, abort, send_from_directory
#from redis

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, JoinEvent,TextMessage, TextSendMessage,
    SourceGroup, SourceRoom , ImageMessage, VideoMessage,
    ImageSendMessage,VideoSendMessage, AudioMessage, FileMessage
)


app = Flask(__name__)
line_bot_api=LineBotApi('x34a7IXDiPgbuU0YLQhCe5WGzT9DCFMHACvKrSCNoJA5maSLzVqogSbpjumayFfkxcGDTBdF/4VxTcztsp7Z7BriRQkeESG53a3/qrg6SCulOr+lSdVDu5p5264lV2+q+HH2GptE1iDKyvT1qwXRqH6Nfd2Y6SKCxBWg7Cr7O3c=')
handler = WebhookHandler('7449a2dc2533901914c08257df138916')

''''
def make_black_image():
    file_path = os.path.join(static_path,"basic","black.jpg")
    black_image = np.zeros((950,525,3),np.uint8)
    black_image = cv2.cvtColor(black_image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(file_path, black_image)
'''
#static img path
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
#make_black_image()
basic = {"basic_path": os.path.join(static_path,"basic"),
        "introduce":["introduce0.jpg","introduce1.jpg","introduce2.jpg"]
        ,"intro": {"type":"basic_intro","ext":"mp4", "duration":2, "cur_sp":0, "L":"L_basic_intro.mp4","P":"P_basic_intro.mp4"}
        ,"ending": {"type":"basic_ending","ext":"mp4", "duration":2, "cur_sp":0, "L":"L_basic_ending.mp4","P":"P_basic_ending.mp4"}
        ,"audio": {"emotional":"mp3_emotional.mp3","extreme":"mp3_extreme.mp3","happy":"mp3_happy.mp3"}
        }

if not os.path.isdir(static_path) :
    os.makedirs(static_path)

def get_instance_id(event):
    if isinstance(event.source, SourceGroup):
         return event.source.group_id
    elif isinstance(event.source, SourceRoom):
        return event.source.room_id
    else:
        return event.source.user_id

def get_timestamp(event):
    return event.timestamp

def make_room_name(event):
    room_name = get_instance_id(event) +'_'+ str(get_timestamp(event))
    return room_name

def Is_room_name(event):
    room_name_list = os.listdir(static_path)
    instance_id = get_instance_id(event)
    cand =  [room_name for room_name in room_name_list if instance_id+'_' in room_name]
    if len(cand) == 0 :
        return None
    else :
        f = lambda x : int(x.split('_')[1])
        max_stamp = max(map(f,cand))
        room_name = instance_id + '_' + str(max_stamp)

        with open(os.path.join(static_path,room_name,"room_info.json")) as infile:
            room_info = json.load(infile,object_pairs_hook=collections.OrderedDict)
        if room_info["Isexpired"] == True:
            return None
        else :
            return room_name

def get_room_name(event):
    room_name = Is_room_name(event)
    if room_name is None:
        room_name = make_static_room_dir(event)
        return room_name
    else :
        return room_name


def make_static_room_dir(event):
    sys.stdout.write("enter make_room_dir\n")
    try:
        sys.stdout.write("create room dir\n")
        room_name = make_room_name(event)
        os.makedirs(os.path.join(static_path,room_name))
        os.makedirs(os.path.join(static_path,room_name,"imgs"))
        os.makedirs(os.path.join(static_path,room_name,"manifests"))
        os.makedirs(os.path.join(static_path,room_name,"clips"))
        os.makedirs(os.path.join(static_path,room_name,"results"))

        room_info = {"Isexpired":False,"intro":basic["intro"], "ending":basic["ending"],
                "all_files":collections.OrderedDict(), "all_clips":{},"num_manifest_files":0, "cur_manifest": -1 , "room_path": os.path.join(static_path,room_name)}
        with open(os.path.join(static_path,room_name,"room_info.json"),'w') as outfile:
            json.dump(room_info,outfile)
        print "all_files type", type(room_info["all_files"])
        return room_name

    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_path):
            sys.stdout.write("pass\n")
            pass
        else:
            sys.stdout.write("raise\n")
            raise

def reply_result_video(my_instance_id, reply_token ,room_info, my_cur_info):

    print "result_file : ", my_cur_info["result_file"]
    result_file_url = my_cur_info["result_file"].split("hello_bot/")[1]
    print "result_file_url = ",result_file_url

    if room_info["all_files"][my_cur_info["all_data_names"][0]]['ext'] == 'jpg':
        pre_view = room_info["all_files"][my_cur_info["all_data_names"][0]][my_cur_info["fm"]]
        print "jpg"
    else :
        print room_info["all_files"][my_cur_info["all_data_names"][0]]['iconic']
        pre_view = room_info["all_files"][my_cur_info["all_data_names"][0]]['iconic'][my_cur_info["fm"]]
        print "mp4"

    room_path = room_info["room_path"].split("hello_bot/")[1]
    preview_image_url = os.path.join(room_path,'imgs',pre_view)
    print "result : ", result_file_url
    print "preview : ",preview_image_url
    line_bot_api.push_message(my_instance_id, VideoSendMessage(
        original_content_url="https://intern-bot.line-apps-beta.com:443/"+result_file_url ,
        preview_image_url="https://intern-bot.line-apps-beta.com:443/"+preview_image_url))

def reply_text(reply_token, msg):
    line_bot_api.reply_message(reply_token,TextSendMessage(text=msg))


def push_img(instance_id, room_path ,file_name_list):
    
    room_path = room_path.split("hello_bot/")[1]
    
    send_list = []
    for file_name in file_name_list:
        img_url_path = os.path.join("https://intern-bot.line-apps-beta.com:443/",room_path,file_name)
        send_list.append(ImageSendMessage(original_content_url= img_url_path,
            preview_image_url = img_url_path))
    
    line_bot_api.push_message(instance_id,send_list)


 #fm is only one char like 'L''P'
def get_clip_info(room_info, my_cur_info):
    
    intro_file_name =  room_info['intro']["type"]
    ending_file_name = room_info['ending']["type"]
    all_files =  room_info["all_files"]
    fm = my_cur_info["fm"]
    p_s = my_cur_info["p_s"]
    ts_t = my_cur_info["ts_t"]
    ts = my_cur_info["ts"]
    picked_data_names = list (my_cur_info["all_data_names"][:my_cur_info["numimg"]])

    clip_info = {}
    picked_data_names.insert(0,intro_file_name)
    picked_data_names.append(ending_file_name)

    for i in range(len(picked_data_names)):
        fm_s = '960x540' if fm == 'L' else '540x960'
        clip = {"p_s":p_s, "ts_t":ts_t, 'ts':ts, 'fm':fm_s}
       

        if i == len(picked_data_names)-1:
            if "basic" in picked_data_names[i]:
                start_info = basic["ending"]
            clip["start"] = start_info[fm]
            clip["type"] = 'end'
            clip["p_s"] = start_info["duration"]
            clip["start_v_sp"]= start_info["cur_sp"]
            clip["ts_t"] = 0
            clip["ts"] = None

        else : 
            if i == 0 and 'basic' in picked_data_names[i] :
                start_info = basic["intro"]
            else :
                start_info = all_files[picked_data_names[i]] 

            end_info = all_files[picked_data_names[i+1]] if not "basic" in picked_data_names[i+1] else basic["ending"]
            if start_info['ext']== 'jpg':
                clip["type"] = 'i'
            elif start_info['ext']== 'mp4':
                clip["p_s"] = start_info["duration"] - clip["ts_t"]
                clip["start_v_sp"] = start_info["cur_sp"]
                clip["type"] = 'v'
                if'basic' in picked_data_names[i] :
                    clip["p_s"] = start_info["duration"]
    
            if end_info['ext']== 'jpg':
                clip["type"] += 'i'
            elif end_info['ext']=='mp4':
                clip["end_v_sp"] = end_info["cur_sp"]
                clip["type"] += 'v'
    
        clip["start"] = start_info[fm]
        clip["end"] = end_info[fm]

        clip_info[i] = clip
    return clip_info 

def check_arg(arg,reply_token,min=None, max=None, checklist=None,checktype=None):
    if checktype == 'integer':
        if not arg.isdigit():
            reply_text(reply_token,"arg is not integer or negative number")
            
            return None
        else :
            arg = int(arg)
            if (min is not None and min > arg) or (max is not None and max < arg):
                reply_text(reply_token,"please check argument range")
                return None
            else :
                return int(arg)
    
    if checktype == 'string':
        arg = str(arg)
        if checklist is not None:
            if arg not in checklist:
                reply_text(reply_token,"please enter right argument")
                return None
            else :
                return arg
        return arg

def save_manifest(room_info,my_cur_info):
    room_path = room_info["room_path"]
    cur_manifest = room_info["cur_manifest"] 

    print "[save_manifest!!!!!!!!!!!]" + str(cur_manifest)
    with open(os.path.join(room_path, "manifests",
                           "manifest_" + str(cur_manifest) + ".json"), 'w') as mani_f:
        json.dump(my_cur_info, mani_f,indent=2)

def save_room_info(room_info):
    room_path = room_info["room_path"]

    if room_info["num_manifest_files"]<=room_info["cur_manifest"]+1 :
        room_info["num_manifest_files"] = room_info["num_manifest_files"] + 1

    with open(os.path.join(room_path,"room_info.json"),'w+') as info_f:
        json.dump(room_info,info_f,indent=2)

def get_iconic_image(room_info, file_name):
    print room_info
    file_path = os.path.join(room_info["room_path"],"imgs",file_name)
    new_iconic = os.path.join(room_info["room_path"],"imgs",'i_'+file_name[:-3]+'jpg')
    cmd = ["sudo","ffmpeg","-y","-i",file_path, "-vf","select=eq(n\,0)", "-q:v","3",new_iconic]
    subprocess.call(cmd)
    return os.path.basename(new_iconic)

def resize(room_info, my_cur_info,cur_sp=0):
    room_path = room_info["room_path"]
    all_files = room_info["all_files"]
    fm = my_cur_info["fm"]
    p_s = my_cur_info["p_s"]+my_cur_info["ts_t"]
    
    size = ['960','540'] if fm == 'L' else ['540','960']
    print all_files

    for file_name in all_files:
        cur_file_info = all_files[file_name]
        print cur_file_info
        if not fm in cur_file_info:
            ori_file_path = os.path.join(room_path,'imgs',file_name)
            new_file_path = os.path.join(room_path,'imgs',fm+'_'+file_name)
            if cur_file_info["ext"]== "mp4":
                subprocess.call(['ffmpeg','-y','-i', ori_file_path, '-vf', 'scale='+size[0]+':'+size[1]
                    +':force_original_aspect_ratio=decrease,pad='+size[0]+':'+size[1]+':(ow-iw)/2:(oh-ih)/2', "-c:v","libx264",
                    "-preset","veryslow","-profile:v","main","-crf","18","-c:a","copy",new_file_path])
            else :
                subprocess.call(['ffmpeg','-y', '-i', ori_file_path, '-vf', 'scale='+size[0]+':'+size[1]
                    +':force_original_aspect_ratio=decrease,pad='+size[0]+':'+size[1]+':(ow-iw)/2:(oh-ih)/2', new_file_path])
            os.chmod(new_file_path,0o777)
            all_files[file_name][fm] = os.path.basename(new_file_path) 

            if cur_file_info["ext"]== 'mp4' and cur_file_info["iconic"][fm] is None:
                all_files[file_name]['iconic'][fm] = get_iconic_image(room_info, all_files[file_name][fm])
        
       # if cur_file_info['ext'] == 'mp4':
        #    if cur_file_info['duration'] > p_s and cur_sp < cur_file_info['duration']-1 and cur_sp >= 0:
         #       all_files[file_name]['cur_sp'] = cur_sp
    print all_files

def get_string_clip_info(clip_info):

    start = clip_info['start'] if 'start' in clip_info else None
    end = clip_info['end'] if 'end' in clip_info else None
    _type = clip_info['type'] if 'type' in clip_info else None
    fm = clip_info['fm'] if 'fm' in clip_info else None
    p_s = clip_info['p_s'] if 'p_s' in clip_info else None
    ts_t = clip_info['ts_t'] if 'ts_t' in clip_info else None
    ts = clip_info['ts'] if 'ts' in clip_info else None
    start_v_sp = clip_info['start_v_sp'] if 'start_v_sp' in clip_info else None
    end_v_sp = clip_info['end_v_sp'] if 'end_v_sp' in clip_info else None
    
    clip_info_str = " ".join(str(e) for e  in (start, end, _type, fm ,p_s, ts_t, ts, start_v_sp, end_v_sp))
    return clip_info_str
    

def make_clip(room_info, my_cur_info):
    
    room_path = room_info["room_path"]
    all_clips = room_info["all_clips"]
    clip_info = my_cur_info["clip_info"]
    cur_manifest = str(room_info["cur_manifest"])

    for i in clip_info.keys():
        print "cur_clip :", clip_info[i]
        if get_string_clip_info(clip_info[i]) in all_clips:
            
            print "all_clips exist", get_string_clip_info(clip_info[i])
            clip_info[i]['clip_file'] = all_clips[get_string_clip_info(clip_info[i])]
            continue
        
        cmd_list = ['sudo','ffmpeg','-y']

        pre_clip = clip_info[i-1] if i > 0  else None
        cur_clip = clip_info[i]

        if cur_clip['type'] == 'end':
            print "[make_clip] end "
            file_path = os.path.join(room_path,'imgs',cur_clip['start']) if not "basic" in cur_clip['start'] else os.path.join(static_path, 'basic', cur_clip['start'])
            
            cmd = ['sudo','cp',file_path, os.path.join(room_path,'clips',cur_manifest+'_end.mp4')]
            print cmd 
            subprocess.call(cmd)
            clip_info[i]['clip_file'] = os.path.join(room_path,'clips',cur_manifest+'_end.mp4')
            os.chmod(clip_info[i]['clip_file'],0o777)
            print  clip_info[i]
            break
        
        else :
            if cur_clip['type'][0] == 'i':
                tmp_list = ['-loop','1','-t',str(cur_clip['p_s']),'-i', os.path.join(room_path,'imgs',cur_clip['start'])]
                if pre_clip is None:
                    tmp_list[3] = str(cur_clip['ts_t'])
                cmd_list = cmd_list + tmp_list
            
            elif cur_clip['type'][0] == 'v':
                print "ISbasic" , "basic" in cur_clip['start']
                file_path = os.path.join(room_path,'imgs',cur_clip['start']) if not "basic" in cur_clip['start'] else os.path.join(static_path,'basic',cur_clip['start'])
            
                ts_t = cur_clip['ts_t'] if int(i) > 0 else 0
                tmp_list = ['-ss',str(cur_clip['start_v_sp'] + ts_t),'-t',str(cur_clip['p_s']),'-i',file_path]
                if pre_clip is None:
                    tmp_list[1] = str(cur_clip['start_v_sp'])
                    #tmp_list[3] = str(cur_clip['ts_t'])
                cmd_list = cmd_list + tmp_list
        
            if cur_clip['type'][1] == 'i':
                tmp_list = ['-loop','1','-t',str(cur_clip['ts_t']),'-i',os.path.join(room_path,'imgs',cur_clip['end'])]
                cmd_list = cmd_list + tmp_list
            
            elif cur_clip['type'][1] == 'v':
                file_path = os.path.join(room_path,'imgs',cur_clip['end']) if not "basic" in cur_clip['end'] else os.path.join(static_path,'basic',cur_clip['end'])

                tmp_list = ['-ss',str(cur_clip['end_v_sp']),'-t',str(cur_clip['ts_t']),'-i', file_path]
                cmd_list = cmd_list + tmp_list
            
            clip_file_path = os.path.join(room_path,'clips',str(cur_manifest)+'_'+str(i)+'_clip.mp4')
            tmp_list = ['-f','lavfi', '-i', 'color=black', '-filter_complex' ,
                    '[0:v]fade=t=out:st='+ str(cur_clip['p_s']-cur_clip['ts_t']) + ':d=' + str(cur_clip['ts_t']) + ':alpha=1,setpts=PTS-STARTPTS[va0]; '+
                    '[1:v]fade=t=in:st=0:d='+ str(cur_clip['ts_t']) +':alpha=1,setpts=PTS-STARTPTS+'+str(cur_clip['p_s']-cur_clip['ts_t']) +'/TB[va1]; '+
                    '[2:v]scale=' + cur_clip['fm'] + ',trim=duration=' + str(cur_clip['p_s']) +',setsar=1[over]; '+
                    '[over][va0]overlay[over1]; [over1][va1]overlay[outv]', '-map', '[outv]']
            
            if cur_clip['type'][0] == 'v':
                tmp_list.append("-map")
                tmp_list.append("0:a")
           
            add_list = ["-b:v","1258291"]
                    #"-c:v","libx264","-vprofile","baseline"]

            tmp_list = tmp_list + add_list

            tmp_list.append(clip_file_path)
            cmd_list = cmd_list + tmp_list
            
            print " ".join(cmd_list)
            subprocess.call(cmd_list)

            if cur_clip['type'][0] == 'i':
                new_clip_file_path = os.path.join(room_path,'clips','_'+str(cur_manifest)+'_'+str(i)+'_clip.mp4')
                cmd  = ["sudo", "ffmpeg", "-i",clip_file_path, "-f", "lavfi", "-i", "aevalsrc=0", "-shortest", "-y",new_clip_file_path]
                clip_file_path = new_clip_file_path
                print " ".join(cmd)
                subprocess.call(cmd)

            all_clips[get_string_clip_info(clip_info[i])] = clip_file_path
            clip_info[i]['clip_file'] = clip_file_path
            os.chmod(clip_info[i]['clip_file'],0o777)

            
def concat_clip(room_info, my_cur_info):
    room_path = room_info["room_path"]
    clip_info = my_cur_info["clip_info"]
    cur_manifest = room_info["cur_manifest"]
    
    file_path = os.path.join(room_path,'results',str(cur_manifest)+"_clip_file.txt")
    print "file_path",file_path
    concat_st = "concat:"

    f = open(file_path,mode = 'w')
    for i in range(len(clip_info)):
        data = "file '"+ clip_info[i]["clip_file"]+"'\n"
        f.write(data)
    f.close()

    result_path =os.path.join(room_path,'results',str(cur_manifest)+"_result.mp4") 
     
    cmd = ['sudo','ffmpeg','-y','-f','concat','-safe','0','-i',file_path,'-c:v','copy',"-c:a","libfdk_aac",result_path]
    cmd_str = " ".join(cmd)
    print " ".join(cmd)
    #subprocess.call(cmd_str, shell = True)
    subprocess.call(cmd)
    my_cur_info["result_file"] = result_path

    return

def merge_audio(room_info, my_cur_info):
    print "merge_audio!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    result_file_path = my_cur_info["result_file"]
    new_result_file_path = os.path.join(room_info["room_path"],"results","_"+os.path.basename(result_file_path))
    audio_type = my_cur_info["music"]
    audio_path = os.path.join(basic["basic_path"],basic["audio"][audio_type])
    result_d = get_video_duration(result_file_path)
    fade_d = 2
    print "merge_audio"
    cmd = ["sudo","ffmpeg","-y","-i",result_file_path,"-i",audio_path,"-filter_complex",
            "[0:a][1:a]amix=inputs=2,dynaudnorm[mix];[mix]afade=t=in:st=0:d="+str(fade_d)+",afade=t=out:st="+str(result_d-fade_d)+":d="+str(fade_d),"-shortest",new_result_file_path]
    print " ".join(cmd)
    subprocess.call(cmd)
    my_cur_info["result_file"]= new_result_file_path
    #subprocess.call(["sudo","mv", new_result_file_path, result_file_path])

def make_result_video_dash(room_info,my_cur_info,timestamp):
    
    concat_clip(room_info,my_cur_info)
    merge_audio(room_info,my_cur_info)

    dash = Timelette_dashboard(room_info, my_cur_info, my_cur_info["fm"])
    my_cur_info = dash.make_dashboard(timestamp)
    print my_cur_info["dashboard"]

def send_result(my_instance_id, event, room_info, my_cur_info):
    reply_result_video(my_instance_id, event.reply_token, room_info, my_cur_info) 
    img_room_path = os.path.join(room_info["room_path"],"imgs")
    push_img(my_instance_id,img_room_path,my_cur_info["dashboard"])

def make_video(event) :
    my_instance_id = get_instance_id(event)
    my_room_name = get_room_name(event)
    msg_list = event.message.text.split(" ")[1:]
    print "msg_list" , msg_list

    with open(os.path.join(static_path,my_room_name,"room_info.json")) as infile:
        room_info = json.load(infile,object_pairs_hook=collections.OrderedDict)
    if len(room_info["all_files"]) == 0 :
        reply_text(event.reply_token,"you should upload midea files first")
        return

    room_info['cur_manifest'] = room_info['cur_manifest']+1
    my_cur_info = {"numimg": len(room_info["all_files"]), "music":"emotional","p_s": 2 ,"ts_t":0.5, "ts":'d' ,"clip_info":collections.OrderedDict(), "fm":'L',"all_data_names":[]}
    Israndom = 'T'


    if "numimg" in msg_list and len(msg_list) > msg_list.index("numimg")+1 :
        numimg = check_arg(msg_list[msg_list.index("numimg")+1],event.reply_token,min=1,max=len(room_info["all_files"]),checktype='integer') 
        if numimg is None : 
            return
        my_cur_info["numimg"] = numimg 
    if "per_sec" in msg_list and len(msg_list) > msg_list.index("per_sec")+1:
        p_s = check_arg(msg_list[msg_list.index("per_sec")+1],event.reply_token, min=1, max=20,checktype='integer')
        if p_s is None : 
            return
        my_cur_info["p_s"] = p_s 
    if "format" in msg_list and len(msg_list) > msg_list.index("format")+1:
        fm = check_arg(msg_list[msg_list.index("format")+1],event.reply_token, checklist=['L','P'],checktype='string')
        if fm is None : 
            return
        my_cur_info["fm"] = fm 
    if "ts" in msg_list and len(msg_list) > msg_list.index("ts")+1:
        ts = check_arg(msg_list[msg_list.index("ts")+1],event.reply_token, checklist=['d'],checktype='string')
        if ts is None : 
            return
        my_cur_info["ts"] = ts 
    if "ts_t" in msg_list and len(msg_list) > msg_list.index("ts_t")+1:
        ts_t = check_arg(msg_list[msg_list.index("ts_t")+1],event.reply_token, min=1, max=my_cur_info['p_s'],checktype='integer')
        if ts_t is None : 
            return
        my_cur_info["ts_t"] = ts_t
    
    if "random" in msg_list and len(msg_list) > msg_list.index("random")+1:
        Israndom = check_arg(msg_list[msg_list.index("random")+1],event.reply_token,checklist=['T','F'],checktype='string')
        if Israndom is None :
            return

    if "music" in msg_list:
        music = check_arg(msg_list[msg_list.index("music")+1],event.reply_token,checklist=['happy','emotional','extreme'],checktype='string')
        if music is None : 
            return
        my_cur_info["music"] = music

    print "[make]resize to " + my_cur_info["fm"]
    resize(room_info, my_cur_info)
    
    print "Israndom : ",Israndom
    if Israndom == 'T':
        print "[make]picking data randomly"
        cand = room_info["all_files"].keys()
        print cand, "numimg ",my_cur_info["numimg"]
        picked_data_names = random.sample(cand , my_cur_info["numimg"])
        #picked_data_names = ["jpg-bOF_CD.jpg","mp4-8LT9BJ.mp4","jpg-SBca2Y.jpg"]
        print picked_data_names
    else :
        picked_data_names = room_info["all_files"].keys()[:my_cur_info["numimg"]]

    print "[make] make all_data_names for making dashboard"
    all_data_names = [i for i in room_info["all_files"] if not i in picked_data_names]
    all_data_names = picked_data_names + all_data_names
    my_cur_info["all_data_names"] = all_data_names
    
    print "[make] get clip info"
    my_cur_info["clip_info"] = get_clip_info(room_info, my_cur_info)

    print "[make] make clip video"
    make_clip(room_info, my_cur_info)
    print my_cur_info["clip_info"]

    make_result_video_dash(room_info,my_cur_info,get_timestamp(event))
    send_result(my_instance_id,event,room_info,my_cur_info)
    save_manifest(room_info, my_cur_info)
    save_room_info(room_info)

    print "[make] make whole video"
    print "DONE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    

    return


# del (img_number)
def delete_img (event) :
    print "[delete_img] strat"
    my_instance_id = get_instance_id(event)
    my_room_name = get_room_name(event)
    msg = event.message.text.split(" ")[1:]
   
    with open(os.path.join(static_path,my_room_name,"room_info.json")) as info_f:
        room_info = json.load(info_f,object_pairs_hook=collections.OrderedDict)
    with open(os.path.join(static_path,my_room_name,"manifests","manifest_"+ str(room_info["cur_manifest"])+".json")) as mani_f:
        my_cur_info = json.load(mani_f)
   
    if len(msg)> msg.index("del")+1:
        del_num = check_arg(msg[msg.index("del")+1],event.reply_token,min=1, max=my_cur_info["numimg"], checklist=None,checktype="integer")
        if del_num is None:
            return
        else :
            del_num -=1
    else :
        reply_text(event.reply_token, "del need index number of deleting image")
        return
   
    
    ori_del_name = my_cur_info["all_data_names"].pop(del_num)
    my_cur_info["all_data_names"].insert(my_cur_info["numimg"]-1,ori_del_name)
    my_cur_info["numimg"] = my_cur_info["numimg"]-1
    print "numimg :", my_cur_info["numimg"]

    room_info["cur_manifest"] += 1 

    print "get_clip_info"
    my_cur_info["clip_info"] = get_clip_info(room_info, my_cur_info)    

    print "[make] make clip video"
    make_clip(room_info, my_cur_info)
    print my_cur_info["clip_info"]
    
    make_result_video_dash(room_info,my_cur_info,get_timestamp(event))
    send_result(my_instance_id,event,room_info,my_cur_info)
    save_manifest(room_info, my_cur_info)
    save_room_info(room_info)

    return


# add front (standard_point) (img_number)
def add_img_front(event):
    print "[add_img] front strat"
    my_instance_id = get_instance_id(event)
    my_room_name = get_room_name(event)
    msg = event.message.text.split(" ")[1:]
    
    with open(os.path.join(static_path,my_room_name,"room_info.json")) as info_f:
        room_info = json.load(info_f,object_pairs_hook=collections.OrderedDict)
    with open(os.path.join(static_path,my_room_name,"manifests","manifest_"+ str(room_info["cur_manifest"])+".json")) as mani_f:
        my_cur_info = json.load(mani_f)
    
    if len(msg)> msg.index("front")+2:
        standard_point = check_arg(msg[msg.index("front")+1],event.reply_token,min=1, max=my_cur_info["numimg"], checklist=None,checktype="integer")
        img_num = check_arg(msg[msg.index("front")+2],event.reply_token,min=1, max=len(room_info["all_files"]), checklist=None,checktype="integer")
        if standard_point is None or img_num is None:
            return
        else :
            standard_point -=1
            img_num -=1
    else:
        reply_text(event.reply_token, "add need two index number as arg")
        return 

    ori_img_num = my_cur_info["all_data_names"].pop(img_num)
    my_cur_info["all_data_names"].insert(standard_point,ori_img_num)
    if img_num >= my_cur_info["numimg"]:
        my_cur_info["numimg"] = my_cur_info["numimg"] +1

    room_info["cur_manifest"] += 1 

    print "get_clip_info"
    picked_data_names = my_cur_info["all_data_names"][:my_cur_info["numimg"]]
    my_cur_info["clip_info"] = get_clip_info(room_info, my_cur_info)  
    print "clip_info type: ", type(my_cur_info["clip_info"])
    
    print "[make] make clip video"
    make_clip(room_info, my_cur_info)
    print my_cur_info["clip_info"]
    
    make_result_video_dash(room_info,my_cur_info,get_timestamp(event))
    send_result(my_instance_id,event,room_info,my_cur_info)
    save_manifest(room_info, my_cur_info)
    save_room_info(room_info)
    
    return

# add back (standard_point) (img_number)
def add_img_back(event):
    print "[add_img] back strat"
    my_instance_id = get_instance_id(event)
    my_room_name = get_room_name(event)
    msg = event.message.text.split(" ")[1:]

    with open(os.path.join(static_path,my_room_name,"room_info.json")) as info_f:
        room_info = json.load(info_f,object_pairs_hook=collections.OrderedDict)
    with open(os.path.join(static_path,my_room_name,"manifests","manifest_"+ str(room_info["cur_manifest"])+".json")) as mani_f:
        my_cur_info = json.load(mani_f)
    
    if len(msg)> msg.index("back")+2:
        standard_point = check_arg(msg[msg.index("back")+1],event.reply_token,min=1, max=my_cur_info["numimg"], checklist=None,checktype="integer")
        img_num = check_arg(msg[msg.index("back")+2],event.reply_token,min=1, max=len(room_info["all_files"]), checklist=None,checktype="integer")
        
        if standard_point is None or img_num is None:
            return
        else :
            standard_point -=1
            img_num -=1
    else:
        reply_text(event.reply_token, "add need two index number as arg")
        return


    ori_img_num = my_cur_info["all_data_names"].pop(img_num)
    my_cur_info["all_data_names"].insert(standard_point+1,ori_img_num)
    if img_num >= my_cur_info["numimg"]:
        my_cur_info["numimg"] = my_cur_info["numimg"] +1
    
    room_info["cur_manifest"] += 1 

    print "get_clip_info"
    picked_data_names = my_cur_info["all_data_names"][:my_cur_info["numimg"]]
    my_cur_info["clip_info"] = get_clip_info(room_info, my_cur_info)  
    print "clip_info : ", my_cur_info["clip_info"]

    print "[make] make clip video"
    make_clip(room_info, my_cur_info)
    print my_cur_info["clip_info"]
    
    make_result_video_dash(room_info,my_cur_info,get_timestamp(event))
    send_result(my_instance_id,event,room_info,my_cur_info)
    save_manifest(room_info, my_cur_info)
    save_room_info(room_info)
    return 

#replace (standard_point) (img_number)
def replace_img (event):
    print "[replace] strat"
    my_instance_id = get_instance_id(event)
    my_room_name = get_room_name(event)
    msg = event.message.text.split(" ")[1:]

    with open(os.path.join(static_path,my_room_name,"room_info.json")) as info_f:
        room_info = json.load(info_f,object_pairs_hook=collections.OrderedDict)
    with open(os.path.join(static_path,my_room_name,"manifests","manifest_"+ str(room_info["cur_manifest"])+".json")) as mani_f:
        my_cur_info = json.load(mani_f)
    
    if len(msg)> msg.index("replace")+2:
        standard_point = check_arg(msg[msg.index("replace")+1],event.reply_token,min=1, max=my_cur_info["numimg"], checklist=None,checktype="integer")
        img_num = check_arg(msg[msg.index("replace")+2],event.reply_token,min=1, max=len(room_info["all_files"]), checklist=None,checktype="integer")
        if standard_point is None or img_num is None:
            return
        else :
            standard_point -=1
            img_num -=1
    else:
        reply_text(event.reply_token, "replace need two index number as arg")
        return

    tmp = my_cur_info["all_data_names"][img_num]
    my_cur_info["all_data_names"][img_num] = my_cur_info["all_data_names"][standard_point]
    my_cur_info["all_data_names"][standard_point] = tmp

    room_info["cur_manifest"] += 1 

    print "get_clip_info"
    picked_data_names = my_cur_info["all_data_names"][:my_cur_info["numimg"]]
    my_cur_info["clip_info"] = get_clip_info(room_info, my_cur_info)  
    print "clip_info : ", my_cur_info["clip_info"]

    print "[make] make clip video"
    make_clip(room_info, my_cur_info)
    print my_cur_info["clip_info"]
    
    make_result_video_dash(room_info,my_cur_info,get_timestamp(event))
    send_result(my_instance_id,event,room_info,my_cur_info)
    save_manifest(room_info, my_cur_info)
    save_room_info(room_info)
    return 

def get_dashboard(event):
    print "get dashboard"
    my_instance_id = get_instance_id(event)
    my_room_name = get_room_name(event)
    
    with open(os.path.join(static_path, my_room_name, "room_info.json")) as info_f:
        room_info = json.load(info_f,object_pairs_hook=collections.OrderedDict)
    
    if room_info["cur_manifest"] < 0:
        reply_text(event.reply_token, "you need to do 'make' first")
        return
    
    with open(os.path.join(static_path,my_room_name,"manifests",
                           "manifest_" + str(room_info["cur_manifest"])+ ".json")) as mani_f:
        my_cur_info = json.load(mani_f)
    print "all_files:::::::", len(room_info["all_files"])

    resize(room_info,my_cur_info)
    dash = dashboard(room_info, my_cur_info, my_cur_info["fm"])
    my_cur_info = dash.make_dashboard(get_timestamp(event))
    
    img_room_path = os.path.join(room_info["room_path"],"imgs")
    push_img(my_instance_id,img_room_path,my_cur_info["dashboard"])
    save_manifest(room_info, my_cur_info)
    save_room_info(room_info)

def undo_manifest (event):
    print "[undo_manifest] strat"
    my_instance_id = get_instance_id(event)
    my_room_name = get_room_name(event)
    msg = event.message.text.split(" ")[1:]

    if len(msg)>1:
        num_undo = check_arg(msg[msg.index("undo")+1],event.reply_token,min=1, max=None, checklist=None,checktype="integer")
        if num_undo is None:
            return
    else :
        num_undo = 1

    with open(os.path.join(static_path, my_room_name, "room_info.json")) as info_f:
        room_info = json.load(info_f,object_pairs_hook=collections.OrderedDict)
    if room_info["cur_manifest"]- num_undo <0 :
        reply_text(event.reply_token,"No file to undo")
        return

    room_info["cur_manifest"] = room_info["cur_manifest"] - num_undo
    print room_info["cur_manifest"] 
    
    with open(os.path.join(static_path,my_room_name,"manifests",
                           "manifest_" + str(room_info["cur_manifest"])+ ".json")) as mani_f:
        my_cur_info = json.load(mani_f)
    
    send_result(my_instance_id,event,room_info,my_cur_info)
    save_room_info(room_info)
    return 

def redo_manifest (event):
    print "[undo_manifest] strat"
    my_instance_id = get_instance_id(event)
    my_room_name = get_room_name(event)
    msg = event.message.text.split(" ")[1:]

    if len(msg)>1:
        num_redo = check_arg(msg[msg.index("redo")+1],event.reply_token,min=1, max=None, checklist=None,checktype="integer")
        if num_redo is None:
            return
    else :
        num_redo = 1

    with open(os.path.join(static_path, my_room_name, "room_info.json")) as info_f:
        room_info = json.load(info_f,object_pairs_hook=collections.OrderedDict)

    print room_info["cur_manifest"] + num_redo , room_info["num_manifest_files"]

    if room_info["cur_manifest"] + num_redo >= room_info["num_manifest_files"]:
        reply_text(event.reply_token, "No file to redo")
        return

    room_info["cur_manifest"] = room_info["cur_manifest"] + num_redo
    print room_info["cur_manifest"] 
    with open(os.path.join(static_path,my_room_name,"manifests",
                           "manifest_" + str(room_info["cur_manifest"])+ ".json")) as mani_f:
        my_cur_info = json.load(mani_f)
    
    send_result(my_instance_id,event,room_info,my_cur_info)
    save_room_info(room_info)
    return 
def set_expired_room(event):
    my_room_name = get_room_name(event)
    with open(os.path.join(static_path, my_room_name, "room_info.json")) as info_f:
        room_info = json.load(info_f,object_pairs_hook=collections.OrderedDict)
    room_info["Isexpired"] = True
    save_room_info(room_info)

def exit(event):
    if isinstance(event.source, SourceGroup):
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text="Leaving Group"))
        set_expired_room(event)
        line_bot_api.leave_group(event.source.group_id)

    elif isinstance(event.source, SourceRoom):
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text="Leaving Room"))
        set_expired_room(event)
        line_bot_api.leave_room(event.source.room_id)
    else :
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text="hello_bot can't leave from 1:1 chat!"))
        set_expired_room(event)
        return
    #subprocess.call(["sudo","rm","-rf","static/"+get_room_name(event)])


@app.route("/monitor/l7check", methods=['HEAD'])
def check():
    return "OK"

@app.route("/static/<path:path>")
def send_file(path):
    return send_from_directory(static_path,path)



@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(JoinEvent)
def handle_join(event):
    
    push_img(get_instance_id(event),basic["basic_path"],basic["introduce"])



@handler.add(MessageEvent, message=TextMessage)
def handle_message(event): 
    print event.message.text
    if "@Timelette" != event.message.text.split(" ")[0] or len(event.message.text.split(" "))<=1:
        return

    commend = event.message.text.split(" ")
    if "make" == commend[1]: 
        if Is_room_name(event) is None:
            reply_text(event.reply_token,"you should upload media files first")

        sys.stdout.write("make img!!!!!!!!!!!!!!")
        make_video(event)
    elif "dashboard" == commend[1]:
        get_dashboard(event)
    
    elif "del" == commend[1]:
        delete_img(event)

    elif "add" == commend[1]:
        if len(commend) <= 2 :
            reply_text(event.reply_token, "add need more arg")
            return 
        else :
            if "back" == commend[2]:
                add_img_back(event)
            elif "front" == commend[2]:
                add_img_front(event)
            else :
                reply_text(event.reply_token, "you must use 'front' or 'back' as commend")
                return

    elif "replace" == commend[1]:
        replace_img(event)

    elif "undo" == commend[1]:
        undo_manifest(event)

    elif "redo" == commend[1]:
        redo_manifest(event)

    elif "exit" == commend[1]:
        exit(event)
    else :
        pass
        #line_bot_api.reply_message(event.reply_token,TextSendMessage(text=event.message.text))


def get_file_size(file_path):
    size = subprocess.check_output(['bash','CheckSize.sh',file_path])[:-1]
    print size
    size = map(int,size.split('x'))
    return size

def get_video_duration(file_path):
    d = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 
        'stream=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path])
    return float(d)

def file_save(room_path,msg_content,ext):

    with tempfile.NamedTemporaryFile(dir=os.path.join(room_path,"imgs"), prefix=ext+'-', delete=False) as tf:
        for chunk in msg_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    dist_path = tempfile_path + '.' + ext
    os.rename(tempfile_path,dist_path)
    os.chmod(dist_path,0o777)
    
    return dist_path

def add_file_info(room_path,dist_path,ext):
    
    with open(os.path.join(room_path,"room_info.json")) as loaded_file:
        room_info = json.load(loaded_file,object_pairs_hook=collections.OrderedDict)
    
    print "[add_file_info]all_files type ", type(room_info["all_files"])
    
    file_size = get_file_size(dist_path) 
    file_format = 'L' if file_size[0]>=file_size[1] else 'P'

    dist_name = os.path.basename(dist_path)

    tmp_tuple = (dist_name,)
    room_info["all_files"][dist_name] = {"ext":ext, "resolution":file_size, "format":file_format}
    cur_file_info = room_info["all_files"][dist_name]
   
    if ext =='mp4':
        cur_file_info["duration"] = get_video_duration(dist_path)
        cur_file_info["cur_sp"] = 0
        cur_file_info["iconic"] ={'L':None, 'P':None}
    print  "dist_name" ,dist_name
    print "all_files ", room_info["all_files"].keys()
    print  "all_files type", type(room_info["all_files"])
    with open(os.path.join(room_path,"room_info.json"), 'w+b') as outfile:
        json.dump(room_info, outfile) 

@handler.add(MessageEvent, message=AudioMessage)
def handle_audio_message(event):
    ext = "mp3"
    msg_content = line_bot_api.get_message_content(event.message.id)
    instance_id = get_instance_id(event)
  
    print "instance_id = " + instance_id
    room_path = os.path.join(static_path,get_room_name(event))
    #if not os.path.isdir(room_path):
    #    make_static_room_dir(instance_id)
    dist_path = file_save(room_path, msg_content, ext)


@handler.add(MessageEvent, message=FileMessage)
def handle_file_message(event): 
    
    msg_content = line_bot_api.get_message_content(event.message.id)
    
    with tempfile.NamedTemporaryFile(dir="./", prefix="png"+'-', delete=False) as tf:
        for chunk in msg_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    dist_path = tempfile_path + '.zip'
    os.rename(tempfile_path,dist_path)
    os.chmod(dist_path,0o777)

    reply_text(event.reply_token,"file")


@handler.add(MessageEvent, message=(ImageMessage, VideoMessage))

def handle_content_message(event):
    if isinstance(event.message, ImageMessage) :
        ext='jpg'
    elif isinstance(event.message, VideoMessage) :
        ext='mp4'
    else :
        return
 
    #instance_id = get_instance_id(event)
    room_name = get_room_name(event)
    msg_content = line_bot_api.get_message_content(event.message.id)
  
    print "room_name = ",room_name
    room_path = os.path.join(static_path,room_name)
    
    dist_path = file_save(room_path,msg_content,ext)
    add_file_info(room_path,dist_path,ext)

    
    dist_name = os.path.basename(dist_path)
    #line_bot_api.reply_message( event.reply_token, TextSendMessage(text=request.host_url + os.path.join(room_path,dist_name)))

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("Start RestAPI :  listen %s : %s"%('127.0.0.1','8443'))
    arg_parser = ArgumentParser(
        usage= 'Usage : python' + __file__ + '[--port <port>]  [--help]'
    )
    print "app run"
    app.run(host = '0.0.0.0', port =80, debug=True)

