#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# webdriver
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import LOGGER
import logging,os
LOGGER.setLevel(logging.WARNING)
from selenium.webdriver.chrome.options import Options

# selenium - waiting
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException

# various utilities
import time, random, sys
import hashlib
from datetime import datetime
import os.path
from shutil import copyfile
import base64
import shutil
from datetime import timedelta, date, datetime
import signal


# In[ ]:


# Returns chromedriver with necessary parameters
def loadDriver(log_out):
    user_data_folder = sys.argv[1]
    user_data_copy = user_data_folder + "_copy"

    if os.path.exists(user_data_copy):
        shutil.rmtree(user_data_copy)
    shutil.copytree(user_data_folder, user_data_copy)
    log_out.write("Using user data: %s\n" % user_data_folder)

    # Set Chrome driver options: user agent, user data directory, and headless properties in Docker
    options = webdriver.ChromeOptions()

    with open(sys.argv[3], 'rt') as uafile:
        ua = uafile.read()
    log_out.write("User agent: %s\n" % ua)

    options.add_argument(ua)
    #MAC options.add_argument("--user-data-dir=" + user_data_copy)
    options.add_argument("--user-data-dir=/home/vzwa/" + user_data_copy)
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options, executable_path="/usr/local/bin/chromedriver")

    driver.set_page_load_timeout(15)

    return driver


# In[ ]:


