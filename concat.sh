#!/bin/sh

python ~/git/dr-scraper/xml2srt.py subtitle.xml subtitles 1 1

cat 96000.dash $(ls -vx 96000-*.m4s) > audio.mp4
#cat 5070000.dash $(ls -vx 5070000-*.m4s) > video.mp4
#cat 2812000.dash $(ls -vx 2812000-*.m4s) > video.mp4
cat 1604000.dash $(ls -vx 1604000-*.m4s) > video.mp4

ffmpeg -i video.mp4 -i audio.mp4 -c:v copy -c:a aac audio_and_video.mp4

ffmpeg -i audio_and_video.mp4 -i subtitles.srt -c copy -c:s mov_text audio_and_video_and_subtitle.mp4

