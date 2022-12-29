#!/usr/bin/env python

import sys
import urllib3.request
import http.client
import os.path
import os
import datetime
import threading
import json

def fetch_play_lists(path, i, fetch_segments):
    file = open(path, 'r')
    grab_next_path = False
    for line in file:
        if line[0] == '#':
            parts = line.split(',')
            print(parts)
            for part in parts:
                if 'BANDWIDTH' in part:
                    bandwidth = part.split('=')[-1]
                    if int(bandwidth) > 1173000:
                        grab_next_path = True
            continue
        if grab_next_path == False:
            continue
        print(line)
        filedata = urlopen(line)
        datatowrite = filedata.read()
        play_list_file_name = os.path.dirname(path) + '/play-list.m3u8'
        with open(play_list_file_name, 'wb') as play_list:
            play_list.write(datatowrite)
        return play_list_file_name

def fetch_and_save_subtitles(url, path, index):
    subtitles_file_name = path + '/subtitles{}.xml'.format(index)
    if os.path.isfile(subtitles_file_name):
        return
    data = download(url)
    with open(subtitles_file_name, 'wb') as subtitles:
        subtitles.write(data)


def find_play_list(text):
    found = False
    for line in text.split('\n'):
        if line != '' and line[0] == '#':
            parts = line.split(',')
            print(parts)
            for part in parts:
                if 'BANDWIDTH' in part:
                    bandwidth = part.split('=')[-1]
                    if int(bandwidth) > 1173000:
                        found = True
                        break
            continue
        if found:
            return line
    return None

#https://b1rbsov.bidi.live.bbc.co.uk/vod-dash-uk/usp/auth/vod/piff_abr_full_sd_ad/8c218f-b093vffs/vf_b093vffs_40d52510-b5bf-43f9-89a5-db87acdb09b4.ism.hlsv2.ism/vf_m000qfgc_704e0e70-ab88-4efe-9ee8-35c53143d935.ism.hlsv2-audio_eng_1=128000-video=1570000.m3u8
def find_base_url(url):
    last_slash = url.rfind('/')
    return url[0:last_slash]

def download_json(url):
    return json.loads(download(url))

def download(url):
    http = urllib3.PoolManager()
    response = http.request('GET', url)
    return response.data
    
def fetch_play_list_from_url(url):
    retries = urllib3.util.Retry(connect=5, read=4, redirect=5)
    http = urllib3.PoolManager(retries=retries)
    response = http.request('GET', url)
    data = response.data      # a `bytes` object
    return data.decode('utf-8') # a `str`; this step can't be used if data is binary

def fetch_ts_segments(text, dir_name):
    if os.path.isfile(dir_name + 'list.txt'):
        return
    for line in text.split('\n'):
        if line == '' or line[0] == '#':
           continue
        segment_name = line.split('-')[-1]
        with open(dir_name + '/list.txt', 'a') as list:
            list.write("file '" + segment_name + "'")
            list.write("\n")
        continue

def download_ts_segment(url, dir_name, base_url):
    segment_name = url.split('-')[-1]
    status = ''
    start = datetime.datetime.now()
    while status != '200':
        retries = urllib3.util.Retry(connect=5, read=4, redirect=5)
        http = urllib3.PoolManager(retries=retries)
        print(base_url + '/' + url)
        request = http.request('GET', base_url + '/' + url)
        status = str(request.status)
    end = datetime.datetime.now()
    print('Time: ' + str((end-start).seconds) + 's')
    datatowrite = request.data
    with open(dir_name + '/' + segment_name, 'wb') as video_segment:
        video_segment.write(datatowrite)
    print(segment_name + ' saved')

 

def download_ts_segments(urls, dir_name, base_url):
    for line in text.split('\n'):
        if line == '' or line[0] == '#':
           continue
        segment_name = line.split('-')[-1]
        if os.path.isfile(dir_name + '/' + segment_name):
            print(segment_name + ' skipped')
            continue
        retries = urllib3.util.Retry(connect=5, read=4, redirect=5)
        http = urllib3.PoolManager(retries=retries)
        status = ''
        start = datetime.datetime.now()
        while status != '200':
            request = download_ts_segment(base_url + '/' + line)
            status = str(request.status)
            print(status)
        end = datetime.datetime.now()
        print('Time: ' + str((end-start).seconds) + 's')
        datatowrite = request.data
        with open(dir_name + '/' + segment_name, 'wb') as video_segment:
            video_segment.write(datatowrite)
        print(segment_name + ' saved')

def find_missing_ts_segments(text, dir_name):
    ts_segments = []
    for line in text.split('\n'):
        if line == '' or line[0] == '#':
           continue
        segment_name = line.split('-')[-1]
        if os.path.isfile(dir_name + '/' + segment_name):
            print(segment_name + ' skipped')
            continue
        ts_segments.append(line)
    return ts_segments


if len(sys.argv) < 3:
    print('url and output path is missing')
    sys.exit()

url = sys.argv[1]
id = sys.argv[1]
output_path = sys.argv[2]  #'/Users/jfa/dr/PawPatrol/SE04/12/'
index = 0
if len(sys.argv) > 3:
    index = int(sys.argv[3])


os.makedirs(output_path, exist_ok=True)

#response = urllib.request.urlopen(url, timeout=500)
#data = response.read()      # a `bytes` object
#text = data.decode('utf-8') # a `str`; this step can't be used if data is binary

episode_selector_url = "https://ibl.api.bbc.co.uk/ibl/v1/episodes/{}".format(id)

episode_json = download_json(episode_selector_url)

pid = episode_json['episodes'][0]['versions'][0]['id']

media_selector_url = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{}/format/json/jsfunc/JS_callbacks0".format(pid)
print(media_selector_url)
media_output = download(media_selector_url).decode('utf8')

media_json = json.loads(media_output.replace('/**/ JS_callbacks0(', '').replace(');', ''))

media_urls = []
subtitle_urls = []
for item in media_json['media']:
    if item['kind'] == 'video':
        for connection in item['connection']:
            if connection['protocol'] != 'https':
                continue
            media_urls.append(connection['href'])
    if item['kind'] == 'captions':
        for connection in item['connection']:
            if connection['protocol'] != 'https':
                continue
            subtitle_urls.append(connection['href'])
         
print(subtitle_urls)

subtitles_index = 0
for subtitle_url in subtitle_urls:
    fetch_and_save_subtitles(subtitle_url, output_path, subtitles_index)
    subtitles_index += 1

#exit()

url = media_urls[index]

relative_play_list_url = find_play_list(fetch_play_list_from_url(url))

base_url = find_base_url(url)

play_list_url = base_url + '/' + relative_play_list_url

segments_text = fetch_play_list_from_url(play_list_url)

fetch_ts_segments(segments_text, output_path)

ts_segment_urls = find_missing_ts_segments(segments_text, output_path)

#download_ts_segments(segments_text, output_path, base_url)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

if len(ts_segment_urls) != 0:
    ts_segment_chunks = chunks(ts_segment_urls, 10)
    for ts_segment_chunk in ts_segment_chunks:
        threads = [threading.Thread(target=download_ts_segment, args=(url, output_path, base_url)) for url in ts_segment_chunk]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
else:
    print('All segments have been downloaded')
    ffmpeg = 'cd ' + output_path + ' && ffmpeg -f concat -i list.txt -bsf:a aac_adtstoasc -vcodec copy -c copy -crf 50 video.mp4'
    os.system(ffmpeg)