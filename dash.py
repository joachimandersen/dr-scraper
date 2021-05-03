#!/usr/bin/env python

import sys
import urllib3.request
import os
import json
import re
import datetime
import threading
from xml.etree import ElementTree

# Copy from https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/utils.py
def parse_duration(s):
    if not isinstance(s, str):
        return None

    s = s.strip()

    days, hours, mins, secs, ms = [None] * 5
    m = re.match(r'(?:(?:(?:(?P<days>[0-9]+):)?(?P<hours>[0-9]+):)?(?P<mins>[0-9]+):)?(?P<secs>[0-9]+)(?P<ms>\.[0-9]+)?Z?$', s)
    if m:
        days, hours, mins, secs, ms = m.groups()
    else:
        m = re.match(
            r'''(?ix)(?:P?
                (?:
                    [0-9]+\s*y(?:ears?)?\s*
                )?
                (?:
                    [0-9]+\s*m(?:onths?)?\s*
                )?
                (?:
                    [0-9]+\s*w(?:eeks?)?\s*
                )?
                (?:
                    (?P<days>[0-9]+)\s*d(?:ays?)?\s*
                )?
                T)?
                (?:
                    (?P<hours>[0-9]+)\s*h(?:ours?)?\s*
                )?
                (?:
                    (?P<mins>[0-9]+)\s*m(?:in(?:ute)?s?)?\s*
                )?
                (?:
                    (?P<secs>[0-9]+)(?P<ms>\.[0-9]+)?\s*s(?:ec(?:ond)?s?)?\s*
                )?Z?$''', s)
        if m:
            days, hours, mins, secs, ms = m.groups()
        else:
            m = re.match(r'(?i)(?:(?P<hours>[0-9.]+)\s*(?:hours?)|(?P<mins>[0-9.]+)\s*(?:mins?\.?|minutes?)\s*)Z?$', s)
            if m:
                hours, mins = m.groups()
            else:
                return None

    duration = 0
    if secs:
        duration += float(secs)
    if mins:
        duration += float(mins) * 60
    if hours:
        duration += float(hours) * 60 * 60
    if days:
        duration += float(days) * 24 * 60 * 60
    if ms:
        duration += float(ms)
    return duration

def download(url):
    http = urllib3.PoolManager()
    response = http.request('GET', url)
    return response.data

def download_json(url):
    return json.loads(download(url))

def find_base_url(url):
    last_slash = url.rfind('/')
    return url[0:last_slash]

def download_ts_segment(url, dir_name):
    is_subtitle = False
    segment_name = url.split('=')[-1]
    if len(segment_name.split('.')) < 2:
        segment_name += '.xml'
        is_subtitle = True
    if os.path.isfile(dir_name + '/' + segment_name):
        return
    print(url)
    status = ''
    start = datetime.datetime.now()
    user_agent = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0'}
    while status != '200':
        retries = urllib3.util.Retry(connect=5, read=4, redirect=5)
        if is_subtitle:
            http = urllib3.PoolManager(retries=retries, headers=user_agent)
        else:
            timeout = urllib3.util.Timeout(connect=2.0, read=5.0)
            http = urllib3.PoolManager(retries=retries, headers=user_agent, timeout=timeout)
        request = http.request('GET', url)
        status = str(request.status)
    end = datetime.datetime.now()
    print('Time: ' + str((end-start).seconds) + 's')
    datatowrite = request.data
    with open(dir_name + '/' + segment_name, 'wb') as segment:
        segment.write(datatowrite)
    print(segment_name + ' saved')

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def find_audio_representation(adaptation_set, ns):
    return adaptation_set.find('mpd:Representation', ns)

def find_audio_template(adaptation_set, ns):
    return adaptation_set.find('mpd:SegmentTemplate', ns)

def find_video_representation(adaptation_set, ns):
    representations = adaptation_set.findall('mpd:Representation', ns)
    selected_representation = representations[0]
    for representation in representations:
        bandwidth = int(representation.attrib['bandwidth'])
        print(bandwidth)
        if bandwidth > int(selected_representation.attrib['bandwidth']) and bandwidth < 5070000:
            selected_representation = representation
    return selected_representation

def find_video_template(representation, ns):
    return representation.find('mpd:SegmentTemplate', ns)

def find_segment_template(adaptation_set, ns):
    if adaptation_set.attrib['contentType'] == 'audio':
        return find_audio_template(adaptation_set, ns)
    representation = find_video_representation(adaptation_set, ns)
    return find_video_template(representation, ns)

