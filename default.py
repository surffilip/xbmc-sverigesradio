# coding: latin-1
import os
import urllib2
from urlparse import urlsplit, urlunsplit, SplitResult
import urllib

import xbmcgui
import xbmcplugin
import xbmcaddon

from xml.dom.minidom import parse, parseString

BASE_API = "http://api.sr.se/api/v2/"
CHANNEL_URL = "http://api.sr.se/api/v2/channels"
NEWS_URL = "http://api.sr.se/api/v2/news"
PROGRAM_LIST_URL = "http://api.sr.se/api/v2/programs"
BROADCAST_LIST_URL = "http://api.sr.se/api/v2/broadcasts?programid={0}&pagination=false"
PROGRAM_DETAIL_URL = "http://api.sr.se/api/v2/program/broadcastfeed.aspx?unitid="
PROGRAM_DETAIL_URL = "http://api.sr.se/api/radio/radio.aspx?type=broadcast&id={0}&codingformat=.m4a&metafile=m3u&quality={1}"
BASE_URL = "http://sr.se"

__settings__ = xbmcaddon.Addon(id='plugin.audio.sverigesradio')

QUALITIES = ["low", "normal", "high"]
PROTOCOLS = ["http", "rtsp"]

SET_QUALITY = QUALITIES[int(__settings__.getSetting("quality"))]
SET_PROTOCOL = PROTOCOLS[int(__settings__.getSetting("protocol"))]


def fetch_channels():
    doc, state = load_xml(CHANNEL_URL)
    if doc and not state:
        for channel in doc.getElementsByTagName("channel"):
            channel_id = channel.getAttribute("id")
            title = channel.getAttribute("name").encode('utf_8')
            originaltitle = title
            logo = get_node_value(channel, "image")
            description = get_node_value(channel, "tagline")
            if description is not None:
                description = description.encode('utf_8')
                title = title + " - " + description
            else:
                description = ''
            audio_link = channel.getElementsByTagName("liveaudio")
            streamingurl = audio_link[0].getElementsByTagName("url")[0].firstChild.nodeValue
            yield {'id': channel_id,
                   'title': title,
                   'originaltitle': originaltitle,
                   'logo': logo,
                   'desc': description,
                   'stream': streamingurl
                   }
    else:
        if state == "site":
            xbmc.executebuiltin('Notification("Sveriges Radio","Site down")')
        else:
            xbmc.executebuiltin('Notification("Sveriges Radio","Malformed result")')


def get_live(channel):
    use_quality = {'high': 'hi',
                   'low': 'low',
                   'normal': 'normal',}[SET_QUALITY]
    stream = urlsplit(channel['stream'])
    protocol = stream.scheme
    stream_dir, stream_file = os.path.split(stream.path)
    new_stream_file = '-{0}'.format(use_quality).join(os.path.splitext(stream_file))
    new_path = os.path.join(stream_dir, new_stream_file)
    return {
    'url': urlunsplit(SplitResult(protocol, stream.netloc, new_path, stream.query, stream.fragment)),
    'logo': channel['logo'] if channel['logo'] is not None else '',}

def list_live():
    for channel in fetch_channels():
        live = get_live(channel)
        add_posts(channel['title'], live['url'], channel['desc'], live['logo'], isLive = 'true', album=channel['originaltitle'], artist='Sveriges Radio')
    xbmcplugin.endOfDirectory(HANDLE)

def list_channels(channelsurl):
    for channel in fetch_channels():
        url = urlsplit(channelsurl)
        new_path = os.path.join(url.path, 'programs', channel['id'])
        new_url = urlunsplit(SplitResult(url.scheme, url.netloc, new_path, url.query, url.fragment))
        print (url, new_path, new_url)
        logo = channel['logo'] if channel['logo'] is not None else ''
        add_posts(channel['title'],  new_url, channel['desc'], logo, isFolder = True, album = channel['originaltitle'], artist = 'Sveriges Radio')
    xbmcplugin.endOfDirectory(HANDLE)

def list_channel_programs(url):
    path = urlsplit(url).path
    if path == "/news/":
        plisturl = urlsplit(NEWS_URL)
    else:
        plisturl = urlsplit(PROGRAM_LIST_URL)
    new_path = os.path.join(plisturl.path, 'index')
    channel_id = os.path.basename(urlsplit(url).path)
    query = {'pagination' : 'false', 'channelid' : channel_id, 'filter' : 'program.hasondemand&filterValue=true'}
    query = urllib.urlencode(query)
    programs_url = urlunsplit(SplitResult(plisturl.scheme, plisturl.netloc, new_path, query, ''))
    doc, state = load_xml(programs_url)
    if doc and not state:
        for program in doc.getElementsByTagName("program"):
            program_id = program.getAttribute("id")
            title = program.getAttribute("name").encode('utf_8')
            description = get_node_value(program, "description")
            if description:
                description = description.encode('utf_8')
                title = title + " - " + description
            else:
                description = ''
            logo = get_node_value(program, "programimage")
            add_posts(title, url + '/program/' + program_id + "/", description, logo, isFolder=True)
    else:
        if state == "site":
            xbmc.executebuiltin('Notification("Sveriges Radio","Site down")')
        else:
            xbmc.executebuiltin('Notification("Sveriges Radio","Malformed result")')
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE)
    xbmcplugin.endOfDirectory(HANDLE)


