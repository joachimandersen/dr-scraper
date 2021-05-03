#!/usr/bin/env python

import sys
import os
import re
from datetime import datetime, timedelta
from xml.etree import ElementTree
import xmltodict
import json


def innertext(tag):
  return (tag.text or '') + ''.join(innertext(e) for e in tag) + (tag.tail or ' ')

xml_file = sys.argv[1]
subtitles_file_name = sys.argv[2]
start_delay = int(sys.argv[3])
end_delay = int(sys.argv[4])

subtitles_base_path = os.path.join(os.path.dirname(xml_file), subtitles_file_name)

def adjust_time(time_str, delay):
    try:
        adjusted_time = datetime.strptime(time_str, '%H:%M:%S.%f') + timedelta(milliseconds=delay)
        return adjusted_time.strftime('%H:%M:%S,%f')[:-3]
    except ValueError:
        adjusted_time = datetime.strptime(time_str, '%H:%M:%S') + timedelta(milliseconds=delay)
        return adjusted_time.strftime('%H:%M:%S,%f')[:-3]

def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


def convert_to_srt(file_path, tree, delay):
    if os.path.isfile(file_path):
        os.remove(file_path)
    text = ''
    for element in tree.getroot():
        if element.tag.endswith('body'):
            for child in element.getchildren():
                line = 1
                for comment in child.getchildren():
                    with open(file_path, 'a') as subtitle:
                        subtitle.write(str(line).strip())
                        subtitle.write(os.linesep)
                        subtitle.write(adjust_time(comment.attrib['begin'], delay))
                        subtitle.write(' --> ')
                        subtitle.write(adjust_time(comment.attrib['end'], delay))
                        subtitle.write(os.linesep)
                        #subtitle.write(innertext(comment).strip())
                        subtitle.write(cleanhtml(ElementTree.tostring(comment).decode().replace('<ns0:br />', os.linesep)))
                        subtitle.write(os.linesep)
                        subtitle.write(os.linesep)
                    line += 1

xml_tree = ElementTree.parse(xml_file)

#xml_dict = xmltodict.parse(ElementTree.tostring(xml_tree.getroot()))
#json_data = json.dumps(xml_dict, indent=2)
#print(json_data)

#exit()

if start_delay != end_delay:
    for delay in range(start_delay, end_delay, 100):
        file_path = subtitles_base_path + str(delay) + '.srt'
        convert_to_srt(file_path, xml_tree, delay)
else:
    file_path = subtitles_base_path + '.srt'
    convert_to_srt(file_path, xml_tree, 0)
