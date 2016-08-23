'''
Created on 2016年8月17日

@author: mengwei
'''

import urllib.request
from bs4 import BeautifulSoup
import mysql.connector
import time
import redis
import threading

def getMainInfo(userHome, headers):
    request = urllib.request.Request(userHome, headers = headers)
    source_code = urllib.request.urlopen(request).read()
    plain_text = source_code.decode("utf-8")
    soup = BeautifulSoup(plain_text, "html.parser")
    full_name = soup.find('div', {'class':'vcard-fullname'}).get_text()
    user_name = soup.find('div', {'class':'vcard-username'}).get_text()
    organizationTag = soup.find('li', {'aria-label':'Organization'})
    organization = ""
    if organizationTag:
        organization = organizationTag.get_text()
    locationTag = soup.find('li', {'aria-label':'Home location'})
    location = ""
    if locationTag:
        location = locationTag.get_text()
    bioTag = soup.find('div', {'class':'user-profile-bio'})
    bio = ""
    if bioTag:
        bio = bioTag.get_text()
    emailTag = soup.find('li', {'aria-label':'Email'})
    email = ""
    if emailTag:
        email = emailTag.get_text()
    urlTag = soup.find('li', {'aria-label':'Blog or website'})
    url = ""
    if urlTag:
        url = urlTag.get_text()
    join_time = soup.find('local-time', {'class':'join-date'})['datetime']
    info = soup.find_all('strong', {'class':'vcard-stat-count d-block'})
    followers = info[0].get_text()
    starred = info[1].get_text()
    following = info[2].get_text()
    user = {
        'name' : user_name,
        'full_name' : full_name,
        'email' : email,
        'bio' : bio,
        'url' : url,
        'company' : organization,
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
        aTag = repo.find('div', {'class':'repo-list-stats'}).find_all('a')
        stars += int(aTag[0].get_text().strip('\n').strip().replace(',',''))
        forks += int(aTag[1].get_text().strip('\n').strip().replace(',',''))
    user['stars'] = stars
    user['forks'] = forks
    
def getFollowers(followersUrl, headers):
    request = urllib.request.Request(followersUrl, headers = headers)
    source_code = urllib.request.urlopen(request).read()
    plain_text = source_code.decode("utf-8")
    soup = BeautifulSoup(plain_text, "html.parser")
    followerList = soup.find_all('span', {'class':'css-truncate css-truncate-target'})
    followers = []
    for follower in followerList:
        aTag = follower.find('a')
        if aTag:
            followers.append(aTag.get('href').replace('/',''))
    return followers

def saveUser(user):
    config = {
        'user': 'root',
        'password': 'root', 
        'host': '127.0.0.1',
        'database': 'github-spider'
    }
    add_user = ("INSERT INTO user (name, full_name, email, bio, url, company, location, join_time, followers, starred, following, stars, forks) VALUES "
                "(%(name)s, %(full_name)s, %(email)s, %(bio)s, %(url)s, %(company)s, %(location)s, %(join_time)s, %(followers)s, %(starred)s, %(following)s, %(stars)s, %(forks)s)")
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
    
def startSpider():
    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    headers = { 'User-Agent' : user_agent }
    redisConfig = {
        'host': '192.168.1.104',
        'port': 6379,
        'password':123
    }
    r = redis.StrictRedis(**redisConfig)
    name = r.lpop("githubspider-toScanUsers").decode()
    while name != None:
        if r.sismember("githubspider-scannedUsers", name):
            print("已经爬取过该用户：%s"%name)
            name = r.lpop("githubspider-toScanUsers").decode()
            continue
        print(name)
        userHome = "https://github.com/" + name
        repositories = userHome + "?tab=repositories"
        followersUrl = userHome + "/followers"
        try:
            user = getMainInfo(userHome, headers)
            getStarsAndForks(repositories, headers, user)
            saveUser(user)
            followers = getFollowers(followersUrl, headers)
            for follower in followers:
                if not r.sismember("githubspider-scannedUsers", name):
                    r.rpush("githubspider-toScanUsers", follower)
        except Exception:
            print("error happend")
        r.sadd("githubspider-scannedUsers", name)
        name = r.lpop("githubspider-toScanUsers").decode()

if __name__ == '__main__':
    threads = []
    for i in range(0,10):
        threads.append(threading.Thread(target=startSpider))
    for t in threads:
        t.start()