def list_broadcasts(program_id):
    doc, state = load_xml(BROADCAST_LIST_URL.format(program_id))
    if doc and not state:
        base = ""
        for broadcast in doc.getElementsByTagName("broadcast"):
            title = get_node_value(broadcast, "title")
            duration = get_node_value(broadcast, "totalduration")
            bcastfiles = broadcast.getElementsByTagName("broadcastfile")
            url = get_node_value(bcastfiles[0], "url")
            logo = get_node_value(broadcast, "image")
            logourl = BASE_URL + logo
            description = get_node_value(broadcast, "description")
            add_posts(title, url, description, logourl, duration=duration) #url, description, thumb, artist='Sveriges Radio', album=originaltitle, duration=duration)
    else:
        if state == "site":
            xbmc.executebuiltin('Notification("Sveriges Radio","Site down")')
        else:
            xbmc.executebuiltin('Notification("Sveriges Radio","Malformed result")')
    xbmcplugin.endOfDirectory(HANDLE)


def add_posts(title, url, description='', thumb='', isPlayable='true', \
    isLive='false', isFolder=False, artist='',
              album='', duration=''):
    print('duration is', duration)
    title = title.replace("\n", " ")
    listitem = xbmcgui.ListItem(title, iconImage=thumb)
    listitem.setInfo(type='music', infoLabels={'title': title, 'artist': artist, 'album': album, 'duration': duration})
    listitem.setProperty('IsPlayable', isPlayable)
    listitem.setProperty('IsLive', isLive)
    listitem.setPath(url)
    return xbmcplugin.addDirectoryItem(HANDLE, url=url, listitem=listitem, isFolder=isFolder)

def add_main_menu():
    listitem = xbmcgui.ListItem("Live")
    listitem.setInfo(type='music', infoLabels={'Title': "Live"})
    listitem.setPath('live')
    u = sys.argv[0] + "live/"
    xbmcplugin.addDirectoryItem(HANDLE, url=u, listitem=listitem, isFolder=True)
    listitem = xbmcgui.ListItem("Program A-Ö")
    listitem.setInfo(type='music', infoLabels={'Title': "Program A-Ö"})
    listitem.setPath('program')
    u = sys.argv[0] + "programs/"
    xbmcplugin.addDirectoryItem(HANDLE, url=u, listitem=listitem, isFolder=True)
    listitem = xbmcgui.ListItem("Kanaler")
    listitem.setInfo(type='music', infoLabels={'Title': "Kanaler"})
    listitem.setPath('channel')
    u = sys.argv[0] + "channels/"
    xbmcplugin.addDirectoryItem(HANDLE, url=u, listitem=listitem, isFolder=True)
    listitem = xbmcgui.ListItem("Nyheter")
    listitem.setInfo(type='music', infoLabels={'Title': "Nyheter"})
    listitem.setPath('news')
    u = sys.argv[0] + "news/"
    xbmcplugin.addDirectoryItem(HANDLE, url=u, listitem=listitem, isFolder=True)
    return xbmcplugin.endOfDirectory(HANDLE)


def get_node_value(parent, name, ns=""):
    if ns:
        if parent.getElementsByTagNameNS(ns, name) and \
                parent.getElementsByTagNameNS(ns, name)[0].childNodes:
            return parent.getElementsByTagNameNS(ns, name)[0].childNodes[0].data
    else:
        if parent.getElementsByTagName(name) and \
                parent.getElementsByTagName(name)[0].childNodes:
            return parent.getElementsByTagName(name)[0].childNodes[0].data
    return None

def load_xml(url):
    try:
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
    except:
        xbmc.log("plugin.audio.sverigesradio: unable to load url: " + url)
        return None, "site"
    xml = response.read()
    response.close()
    try:
        out = parseString(xml)
    except:
        xbmc.log("plugin.audio.sverigesradio: malformed xml from url: " + url)
        return None, "xml"
    return out, None


if (__name__ == "__main__" ):
    MODE = sys.argv[0]
    HANDLE = int(sys.argv[1])
    modes = MODE.split('/')
    activemode = modes[len(modes) - 2]
    parentmode = modes[len(modes) - 3]
    print(MODE, activemode, parentmode, 'hoioi')
    if activemode == "allprograms":
        list_programs(MODE)
    elif activemode == "live":
        list_live()
    elif activemode == "channels":
        list_channels(MODE)
    elif parentmode == "channels" and activemode == 'programs':
        list_channel_programs(MODE)
    elif activemode == "news":
        list_channel_programs(MODE)
    elif parentmode == "program":
        list_broadcasts(activemode)

    else:
        add_main_menu()
