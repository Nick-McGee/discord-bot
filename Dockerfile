FROM python:3.10

WORKDIR /bot

COPY ./requirements.txt /bot
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

COPY ./src /bot/src

CMD ["python", "src/bot.py"]
