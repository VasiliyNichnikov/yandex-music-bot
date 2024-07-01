# syntax=docker/dockerfile:1

FROM python:3.10

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

COPY . .

RUN chmod +x wait-for-it.sh