def get_video_stream_urls(adaptation_set, base_url, type_url, programme_duration, ns):
    representation = find_video_representation(adaptation_set, ns)
    template = find_video_template(representation, ns)
    if template is None:
        template = find_video_template(adaptation_set, ns)
    initialization = template.attrib['initialization']
    media = template.attrib['media']
    representation_id = representation.attrib['id']
    segment_duration = float(template.attrib['duration']) / float(template.attrib['timescale'])

    num_segments = int(programme_duration / segment_duration)
    if segment_duration * num_segments < programme_duration:
        num_segments += 1

    segment_url = base_url + '/' + type_url + media.replace('$RepresentationID$', representation_id)

    segment_urls = []
    segment_urls.append(segment_url.replace('$Number$', '').rsplit('.', 1)[0].rsplit('-', 1)[0] + '.dash')

    for segment_id in range(1, num_segments + 1, 1):
        segment_urls.append(segment_url.replace('$Number$', str(segment_id)))
    return segment_urls

def handle_video_adaptation_set(adaptation_set, base_url, type_url, ns):
    representation = find_video_representation(adaptation_set, ns)
    template = find_video_template(representation, ns)
    print(template)
    initialization = template.attrib['initialization']
    media = template.attrib['media']
    representation_id = representation.attrib['id']
    segment_duration = float(template.attrib['duration']) / float(template.attrib['timescale'])
    print(segment_duration)

    num_segments = int(programme_duration / segment_duration)
    if segment_duration * num_segments < programme_duration:
        num_segments += 1

    print(num_segments)
    segment_url = base_url + '/' + type_url + media.replace('$RepresentationID$', representation_id)

    segment_urls = []

    for segment_id in range(1, num_segments + 1, 1):
        segment_urls.append(segment_url.replace('$Number$', str(segment_id)))
        #download_ts_segment(, output_path)

    segment_chunks = chunks(segment_urls, 10)
    for segment_chunk in segment_chunks:
        threads = [threading.Thread(target=download_ts_segment, args=(url, output_path)) for url in segment_chunk]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()     

def get_audio_stream_urls(adaptation_set, base_url, type_url, programme_duration, ns):
    representation = find_audio_representation(adaptation_set, ns)
    template = find_audio_template(adaptation_set, ns)
    initialization = template.attrib['initialization']
    media = template.attrib['media']
    representation_id = representation.attrib['id']
    segment_duration = float(template.attrib['duration']) / float(template.attrib['timescale'])

    num_segments = int(programme_duration / segment_duration)
    if segment_duration * num_segments < programme_duration:
        num_segments += 1

    segment_url = base_url + '/' + type_url + media.replace('$RepresentationID$', representation_id)

    segment_urls = []
    segment_urls.append(segment_url.replace('$Number$', '').rsplit('.', 1)[0].rsplit('-', 1)[0] + '.dash')

    for segment_id in range(1, num_segments+1, 1):
        segment_urls.append(segment_url.replace('$Number$', str(segment_id)))
    return segment_urls

def handle_audio_adaptation_set(adaptation_set, base_url, type_url, ns):
    representation = find_audio_representation(adaptation_set, ns)
    template = find_audio_template(adaptation_set, ns)
    print(template)
    initialization = template.attrib['initialization']
    media = template.attrib['media']
    representation_id = representation.attrib['id']
    segment_duration = float(template.attrib['duration']) / float(template.attrib['timescale'])
    print(segment_duration)

    num_segments = int(programme_duration / segment_duration)
    if segment_duration * num_segments < programme_duration:
        num_segments += 1

    print(num_segments)
    segment_url = base_url + '/' + type_url + media.replace('$RepresentationID$', representation_id)

    segment_urls = []

    for segment_id in range(1, num_segments+1, 1):
        segment_urls.append(segment_url.replace('$Number$', str(segment_id)))
        #download_ts_segment(, output_path)

    segment_chunks = chunks(segment_urls, 10)
    for segment_chunk in segment_chunks:
        threads = [threading.Thread(target=download_ts_segment, args=(url, output_path)) for url in segment_chunk]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()     

def write_video_list(adaptation_set, dir_path, ns):
    representation = find_video_representation(adaptation_set, ns)
    template = find_video_template(representation, ns)
    initialization = template.attrib['initialization']
    media = template.attrib['media']
    representation_id = representation.attrib['id']
    segment_duration = float(template.attrib['duration']) / float(template.attrib['timescale'])

    num_segments = int(programme_duration / segment_duration)
    if segment_duration * num_segments < programme_duration:
        num_segments += 1

    print(num_segments)
    segment_url = base_url + '/' + type_url + media.replace('$RepresentationID$', representation_id)

    segment_url = base_url + '/' + type_url + media.replace('$RepresentationID$', representation_id)

    for segment_id in range(1, num_segments, 1):
        with open(dir_path + 'list.txt', 'a') as file_list:
            file_list.write('file \'' + segment_url.replace('$Number$', str(segment_id)).split('=')[-1] + '\'')
            file_list.write(os.linesep)

