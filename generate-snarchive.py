#!/usr/bin/env python3
#
# © Jan Kanis 2016
# Available under the MIT license:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Usage: 
- run this script
- put the generated snarchive.xml file in a public Dropbox/Google Drive/other cloud drive folder
- point your podcast player at the link of the file

To generate a shorter archive not going back to the beginning, edit the 'backto' year below.
"""

import tzlocal, datetime
import string
import requests, bs4
from xml.sax.saxutils import escape as esc

template = string.Template(open('sn-template.xml').read())
itemtemplate = string.Template(open('sn-item.xml').read())


def get_urls(end_year, start_year = 2005):
    now = datetime.datetime.now(tzlocal.get_localzone())

    if not end_year:
      end_year = now.year
    
    thisyear = end_year

    urls = []
    if now.year == end_year:
        urls += ['https://www.grc.com/securitynow.htm']

    if start_year:
      urls += ('https://www.grc.com/sn/past/{}.htm'.format(year) for year in range(thisyear-1, start_year-1, -1))
    
    return urls



def download_page(url):
  print("\ndownloading {}...".format(url))
  r = requests.get(url)
  if not r.ok:
    raise Exception("failed to download {}: {} {}".format(url, r.status_code, r.reason))
  return r.content


def find_episodes(links):
  for l in links:
    try:
      page = download_page(l)
      soup = bs4.BeautifulSoup(page, 'html.parser')
      yield from find_episodes_in_page(soup)
    except Exception as e:
      print(e)


def find_episodes_in_page(soup):
  links = soup.find_all('a')
  
  for link in links:
    try:
      episode_nr = int(link.attrs['name'])
      yield get_item(soup, episode_nr)
    except Exception:
      pass


def get_item(soup, item):
  link = soup.find('a', attrs={'name':str(item)})
  
  header = link.findNext('table')
  episode, date, length = (x.strip() for x in header.text.split('|'))
  nr = int(episode.partition('#')[2])
  minutes = int(length.split(' ')[0])
  
  body = header.findNext('table')

  title = body.findChild('font', size=2).text
  description = body.findChild('font', size=1).text
  if description.startswith(title):
    description = description.partition(title)[2]
  description = description.strip()
  title = title.strip()
  assert description

  return dict(episode=episode,
              date=date,
              length=length,
              minutes=minutes,
              nr=nr,
              title=title,
              description=description)


def item_rss(links):
  for episode in find_episodes(links):
    minutes = episode['minutes']
    duration = "{}:{}:00".format(minutes//60, minutes%60)

    # Some old episodes use 'Sept' instead of 'Sep' for the month, and my podcast listener doesn't like that.
    date = episode['date'].split(' ')
    date[1] = date[1][:3]
    date = ' '.join(date)
    yield episode['nr'], itemtemplate.substitute(
      NR=esc(str(episode['nr'])),
      NR4=esc(str(episode['nr']).rjust(4, '0')),
      DATE=esc(date),
      DURATION=esc(duration),
      TITLE=esc(episode['title']),
      DESCRIPTION=esc(episode['description']))



def generate_rss(links, output, year):
  header = True
  episodes = []
  for nr, episode_rss in item_rss(links):
    if header: 
      print("Found episodes: ", end='', flush=True)
      header = False
    print(nr, end=', ', flush=True)
    episodes.append(episode_rss)

  if episodes:
    nowfmt = datetime.datetime(year, 1, 1, 0, 0, 0, 0, datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    out = open(output, 'w', encoding="utf-8")
    out.write(template.substitute(NOW=nowfmt, ITEMS=''.join(episodes)))
    print("\n\nCreated "+output)
    print("Put {} on a cloud drive (Dropbox, Google Drive, etc), create a link, and put the link in your podcast player".format(output))
  else:
    print("\nError: No episodes found!")



# generate_rss(urls)

for year in range(20, 2025):
    urls = get_urls(year+1, year)
    generate_rss(urls, f"rss/{year}.xml", year)