# Create timestamped output directories
def createDirectories(timezstring):
    user_data_folder = sys.argv[1]

    log_directory = "logs/"
    group_count_directory = "group_count/" + user_data_folder + "_" + timezstring + "/"
    group_msg_directory = "group_msg/" + user_data_folder + "_" + timezstring + "/"

    for directory in [log_directory, group_count_directory, group_msg_directory]:
        if not os.path.isdir(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError:
                pass

    # logfile for this run
    log_out = open(log_directory + "traverse_" + user_data_folder + "_" + timezstring + ".txt","w")

    return log_out, group_count_directory, group_msg_directory


# In[ ]:


def md5h(text):
    return hashlib.md5(text).hexdigest()

# Returns MD5 hash of blob image
def hash_blob(driver, uri):
    result = driver.execute_async_script("""
    var uri = arguments[0];
    var callback = arguments[1];
    var toBase64 = function(buffer){for(var r,n=new Uint8Array(buffer),t=n.length,a=new Uint8Array(4*Math.ceil(t/3)),i=new Uint8Array(64),o=0,c=0;64>c;++c)i[c]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);for(c=0;t-t%3>c;c+=3,o+=4)r=n[c]<<16|n[c+1]<<8|n[c+2],a[o]=i[r>>18],a[o+1]=i[r>>12&63],a[o+2]=i[r>>6&63],a[o+3]=i[63&r];return t%3===1?(r=n[t-1],a[o]=i[r>>2],a[o+1]=i[r<<4&63],a[o+2]=61,a[o+3]=61):t%3===2&&(r=(n[t-2]<<8)+n[t-1],a[o]=i[r>>10],a[o+1]=i[r>>4&63],a[o+2]=i[r<<2&63],a[o+3]=61),new TextDecoder("ascii").decode(a)};
    var xhr = new XMLHttpRequest();
    xhr.responseType = 'arraybuffer';
    xhr.onload = function(){ callback(toBase64(xhr.response)) };
    xhr.onerror = function(){ callback(xhr.status) };
    xhr.open('GET', uri);
    xhr.send();
    """, uri)

    if type(result) == int :
        raise Exception("Request failed with status %s" % result)

    return md5h(base64.b64decode(result))


# In[ ]:


def countMembers(logfile_out, driver, groupfile_out):
    time.sleep(3)
    subtitle = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/header/div[2]/div[2]/span'))).text

    waits = 0

    while subtitle[0] != "+" and waits < 5:
        wait += 1
        time.sleep(5)
        subtitle = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/header/div[2]/div[2]/span'))).text

    # Click initial sidebar button
    button = driver.find_element_by_xpath('//*[@id="main"]/header/div[2]/div[2]')
    button.click()
    time.sleep(2)

    # Click secondary sidebar button, save number of members
    all_members = driver.find_element_by_xpath('//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/div[1]/div[5]/div[1]/div/div/div[1]/span')
    count = int(all_members.text.split(" ")[0])

    if subtitle[0] == '+' and (subtitle.count(',') + 1) == count:
        groupfile_out.write(subtitle + "\n\n")
        groupfile_out.write("SUCCESS:     Member true count: %s\n" % count)
        logfile_out.write("SUCCESS:     Member true count: %s\n" % count)

        time.sleep(1)
        button =         WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/header/div/div[1]/button')))
        button.click()
        return

    logfile_out.write("**EXCEPT**:  Running manual member count\n" % count)

    member_array = set()
    all_members.click()

    # Order members by their px/coordinates on page
    max_member_px = 0
    max_element = None

    while(True):
        prev_member_px = max_member_px

        # Grab all members
        full_list = driver.find_element_by_xpath('//*[@id="app"]/div/span[2]/div/div/div/div/div/div/div/div[2]/div[1]/div/div')
        full_list_members = full_list.find_elements_by_xpath('div')

        # For each member, find px; add member to array
        for element in full_list_members:
            s = element.get_attribute('style')
            member_px = int(s[s.find("(")+1 : s.find("px)")])

            try: # Some elements in the list are separators, not actual members
                member_name = element.find_element_by_xpath('./div/div/div[2]').text.split('\\n')[0]
                member_array.add(member_name)
            except:
                pass

            # Record member at bottom of list, while we keep trying to scroll
            if member_px > max_member_px:
                max_element = element
                max_member_px = member_px

        # Exit loop when scroll to end
        if max_member_px == prev_member_px:
            break
        else:
            # Scroll through list of members
            driver.execute_script("arguments[0].scrollIntoView();", max_element)
            time.sleep(3)

    groupfile_out.write(str(member_array) + "\n\n")
    groupfile_out.write("SUCCESS:     Member true count: %s\n" % count)
    logfile_out.write("SUCCESS:     Member true count: %s\n" % count)

    if len(member_array) != count:
        groupfile_out.write("**EXCEPT**:  COUNTS DID NOT MATCH\nFound: %s\n" % len(member_array))
        logfile_out.write("**EXCEPT**:  COUNTS DID NOT MATCH\nFound: %s\n" % len(member_array))

    time.sleep(1)
    button =     WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/span[2]/div/div/div/div/div/div/div/header/div/div[1]/button')))
    button.click()

    time.sleep(1)
    button =     WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/header/div/div[1]/button')))
    button.click()


# In[ ]:


def processMessage(driver, message, groupfile_out):
    not_found_quote = True

    # blue text messages
    if 'message' not in message.get_attribute('class'):
        groupfile_out.write("{EVENT}// %s\n" % message.text)
        groupfile_out.write("\n========={}//\n\n")
        return

    # try to gather message ORIGIN information (some messages don't have)
    try:
        message_origin = message.find_element_by_xpath('.//div[contains(@class,"color-")]')
        origin_info = [e.text for e in message_origin.find_elements_by_xpath('.//span')]

        # if length 2, contains phone number and nickname ("~Adam")
        if len(message_origin.find_elements_by_xpath('.//span')) > 1:
            origin_name = message_origin.find_elements_by_xpath('.//span')[1]
            origin_emojis = origin_name.find_elements_by_xpath("./img")
            for e in origin_emojis:
                origin_info[1] += e.get_attribute('alt')
        groupfile_out.write('{MESSAGE ORIGIN}// %s\n' % origin_info)
    except:
        pass

    # groupfile_out.write MESSAGE TIME
    message_time = message.find_elements_by_xpath('.//span[contains(@dir,"auto")]')[-1].text
    groupfile_out.write('{MESSAGE TIME}// %s\n' % message_time)

    # try to expand READ MORE text
    try:
        button = message.find_element_by_xpath(
        './/span[@role="button" and contains(text(),"Read more")]')
        button.click()
    except:
        pass

    # try to find FORWARDED MESSAGES
    try:
        if message.find_element_by_xpath('.//span[@data-icon="highly-forwarded"]'):
            groupfile_out.write("{FORWARDED_HIGHLY}\n")
    except:
        pass
    try:
        if message.find_element_by_xpath('.//span[@data-icon="forwarded"]'):
            groupfile_out.write("{FORWARDED}\n")
    except:
        pass

    # QUOTES/REPLIES
    try:
        quote = message.find_element_by_xpath(
            ".//span[contains(@class,'quoted-mention')]"
            )
        quote_all = quote.find_element_by_xpath(
            '..')

        # QUOTE ORIGIN INFORMATION
        quote_orgin =             quote.find_element_by_xpath('../../div')
        origin_info = [e.text for e in quote_orgin.find_elements_by_xpath('./span')]
        if len(quote_orgin.find_elements_by_xpath('./span')) > 1:
            origin_name = quote_orgin.find_elements_by_xpath('./span')[1]
            origin_emojis = origin_name.find_elements_by_xpath("./img")
            for e in origin_emojis:
                origin_info[1] += e.get_attribute('alt')
        not_found_quote = False
        groupfile_out.write("....\n{REPLY_TO}// %s\n" % origin_info)
        groupfile_out.write("{REPLY_TEXT}// %s\n" % quote_all.text)

        # EMOJIS IN quotes
        reply_emojis = quote.find_elements_by_xpath("./img")
        if len(reply_emojis) > 0:
            reply_emojis = [e.get_attribute('alt') for e in reply_emojis]
            groupfile_out.write("{REPLY_EMOJIS}// %s\n" % reply_emojis)

        try:
            quote_icon = quote.find_element_by_xpath('../div').get_attribute('class')
            if "status-ptt" in quote_icon:
                groupfile_out.write("{REPLY_TYPE_AUDIO}//\n")
            elif "status-image" in quote_icon:
                groupfile_out.write("{REPLY_TYPE_IMAGE}//\n")
        except:
            pass

        # LOOK FOR REPLY ORIGINAL IMAGE/VIDEO
        quote_parent = quote.find_element_by_xpath('../../../..')
        try: # IMAGE
            s = quote_parent.find_element_by_xpath('.//div[contains(@style,"blob")]').get_attribute('style')
            quote_image_src = s[s.rfind('blob:') : s.rfind('");')]
            groupfile_out.write("{REPLY_IMAGE}// %s\n" % hash_blob(driver, quote_image_src))
        except:
            pass
        try: # VIDEO
            s = quote_parent.find_element_by_xpath('.//div[contains(@style,"base64")]').get_attribute('style')
            quote_video_src = md5h(s[s.rfind("base64")+7 : s.rfind('");')].encode())
            groupfile_out.write("{REPLY_THUMB}// %s\n" % quote_video_src)
        except:
            pass

        groupfile_out.write("....\n")
    except:
        pass

    # REPLIES WITHOUT QUOTED-MENTION (non-blob image only)
    images_in_quote = []
    if not_found_quote:
        try:
            quote_color = message.find_element_by_xpath('.//span[contains(@class,"bg-color-")]')
            quote = quote_color.find_element_by_xpath('..')

            # QUOTE ORIGIN INFORMATION
            quote_orgin =                 quote.find_element_by_xpath('./div/div/div[1]')
            origin_info = [e.text for e in quote_orgin.find_elements_by_xpath('./span')]
            if len(quote_orgin.find_elements_by_xpath('./span')) > 1:
                origin_name = quote_orgin.find_elements_by_xpath('./span')[1]
                origin_emojis = origin_name.find_elements_by_xpath("./img")
                for e in origin_emojis:
                    origin_info[1] += e.get_attribute('alt')
            groupfile_out.write("....\n{REPLY_TO}// %s\n" % origin_info)

            quote_images =                 quote.find_elements_by_xpath('./div/div/div[2]//img')
            images_in_quote = quote_images
            for image in quote_images:
                groupfile_out.write("{REPLY_IMAGE}// %s\n" % hash_blob(driver, image.get_attribute('src')))
            groupfile_out.write("....\n")
        except:
            pass

    # text messages
    message_container = message.find_elements_by_xpath(".//div[contains(@class,'copyable-text')]")
    if len(message_container) > 0:
        message_container = message_container[0]
        groupfile_out.write('{INFOCHECK}// %s\n' % message_container.get_attribute('data-pre-plain-text'))
        try: # text
            message_text = message_container.find_element_by_xpath(
            ".//span[contains(@class,'selectable-text invisible-space copyable-text')]"
            ).text
            groupfile_out.write("{TEXT}// %s\n" % message_text)
        except:
            pass

    # EMOJIS IN MESSAGES
    emojis = message.find_elements_by_xpath(".//img[contains(@class,'selectable-text invisible-space copyable-text')]")
    if len(emojis) > 0:
        emojis = [e.get_attribute('alt') for e in emojis]
        groupfile_out.write("{EMOJIS}// %s\n" % emojis)

    # images in messages
    images = message.find_elements_by_xpath(".//img[contains(@src,'blob')]")
    for image in images:
        if image not in images_in_quote:
            groupfile_out.write("{IMAGE}// %s\n" % hash_blob(driver, image.get_attribute('src')))

    # DELETED MESSAGES
    try:
        deleted = message.find_element_by_xpath('./div/div/div/div[2]')
        if deleted.text == "This message was deleted":
            groupfile_out.write("{MESSAGE DELETED}//\n")
            groupfile_out.write("\n========={}//\n\n")
            return
    except:
        pass

    # AUDIO IN MESSAGES
    try:
        if message.find_element_by_xpath('.//span[@data-icon="audio-play"]'):
            audio_time = message.find_element_by_xpath('./div/div/div/div/div[1]/div/div[2]/div[1]').text
            groupfile_out.write("{AUDIO_LENGTH}// %s\n" % audio_time)
            groupfile_out.write("\n========={}//\n\n")
            return
    except:
        pass

    # VIDEOS IN MESSAGES
    try:
        video_container = message.find_element_by_xpath(".//div[contains(@class,'video-thumb')]")
        video_time = video_container.find_element_by_xpath("./span").text
        video_thumb = video_container.find_element_by_xpath('./div[contains(@style,"background-image")]')
        s = video_thumb.get_attribute('style')
        video_thumb_url = md5h(s[s.rfind("base64")+7 : s.rfind('");')].encode())
        groupfile_out.write("{VIDEO_LENGTH}// %s\n" % video_time)
        groupfile_out.write("{VIDEO_THUMB}// %s\n" % video_thumb_url)
        groupfile_out.write("\n========={}//\n\n")
        return
    except:
        pass

    groupfile_out.write("\n========={}//\n\n")


# In[ ]:


def scrollUp(driver, time_lookback, logfile_out):
    previous_scrollto = None
    duplicates = 0

    while True:
        # try to find first message; checks time, and keeps scrolling if not early enough
        try:
            first_message = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//div[contains(@class,"message-")][1]')))
            time_first_message = first_message.find_elements_by_xpath('.//span[contains(@dir,"auto")]')[-1].text
            current_day = first_message.find_element_by_xpath('./../div[1]')
        except: # if only blue events, no messages
            current_day = driver.find_element_by_xpath('//*[@id="main"]/div[3]/div/div/div[last()]/div')
            time_first_message = "11:59 PM"

        if current_day.text == 'TODAY' or current_day.text == '':
            dt_first_message = datetime.combine(
                datetime.now().date(),
                datetime.strptime(time_first_message, "%I:%M %p").time(),
                )
        elif current_day.text == 'YESTERDAY':
            dt_first_message = datetime.combine(
                datetime.now().date() - timedelta(hours = 24),
                datetime.strptime(time_first_message, "%I:%M %p").time(),
                )
        else: # Regardless of actual day, assume it was 2 days ago
              # (This results in all messages still being captured)
            dt_first_message = datetime.combine(
                datetime.now().date() - timedelta(hours = 48),
                datetime.strptime(time_first_message, "%I:%M %p").time(),
                )

        # Break once we have scrolled up enough in messages
        if dt_first_message < time_lookback:
            logfile_out.write("INFO:        Breaking scroll: %s (%s %s)\n" % (dt_first_message, current_day.text, time_first_message))
            return True

        logfile_out.write("INFO:        Scroll: %s (%s %s)\n" % (dt_first_message, current_day.text, time_first_message))

        if current_day == previous_scrollto:
            duplicates += 1
            logfile_out.write("**EXCEPT**:  Scroll duplicate\n")
            time.sleep(5)

            if duplicates > 3:
                logfile_out.write("**FAILURE**: Exited scrolling because of duplicates\n")
                return False

        driver.execute_script("arguments[0].scrollIntoView(true)", current_day)
        previous_scrollto = current_day
        time.sleep(3)


# In[ ]:


def readMsgs(logfile_out, driver, groupfile_out, time_lookback):
    # try to CLICK JUMP DOWN ARROW
    try:
        jumpdown = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]//span[@data-icon="down"]')))
        jumpdown.click()
        time.sleep(3)
    except:
        pass

    logfile_out.write("--------------------------------------------------------\n")
    start_time = time.time()
    scrollSuccess = scrollUp(driver, time_lookback, logfile_out)
    if not scrollSuccess:
        scrollSuccess = scrollUp(driver, time_lookback, logfile_out)
    if scrollSuccess:
        logfile_out.write("SUCCESS:     Scroll messages successful (%s seconds)\n" % (time.time() - start_time))
        logfile_out.write("--------------------------------------------------------\n")
    else:
        raise Exception('Scroll failure')

    try:
        message_table = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//div[contains(@class,"message-")]/..')))
    except: # No messages found - only blue status events...or WhatsApp glitch, as usual
        logfile_out.write("**EXCEPT**:  No actual messages found\n")
        message_table = driver.find_element_by_xpath('//*[@id="main"]/div[3]/div/div/div[last()]')
    logfile_out.write("INFO:        Number of messages: %s\n" % len(message_table.find_elements_by_xpath('./div')))

    start_time = time.time()

    for message in message_table.find_elements_by_xpath('./div'):
        processMessage(driver, message, groupfile_out)

    logfile_out.write("SUCCESS:     Read messages successful (%s seconds)\n" % (time.time() - start_time))
    logfile_out.write("--------------------------------------------------------\n\n")