def write_audio_list(adaptation_set, dir_path, ns):
    representation = find_audio_representation(adaptation_set, ns)
    template = find_audio_template(adaptation_set, ns)
    initialization = template.attrib['initialization']
    media = template.attrib['media']
    representation_id = representation.attrib['id']
    segment_duration = float(template.attrib['duration']) / float(template.attrib['timescale'])

    num_segments = int(programme_duration / segment_duration)
    if segment_duration * num_segments < programme_duration:
        num_segments += 1

    segment_url = base_url + '/' + type_url + media.replace('$RepresentationID$', representation_id)

    for segment_id in range(1, num_segments, 1):
        with open(dir_path + 'list.txt', 'a') as file_list:
            file_list.write('file \'' + segment_url.replace('$Number$', str(segment_id)).split('=')[-1] + '\'')
            file_list.write(os.linesep)

def create_download_list_file(id, dir_path):
    if os.path.isfile(output_path + '/file_list.txt'):
        return
    episode_selector_url = "https://ibl.api.bbc.co.uk/ibl/v1/episodes/{}".format(id)
    episode_json = download_json(episode_selector_url)
    pid = episode_json['episodes'][0]['versions'][0]['id']

    media_selector_url = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{}/format/json/jsfunc/JS_callbacks0".format(pid)
    media_output = download(media_selector_url).decode('utf8')

    media_json = json.loads(media_output.replace('/**/ JS_callbacks0(', '').replace(');', ''))

    segment_urls = []
    media_urls = []
    for item in media_json['media']:
        if item['kind'] == 'video':
            for connection in item['connection']:
                if connection['protocol'] != 'https' or connection['transferFormat'] != 'dash':
                    continue
                media_urls.append(connection['href'])
        if item['kind'] == 'captions':
            for connection in item['connection']:
                if connection['protocol'] != 'https':
                    continue
                segment_urls.append(connection['href'])
         
    #print(media_urls)

    ns = {'mpd':'urn:mpeg:dash:schema:mpd:2011'}
    xml_root = ElementTree.fromstring(download(media_urls[-1]).decode('utf-8'))
    media_presentation_duration = xml_root.attrib['mediaPresentationDuration']
    print(media_presentation_duration)
    programme_duration = parse_duration(media_presentation_duration)
    #duration_matches = re.search(r'^PT(\d*)M(\d*)\.(\d*)S', media_presentation_duration)
    #programme_duration = int(int(duration_matches[1]) * 3600 + int(duration_matches[2]) * 60 + int(duration_matches[3]))
    #programme_duration = int(int(duration_matches[1]) * 60 + int(duration_matches[2]))
    print(programme_duration)
    period = xml_root.find('mpd:Period', ns)
    type_url = period.find('mpd:BaseURL', ns).text
    base_url = find_base_url(media_urls[0])
    adaptation_sets = period.findall('mpd:AdaptationSet', ns)
    for a_s in adaptation_sets:
        if a_s.attrib['contentType'] == 'audio':
            #handle_audio_adaptation_set(a_s, base_url, type_url, ns)
            #write_audio_list(a_s, output_path, ns)
            segment_urls.extend(get_audio_stream_urls(a_s, base_url, type_url, programme_duration, ns))
        if a_s.attrib['contentType'] == 'video':
            segment_urls.extend(get_video_stream_urls(a_s, base_url, type_url, programme_duration, ns))
            #handle_video_adaptation_set(a_s, base_url, type_url, ns)
            #write_video_list(a_s, output_path, ns)

    with open(output_path + '/file_list.txt', 'w') as f:
        s1=os.linesep.join(segment_urls)
        f.write(s1)

def fetch_missing_segments(file_list, dir_name):
    if os.path.isfile(file_list):
        all_segment_urls = []
        with open(file_list) as file_list:
            for url in file_list:
                all_segment_urls.append(url.replace(os.linesep, ''))
        segment_chunks = chunks(all_segment_urls, 5)
        for segment_chunk in segment_chunks:
            threads = [threading.Thread(target=download_ts_segment, args=(url, dir_name)) for url in segment_chunk]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

def have_all_segments_been_fetched(file_list, dir_name):
    all_segment_urls = []
    with open(file_list) as file_list:
        for url in file_list:
            segment_name = url.split('=')[-1]
            if len(segment_name.split('.')) < 2:
                segment_name += '.xml'
            if not os.path.isfile(dir_name + '/' + segment_name):
                return False
    return True
 

id = sys.argv[1]
output_path = sys.argv[2]  #'/Users/jfa/dr/PawPatrol/SE04/12/'

os.makedirs(output_path, exist_ok=True)

