#!/usr/bin/env python

from urllib import URLopener
from urllib2 import urlopen
import requests
from urlparse import urlparse
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
                    if int(bandwidth) > 1500000:
                        grab_next_path = True
            continue
        if grab_next_path == False:
            continue
        print(line)
        filedata = urlopen(line)
        datatowrite = filedata.read()
        play_list_file_name = os.path.dirname(path) + '/play-list.m3u8'
        with open(play_list_file_name, 'w') as play_list:
            play_list.write(datatowrite)
        return play_list_file_name

def fetch_play_list(url):
    connection = urlopen(url)
    data = connection.read()
    connection.close()
    return data

def save_master_play_list(data, path):
    file_name = path + '/master.m3u8'
    file = open(file_name, 'wt')
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
    file = open(rendered_file_name, 'wt')
    file.write(html.encode('utf8'))
    file.close()

    soup = BeautifulSoup(html, 'lxml')

    video = soup.find('video')

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

master_play_list_url = fetch_master_play_list(url, output_path)#'https://www.dr.dk/tv/se/boern/ramasjang/paw-patrol/paw-patrol-iv/paw-patrol-iv-12', output_path) 
data = fetch_play_list(master_play_list_url)
master_play_list = save_master_play_list(data, output_path)


#print(os.path.dirname('/Users/jfa/dr/PawPatrol/SE04/12/master.m3u8'))

play_list_path = fetch_play_lists(master_play_list, 0, False)
fetch_ts_segments(play_list_path, False)
fetch_ts_segments(play_list_path, True)

ffmpeg = 'cd ' + output_path + ' && ffmpeg -f concat -i list.txt -bsf:a aac_adtstoasc -vcodec copy -c copy -crf 50 video.mp4'

os.system(ffmpeg)
