'''
Created on 2016年8月17日

@author: mengwei
'''

import urllib.request
from bs4 import BeautifulSoup
import mysql.connector
import time

def getMainInfo(userHome, headers):
    request = urllib.request.Request(userHome, headers = headers)
    source_code = urllib.request.urlopen(request).read()
    plain_text = source_code.decode("utf-8")
    soup = BeautifulSoup(plain_text, "html.parser")
    full_name = soup.find('div', {'class':'vcard-fullname'}).get_text()
    user_name = soup.find('div', {'class':'vcard-username'}).get_text()
    location = soup.find('li', {'aria-label':'Home location'}).get_text()
    join_time = soup.find('local-time', {'class':'join-date'})['datetime']
    info = soup.find_all('strong', {'class':'vcard-stat-count d-block'})
    followers = info[0].get_text()
    starred = info[1].get_text()
    following = info[2].get_text()
    user = {
        'name' : user_name,
        'full_name' : full_name,
        'location' : location,
        'join_time' : time.strptime(join_time, '%Y-%m-%dT%H:%M:%SZ'),
        'followers' : followers,
        'starred' : starred,
        'following' : following
    }
    return user

def getStarsAndForks(repositories, headers, user):
    request = urllib.request.Request(repositories, headers = headers)
    source_code = urllib.request.urlopen(request).read()
    plain_text = source_code.decode("utf-8")
    soup = BeautifulSoup(plain_text, "html.parser")
    repoList = soup.find_all('div', {'class':'repo-list-item public source'})
    stars = 0
    forks = 0
    for repo in repoList:
        aTag = repo.find_all('a')
        for e in aTag:
            print(e.get_text())
    user['stars'] = stars
    user['forks'] = forks

if __name__ == '__main__':
    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    headers = { 'User-Agent' : user_agent }
    userHome = "https://github.com/Vedenin"
    repositories = userHome + "?tab=repositories"
    user = getMainInfo(userHome, headers)
    getStarsAndForks(repositories, headers, user)
    config = {
        'user': 'root',
        'password': 'root',
        'host': '127.0.0.1',
        'database': 'github-spider'
    }
    add_user = ("INSERT INTO user (name, full_name, location, join_time, followers, starred, following) VALUES "
                "(%(name)s, %(full_name)s, %(location)s, %(join_time)s, %(followers)s, %(starred)s, %(following)s)")
    cnx = cur = None
    try:
        cnx = mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        print(err)
    else:
        cur = cnx.cursor()
        cur.execute(add_user, user)
        cnx.commit();
    finally:
        if cur:
            cur.close()
        if cnx:
            cnx.close()
        