# In[ ]:


def traverse():
    # logging/output directories
    timez = datetime.utcnow().strftime("%Y-%m-%d_%H%M%SZ")
    log_out, group_count_directory, group_msg_directory = createDirectories(timez)

    # load driver
    driver = loadDriver(log_out)
    driver.get("https://web.whatsapp.com")

    minutes_lookback = int(sys.argv[2])

    time_lookback = datetime.now() - timedelta(minutes = minutes_lookback)
    log_out.write("New run: %s\n" % timez)
    log_out.write("Going back until %s\n" % time_lookback)
    print("New run: %s" % timez)

    print("Using user data: %s\n" % sys.argv[1])

    # We only save the different groups once; this works
    groups_column = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div/div/div')))
    s = groups_column.get_attribute("style")
    n_groups = int(int(s[s.find(" ") + 1:s.rfind("px")]) / 72)

    groups_checked = []

    while len(groups_checked) < n_groups:
        groups_all = groups_column.find_elements_by_xpath('./div')
        max_z = 0
        max_group = None
        found_group = False

        for group in groups_all:
            try:
                s = group.get_attribute('style')
            except: # Sometimes group out of frame
                continue

            group_z = int(int(s[s.find("(")+1 : s.find("px)")]) / 72)
            if group_z > max_z:
                max_z = group_z
                max_group = group

            group_side_title = group.find_element_by_xpath('./div/div/div[2]/div[1]/div[1]//span[@title]').get_attribute('title')

            if group_side_title not in groups_checked:
                groups_checked.append(group_side_title)
                group.click()

                title = driver.find_element_by_xpath('//*[@id="main"]/header/div[2]/div[1]/div/span').text

                print(title)
                log_out.write("\nTitle: %s\n" % title)

                try:
                    subtitle = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/header/div[2]/div[2]/span'))).text
                except:
                    subtitle = None

                if subtitle == None or                 subtitle.startswith('last seen') or                 subtitle.startswith('click here for contact info') or                 subtitle.startswith('online'):
                    log_out.write("Not a group\n\n")
                    continue

                title_innerHTML = driver.find_element_by_xpath('//*[@id="main"]/header/div[2]/div[1]/div/span').get_attribute('innerHTML')
                log_out.write("Title HTML: %s\n--------------------------------------------------------\n" % title_innerHTML)
                found_group = True

                try:
                    group_pp =                 WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/header/div[1]/div/img'))).get_attribute('src')
                    if "base64" in group_pp:
                        group_pp_b64 = group_pp[group_pp.rfind("base64")+7 : ].encode()
                        group_pp_id = md5h(group_pp_b64)
                        group_uid = group_pp_id
                    else:
                        group_pp_id = group_pp[group_pp.rfind("%2F")+3 : group_pp.rfind("_n.")+2]
                        group_uid = group_pp[group_pp.rfind('u=')+2 : group_pp.rfind('%40')]

                    log_out.write("UID: %s\n" % group_uid)
                    log_out.write("PPID: %s\n" % group_pp_id)
                    log_out.write("PP Link: %s\n--------------------------------------------------------\n" % group_pp)
                except:
                    psUid = title_innerHTML.encode()
                    group_uid = hashlib.md5(psUid).hexdigest()
                    log_out.write("PSUID: %s\n--------------------------------------------------------\n"% group_uid)

                # COUNT MEMBERS
                group_count_file = group_count_directory + group_uid + ".txt"
                group_count_out = open(group_count_file, "w")

                group_count_out.write(title + "\n\n")
                try:
                    countMembers(log_out, driver, group_count_out)
                except:
                    log_out.write("**EXCEPT**:  GROUP COUNT EXITED WITH ERROR; RETRYING\n")
                    time.sleep(20)
                    try:
                        group_count_out.close()
                        group_count_out = open(group_count_file, "w")
                        group_count_out.write(title + "\n\n")
                        countMembers(log_out, driver, group_count_out)
                    except:
                        log_out.write("**FAILURE**: GROUP COUNT FAILED\n")
                group_count_out.close()

                # READ MESSAGES
                group_msg_file = group_msg_directory + group_uid + ".txt"
                group_msg_out = open(group_msg_file, "w")

                group_msg_out.write(title + "\n\n")
                try:
                    readMsgs(log_out, driver, group_msg_out, time_lookback)
                except:
                    log_out.write("**EXCEPT**:  MESSAGE READ EXITED WITH ERROR; RETRYING\n")
                    time.sleep(20)
                    try:
                        group_msg_out.close()
                        group_msg_out = open(group_msg_file, "w")
                        group_msg_out.write(title + "\n\n")
                        readMsgs(log_out, driver, group_msg_out, time_lookback)
                    except:
                        log_out.write("**FAILURE**: MESSAGE READ FAILED\n")
                group_msg_out.close()

        if found_group:
            driver.get("https://web.whatsapp.com")
            groups_column = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div[1]/div/div')))
        else:
            try:
                driver.execute_script("arguments[0].scrollIntoView();", max_group)
                time.sleep(5)
                groups_column = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div[1]/div/div')))
            except:
                driver.get("https://web.whatsapp.com")
                groups_column = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div[1]/div/div')))

    if len(groups_checked) == n_groups:
        log_out.write("\nSUCCESS: All group count matched (%s)\n" % n_groups)
    else:
        groups_column = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div/div/div')))
        s = groups_column.get_attribute("style")
        n_groups_final = int(int(s[s.find(" ") + 1:s.rfind("px")]) / 72)

        if len(groups_checked) == n_groups_final:
            log_out.write("\nSUCCESS: Final group count matched (Initial %s / Final %s)\n" % (n_groups, n_groups_final))
        else:
            log_out.write("\n**EXCEPT**:  GROUP COUNTS DID NOT MATCH\n**EXCEPT**:  Found %s\n**EXCEPT**:  Start %s\n**EXCEPT**:  Final %s\n" % (len(groups_checked), n_groups, n_groups_final))

    driver.close()
    log_out.close()
    print("\nFinished\n")


# In[ ]:


def main():
    traverse()


# In[ ]:


if __name__ == "__main__":
    main()
