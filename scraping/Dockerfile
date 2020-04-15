FROM python:3.8.0

# INSTALL chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
  && apt-get -y update \
  && apt-get install -y google-chrome-stable

# INSTALL chromedriver
RUN apt-get install -yqq unzip \
  && wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip \
  && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
  && apt-get install -y cron

# set display port to avoid crash
ENV DISPLAY=:99

# VZWA custom directories
RUN mkdir /home/vzwa/ \
  && pip3 install selenium \
  && pip3 install twilio

COPY . /home/vzwa/

RUN mv /home/vzwa/entrypoint.sh /entrypoint.sh \
  && chmod +x /entrypoint.sh

ENTRYPOINT /entrypoint.sh
