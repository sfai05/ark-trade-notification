#!/usr/bin/env python
# coding: utf-8
import os, hashlib, sys, glob, urllib
import requests
import olefile
import pandas as pd
from functools import partial
from datetime import datetime
from google.cloud import storage

ARK_DOMAIN = 'https://www.ark-funds.com/auto/trades/'
ARK_FILES = {'ARKG': 'ARK_ARKG_Trades.xls', 'ARKK': 'ARK_ARKK_Trades.xls', 'ARKQ': 'ARK_ARKQ_Trades.xls', 'ARKW': 'ARK_ARKW_Trades.xls'}
GCS_BUCKET = os.environ.get('GCS_BUCKET', 'bucket-for-store-history')
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'telegram-bot-token')
BOT_CHATID = os.environ.get('BOT_CHATID', 'telegram-dest-group-id')


def md5sum(filename):
    with open(filename, mode='rb') as f:
        d = hashlib.md5()
        for buf in iter(partial(f.read, 128), b''):
            d.update(buf)
    return d.hexdigest()


def download_from_remote(url, file_name):
    # open in binary mode
    with open(file_name, "wb") as file:
        # get request
        response = requests.get(url)
        # write to file
        file.write(response.content)


def generate_message_from_file(src):
    with olefile.OleFileIO(src) as ole:
        sheet = ole.openstream('Workbook')
        df = pd.read_excel(sheet, engine='xlrd')
        df = df.iloc[3:]

    # Compose Message
    message = ['%s %s' % (df.iloc[0][1], df.iloc[0][0])]
    for index, row in df.iterrows():
        symbol = row[4]
        price = requests.get('https://finnhub.io/api/v1/quote?symbol=%s&token=brfiks7rh5raper7b7eg' % symbol).json()['o']
        message.append('%s : <b>%s</b> %s ( <pre>%s</pre> ) %s @ $%s (USD $%s)' % (row[2], row[3], urllib.parse.quote(row[6]), row[4], row[7], price,
                                                                                   "{:,}".format(round(float(row[7]) * float(price)))))

    return message


def check_trade_list():
    NO_UPDATE = b'Note: There are no trades listed for the current day'
    url = 'https://ark-funds.com/auto/getidt.php'
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        })
    remote = urllib.request.urlopen(req)
    message = remote.read()
    print(message)
    if message == NO_UPDATE:
        return False
    else:
        return True


def blob_exists(bucket_name, filename):
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(filename)
    return blob.exists()


def upload_blob(bucket_name, filename):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    return blob.upload_from_filename(filename)


def telegram_bot_sendtext(bot_message):
    bot_token = BOT_TOKEN
    bot_chatID = BOT_CHATID
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=HTML&text=' + bot_message
    response = requests.get(send_text)
    return response.json()


def main(data, context):
    # Download the latest file
    renamed_files = []
    if check_trade_list() is not False:
        for symbol, ark_file in ARK_FILES.items():
            download_from_remote('%s%s' % (ARK_DOMAIN, ark_file), ark_file)
            #  Reanme the file
            md5 = md5sum(ark_file)
            refile_name = '%s-%s-%s.xls' % (ark_file.replace('.xls', ''), datetime.today().strftime('%Y%m%d'), md5)
            renamed_files.append(refile_name)
            os.rename(ark_file, refile_name)
    else:
        print('No update so far')

    if len(renamed_files) > 0:
        messages = []
        for renamed_file in renamed_files:
            is_exist = blob_exists(GCS_BUCKET, renamed_file)
            if is_exist is False:
                # Upload the file, process the message
                upload_blob(GCS_BUCKET, renamed_file)
                messages.append(generate_message_from_file(renamed_file))
        for message in messages:
            res = telegram_bot_sendtext("\n".join(message))
            print(res)
    return True
