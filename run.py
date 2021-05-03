#!/usr/bin/env python

from urllib.request import urlopen
import requests
from urllib.parse import urlparse
from selenium import webdriver
from bs4 import BeautifulSoup
from time import sleep
import os
import sys

def fetch_ts_segments(path, fetch):
    file = open(path, 'r')
    dir_name = os.path.dirname(path)
    for line in file:
        if line[0] == '#':
           continue
        segment_name = line.split('/')[-1].split('?')[0]
        if fetch == False:
            with open(dir_name + '/list.txt', 'a') as list:
                list.write("file '" + segment_name + "'")
                list.write("\n")
            continue
        filedata = urlopen(line)
        datatowrite = filedata.read()
        with open(dir_name + '/' + segment_name, 'wb') as video_segment:
            video_segment.write(datatowrite)
        print(segment_name + ' saved')


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

def fetch_play_list(url):
    connection = urlopen(url)
    data = connection.read()
    connection.close()
    return data

def save_master_play_list(data, path):
    file_name = path + '/master.m3u8'
    file = open(file_name, 'wb')
    file.write(data)
    file.close()
    return file_name

def fetch_master_play_list(url, path):
    browser = webdriver.Chrome()
    browser.get(url)
    #html = browser.page_source

    sleep(5)

    html = browser.execute_script("return document.body.innerHTML")
    rendered_file_name = path + '/rendered-webpage.html'
    file = open(rendered_file_name, 'wb')
    file.write(html.encode('utf8'))
    file.close()

    soup = BeautifulSoup(html, 'lxml')

    video = soup.find('ShortVideoUrl')

    print(video)

    parts = str(video).split(' ')

    play_list = ''
    for part in parts:
        if part[0:3] != 'src':
            continue
        src = part.split('=')[-1][1:-1]
        if src[0:5] != 'https':
            continue
        play_list = src
        break
    browser.quit()
    return play_list

def convert(output_path):
    ffmpeg = 'cd ' + output_path + ' && ffmpeg -f concat -i list.txt -bsf:a aac_adtstoasc -vcodec copy -c copy -crf 50 video.mp4'
    os.system(ffmpeg)

print(sys.argv)

if len(sys.argv) < 3:
    print('url and output path is missing')
    sys.exit()

url = sys.argv[1]
output_path = sys.argv[2]  #'/Users/jfa/dr/PawPatrol/SE04/12/'

if os.path.isdir(output_path) == False:
    print(output_path + ' must exist, please create and try again')
    sys.exit()

if len(sys.argv) == 4 and sys.argv[3] == 'ffmpeg':
    convert(output_path)
    sys.exit()

#master_play_list_url = fetch_master_play_list(url, output_path)#'https://www.dr.dk/tv/se/boern/ramasjang/paw-patrol/paw-patrol-iv/paw-patrol-iv-12', output_path) 
#master_play_list_url = 'https://drod07m-vh.akamaihd.net/i/all/clear/streaming/45/5fdb223f539f02076c640445/VS-Ternet-Ninja-2018-009617000_58ce16a3e2454958bfc952eab5f40468_,983,3517,2485,321,1877,499,.mp4.csmil/master.m3u8' # fetch_master_play_list(url, output_path)#'https://www.dr.dk/tv/se/boern/ramasjang/paw-patrol/paw-patrol-iv/paw-patrol-iv-12', output_path) 
#master_play_list_url = 'https://drod02g-vh.akamaihd.net/i/dk/clear/streaming/0f/5fdd8132aa5a612714959b0f/Ternet-Ninja_c8983a9436714fc2b3731072c55dd2e9_,300,512,1000,2200,3000,4300,.mp4.csmil/master.m3u8'
#master_play_list_url = 'https://drod02g-vh.akamaihd.net/i/dk/clear/streaming/0f/5fdd8132aa5a612714959b0f/Ternet-Ninja_c8983a9436714fc2b3731072c55dd2e9_,300,512,1000,2200,3000,4300,.mp4.csmil/master.m3u8?cc1=name=Dansk~default=no~forced=no~lang=da~uri=https://drod02g-vh.akamaihd.net/p/allx/clear/download/0f/5fdd8132aa5a612714959b0f/subtitles/HardOfHearing-17889996-0deafd96-52ce-4c8f-8e8d-0da44fc8ace6/playlist.m3u8'
data = fetch_play_list(url)
master_play_list = save_master_play_list(data, output_path)


#print(os.path.dirname('/Users/jfa/dr/PawPatrol/SE04/12/master.m3u8'))

play_list_path = fetch_play_lists(master_play_list, 0, False)
fetch_ts_segments(play_list_path, False)
fetch_ts_segments(play_list_path, True)

ffmpeg = 'cd ' + output_path + ' && ffmpeg -f concat -i list.txt -bsf:a aac_adtstoasc -vcodec copy -c copy -crf 50 video.mp4'

os.system(ffmpeg)
