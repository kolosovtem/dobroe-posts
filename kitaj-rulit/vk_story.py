#!/usr/bin/env python3
"""Публикует одну готовую сторис Китай RUлит в истории сообщества ВК.

Использование:
  VK_TOKEN=<ключ сообщества> python3 -I vk_story.py <путь к jpg> [--link]

Ключ берётся только из переменной окружения VK_TOKEN, в репозиторий не пишется.
--link добавляет на сторис кнопку «Подробнее» со ссылкой на kitaj-rulit.ru.
Печатает JSON: {"ok": true, "story_id": ..., "owner_id": ...} или {"ok": false, "error": ...}.
"""
import json, os, sys, time, uuid, urllib.request, urllib.parse

API = 'https://api.vk.com/method/'
V = '5.199'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
GROUP = 'kitaj_rulit'


def call(method, **params):
    params.update(access_token=os.environ['VK_TOKEN'], v=V)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API + method, data=data, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    if 'error' in res:
        e = res['error']
        raise RuntimeError('%s: %s (код %s)' % (method, e.get('error_msg'), e.get('error_code')))
    return res['response']


def upload(url, path):
    boundary = uuid.uuid4().hex
    with open(path, 'rb') as f:
        img = f.read()
    body = (('--%s\r\nContent-Disposition: form-data; name="file"; filename="story.jpg"\r\n'
             'Content-Type: image/jpeg\r\n\r\n' % boundary).encode() + img +
            ('\r\n--%s--\r\n' % boundary).encode())
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary, 'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)
    if 'response' in res:
        res = res['response']
    if 'upload_result' not in res:
        raise RuntimeError('upload: ' + json.dumps(res, ensure_ascii=False)[:300])
    return res['upload_result']


def main():
    path = sys.argv[1]
    link = '--link' in sys.argv
    try:
        g = call('groups.getById', group_id=GROUP)
        g = g['groups'][0] if isinstance(g, dict) else g[0]
        gid = g['id']
        p = dict(add_to_news=1, group_id=gid)
        if link:
            p.update(link_text='learn_more', link_url='https://kitaj-rulit.ru/')
        # Загрузчик ВК (go upload) примерно через раз отвечает "go upload error" (код 1)
        # или HTTP 405 - берём новый адрес загрузки и пробуем ещё, до 5 раз.
        for attempt in range(5):
            try:
                srv = call('stories.getPhotoUploadServer', **p)
                ur = upload(srv['upload_url'], path)
                break
            except Exception as e:
                if attempt == 4:
                    raise
                time.sleep(3)
        saved = call('stories.save', upload_results=ur)
        item = saved['items'][0]
        print(json.dumps({'ok': True, 'story_id': item['id'], 'owner_id': item['owner_id'],
                          'group': g.get('screen_name')}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