#download_ts_segment('https://vod-dash-uk-live.akamaized.net/usp/auth/vod/piff_abr_full_hd/3f9bbc-b09t2fj4/vf_b09t2fj4_27c8fdd8-7589-4491-a782-117b9c940698.ism/dash/vf_b09t2fj4_27c8fdd8-7589-4491-a782-117b9c940698-audio_eng=96000.dash', output_path)
#download_ts_segment('https://vod-dash-uk-live.akamaized.net/usp/auth/vod/piff_abr_full_hd/3f9bbc-b09t2fj4/vf_b09t2fj4_27c8fdd8-7589-4491-a782-117b9c940698.ism/dash/vf_b09t2fj4_27c8fdd8-7589-4491-a782-117b9c940698-video=5070000.dash', output_path)

#exit()

create_download_list_file(id, output_path)

while not have_all_segments_been_fetched(output_path + '/file_list.txt', output_path):
    fetch_missing_segments(output_path + '/file_list.txt', output_path)


if os.path.isfile(output_path + '/file_list.txt'):
    all_segment_urls = []
    with open(output_path + '/file_list.txt') as file_list:
        for url in file_list:
            all_segment_urls.append(url.replace(os.linesep, ''))
    segment_chunks = chunks(all_segment_urls, 5)
    for segment_chunk in segment_chunks:
        threads = [threading.Thread(target=download_ts_segment, args=(url, output_path)) for url in segment_chunk]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    exit()

episode_selector_url = "https://ibl.api.bbc.co.uk/ibl/v1/episodes/{}".format(id)


episode_json = download_json(episode_selector_url)

pid = episode_json['episodes'][0]['versions'][0]['id']

media_selector_url = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/pc/vpid/{}/format/json/jsfunc/JS_callbacks0".format(pid)
media_output = download(media_selector_url).decode('utf8')

media_json = json.loads(media_output.replace('/**/ JS_callbacks0(', '').replace(');', ''))

segment_urls = []
media_urls = []
for item in media_json['media']:
    if item['kind'] == 'video':
        for connection in item['connection']:
            if connection['protocol'] != 'https' or connection['transferFormat'] != 'dash':
                continue
            media_urls.append(connection['href'])
    if item['kind'] == 'captions':
        for connection in item['connection']:
            if connection['protocol'] != 'https':
                continue
            segment_urls.append(connection['href'])
         
#print(media_urls)

ns = {'mpd':'urn:mpeg:dash:schema:mpd:2011'}
xml_root = ElementTree.fromstring(download(media_urls[-1]).decode('utf-8'))

media_presentation_duration = xml_root.attrib['mediaPresentationDuration']

print(media_presentation_duration)

duration_matches = re.search(r'^PT(\d*)M(\d*)\.(\d*)S', media_presentation_duration)

#programme_duration = int(int(duration_matches[1]) * 3600 + int(duration_matches[2]) * 60 + int(duration_matches[3]))
programme_duration = int(int(duration_matches[1]) * 60 + int(duration_matches[2]))

period = xml_root.find('mpd:Period', ns)

type_url = period.find('mpd:BaseURL', ns).text

base_url = find_base_url(media_urls[0])

adaptation_sets = period.findall('mpd:AdaptationSet', ns)

for a_s in adaptation_sets:
    if a_s.attrib['contentType'] == 'audio':
        #handle_audio_adaptation_set(a_s, base_url, type_url, ns)
        #write_audio_list(a_s, output_path, ns)
        segment_urls.extend(get_audio_stream_urls(a_s, base_url, type_url, ns))
    if a_s.attrib['contentType'] == 'video':
        segment_urls.extend(get_video_stream_urls(a_s, base_url, type_url, ns))
        #handle_video_adaptation_set(a_s, base_url, type_url, ns)
        #write_video_list(a_s, output_path, ns)

with open(output_path + '/file_list.txt', 'w') as f:
    s1=os.linesep.join(segment_urls)
    f.write(s1)

exit()

adaptation_set = period.find('mpd:AdaptationSet', ns)

template_0 = adaptation_set.find('mpd:SegmentTemplate', ns)
initialization = template_0.attrib['initialization']
media = template_0.attrib['media']
representation = adaptation_set.find('mpd:Representation', ns)
representation_id = representation.attrib['id']
segment_duration = float(template_0.attrib['duration']) / float(template_0.attrib['timescale'])
print(segment_duration)

num_segments = int(programme_duration / segment_duration)
if segment_duration * num_segments < programme_duration:
    num_segments += 1

print(num_segments)


segment_url = base_url + '/' + type_url + media.replace('$RepresentationID$', representation_id)

segment_urls = []

for segment_id in range(1, num_segments, 1):
    segment_urls.append(segment_url.replace('$Number$', str(segment_id)))
    #download_ts_segment(, output_path)

segment_chunks = chunks(segment_urls, 10)
for segment_chunk in segment_chunks:
    threads = [threading.Thread(target=download_ts_segment, args=(url, output_path)) for url in segment_chunk]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join() 