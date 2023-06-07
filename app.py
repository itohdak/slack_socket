from datetime import timedelta
from datetime import datetime as dt
import json
import logging
import os
import re
from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=logging.DEBUG)

app = App(token=os.environ["SLACK_BOT_TOKEN"])

def load_user_data():
    return json.load(open("data.json"))

def dump_user_data(data):
    json.dump(data, open("data.json", "w"))
    return True

def mention_next(client, body, skip=False):
    channel_id = body["channel"]["id"]
    ts = body["message_ts"]
    if skip:
        user_id = re.search(
            r'<@([A-Z0-9]+)> \u30d2\u30a2\u30ea\u30f3\u30b0\u3092\u304a\u9858\u3044\u3057\u307e\u3059\u3002',
            body["message"]["text"]
        ).group(1)
        next_user_id = select_next(client, skip_user_id=user_id)
    else:
        next_user_id = select_next(client)
    text = "<@{}> ヒアリングをお願いします。".format(next_user_id)
    client.chat_postMessage(text=text, channel=channel_id, thread_ts=ts)

def select_next(client, skip_user_id=None):
    data = load_user_data()
    data = sorted(data, key=lambda x: (x["count"], x["id"]))
    i = 0
    while i < len(data) and "ignore" in data[i] and data[i]["ignore"] > dt.now().timestamp():
        i += 1
    if i == len(data):
        # アサインできる要員がいない（全員スキップした場合）
        # ほぼありえない
        pass
    next_user = data[i]
    data[i]["count"] += 1
    if skip_user_id:
        for d in data:
            if d["user_id"] == skip_user_id:
                d["ignore"] = (dt.now() + timedelta(days=1)).timestamp()
                d["count"] -= 1
    dump_user_data(data)
    return next_user["user_id"]

def store_users(users):
    data = load_user_data()
    user_id_exist = set([d["user_id"] for d in data])
    if len(data) == 0:
        count_init = 0
    else:
        count_min = min([d["count"] for d in data])
        count_max = max([d["count"] for d in date])
        if count_min == count_max:
            count_init = count_min-1
        else:
            count_init = count_min
    for u in users:
        if u not in user_id_exist:
            data.append({
                "id": len(user_id_exist),
                "user_id": u,
                "count": count_init
            })
            user_id_exist.add(u)
    dump_user_data(data)
    return True
        
# イベント API
@app.message("list")
def handle_messge_evnts(message, say):
    say(f"こんにちは <@{message['user']}> さん！")

# ショートカットとモーダル
@app.shortcut("my_callback")
def handle_shortcut(ack, body: dict, client: WebClient):
    ack()
    mention_next(client, body)

@app.shortcut("skip")
def handle_shortcut(ack, body: dict, client: WebClient):
    ack()
    mention_next(client, body, skip=True)

@app.shortcut("modify_hearing_members")
def handle_shortcut(ack, body: dict, client: WebClient):
    ack()
    view = json.load(open("./modify_view.json"))
    view["blocks"][0]["element"]["initial_users"] = [u["user_id"]for u in json.load(open("data.json"))]
    client.views_open(
        trigger_id=body["trigger_id"],
        view=view
    )

@app.view("modify_callback")
def handle_view_submission(ack, view, logger):
    users = list(view['state']['values'].values())[0]['multi_users_select-action']['selected_users']
    store_users(users)
    ack()

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

