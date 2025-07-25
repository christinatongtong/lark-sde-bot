#!/usr/bin/env python
# --coding:utf-8--

import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from os import path
import json
from pickle import OBJ
from urllib import request, parse
import requests
#from scratch import call_claude, SYSTEM_PROMPT, git_push
from claude import git_push
from claude_cleaner import GitProcessor
from dotenv import load_dotenv
import traceback

load_dotenv()

APP_SECRET = os.getenv('APP_SECRET')
APP_ID = os.getenv('APP_ID')
APP_VERIFICATION_TOKEN = os.getenv('APP_VERIFICATION_TOKEN')


class RequestHandler(BaseHTTPRequestHandler):

    seen_events = set()

    def do_POST(self):
        # 解析请求 body
        req_body = self.rfile.read(int(self.headers['content-length']))
        obj = json.loads(req_body.decode("utf-8"))

        print("---------------start here-----------------")
        print("REQ BODY OBJECT: ", obj)

        if obj.get("type", "") == "url_verification":
            self.handle_request_url_verify(obj)
            return


        # 校验 verification token 是否匹配，token 不匹配说明该回调并非来自开发平台
        token = obj['header'].get("token", "")
        if token != APP_VERIFICATION_TOKEN:
            print("\nverification token not match, token =", token)
            self.response("")
            return

        # check if duplicate event
        event_id = obj['header']['event_id']

        if event_id in RequestHandler.seen_events:
            print(f"duplicate event ignored: '{event_id}'")
            self.response("")
            return
        RequestHandler.seen_events.add(event_id)

        # Clear seen_events if it gets large
        if len(RequestHandler.seen_events) >= 30:
            RequestHandler.seen_events.clear()

        print(f"Added event_id to seen_events: '{event_id}'")
        print(f"Total seen_events now: {len(RequestHandler.seen_events)}")

        event = obj.get("event", {})
        if 'message' in event.keys():
            self.handle_message(event)
            return


    def handle_request_url_verify(self, post_obj):
        # 原样返回 challenge 字段内容
        challenge = post_obj.get("challenge", "")
        rsp = {'challenge': challenge}
        self.response(json.dumps(rsp))
        return

    def handle_message(self, event):
        # 此处只处理 text 类型消息，其他类型消息忽略
        msg_type = event['message'].get("message_type", "")
        if msg_type != "text":
            print("unknown msg_type =", msg_type)
            self.response("")
            return

        # 调用发消息 API 之前，先要获取 API 调用凭证：tenant_access_token
        access_token = self.get_tenant_access_token()

        if access_token == "":
            self.response("")
            return

        # 机器人 echo 收到的消息
        PM_msg = json.loads(event['message']['content']).get("text", "")

        if len(PM_msg) < 10:
            self.response("")
            return

        self.send_message(access_token, event, f"🤖 Processing your request, I'll send PR link when ready...")

        # PR_url = git_push(PM_msg)
        git_processor = GitProcessor(PM_msg)
        PR_url = git_processor.actions()

        # send each thinking message
        self.send_message(access_token, event, f"Pull Request created successfully! Click here to view: {PR_url}")

        print("DONE")
        self.response("{}")  # Send empty JSON object
        return

    def response(self, body):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body.encode())


    def get_tenant_access_token(self):
        url = "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal"
        headers = {
            "Content-Type" : "application/json"
        }
        req_body = {
            "app_id": APP_ID,
            "app_secret": APP_SECRET
        }

        data = bytes(json.dumps(req_body), encoding='utf8')
        req = request.Request(url=url, data=data, headers=headers, method='POST')
        try:
            response = request.urlopen(req)
        except Exception as e:
            print(f"Error getting tenant access token: {str(e)}")
            return ""

        rsp_body = response.read().decode('utf-8')
        rsp_dict = json.loads(rsp_body)
        code = rsp_dict.get("code", -1)
        if code != 0:
            print("get tenant_access_token error, code =", code)
            return ""
        return rsp_dict.get("tenant_access_token", "")

    def send_message(self, token, event, text):
        if event['message']['chat_type'] == "p2p":
            id = event['sender']['sender_id'].get("open_id")
        elif event['message']['chat_type'] == "group":
            id = event['message'].get("chat_id")

        url = "https://open.larksuite.com/open-apis/im/v1/messages"

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        }

        query_params = {
            "receive_id_type": "open_id"
        }

        req_body = {
            "receive_id": id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }

        data = bytes(json.dumps(req_body), encoding='utf8')

        try:
            # BOT REPLYING AS A REQUEST
            response = requests.request(
                "POST",
                url,
                params=query_params,
                headers=headers,
                data=data
            )

        except Exception as e:
            print(f"Error sending message: {str(e)}")
            return

        rsp_body = response.text
        print("rsp_body: ", rsp_body)
        rsp_dict = json.loads(rsp_body)
        code = rsp_dict.get("code", -1)
        if code != 0:
            print("send message error, code = ", code, ", msg =", rsp_dict.get("msg", ""))

def run():
    test_event = {
    'schema': '2.0',
    'header': {
        'event_id': '3dfa140733d1744b30efee001deaa8c4',
        'token': 'FqxQFraGKf2YNoAEk97xUfmFTCDJxKOK',
        'create_time': '1752736014686',
        'event_type': 'im.message.receive_v1',
        'tenant_key': '14a73a6a10dd1743',
        'app_id': 'cli_a8fcd5e4d1b9d010'
    },
    'event': {
        'message': {
            'chat_id': 'oc_bd3057ed9ac8db59ea9aba9a299c4eac',
            'chat_type': 'p2p',
            'content': '{"text":"hi"}',
            'create_time': '1752736014456',
            'message_id': 'om_x100b48be5e2ba0900d60eb30be638ad',
            'message_type': 'text',
            'update_time': '1752736014456'
        },
        'sender': {
            'sender_id': {
                'open_id': 'ou_6e8512ef2178e21dece8b91d10db1d07',
                'union_id': 'on_0903fc993554ee68afee67f84b32d438',
                'user_id': 'g88c263e'
            },
            'sender_type': 'user',
            'tenant_key': '14a73a6a10dd1743'
        }
    }
    }

    class MockRequestHandler(RequestHandler):
        def __init__(self):
            # Don't call parent constructor to avoid HTTP objects
            pass

        def response(self, body):
            # Mock response method
            print(f"Response: {body}")

        def send_message(self, token, event, text):
            # Mock send_message method
            print(f"Would send message: {text}")
            print(f"To user: {event['sender']['sender_id'].get('open_id')}")
            return True

    # Test the handler
    handler = MockRequestHandler()
    event = test_event.get("event", {})

    print("=== Testing bot.py locally ===")
    print(f"Test message: {json.loads(event['message']['content'])['text']}")
    print("Processing...")

    handler.handle_message(event)

    print("=== Test completed ===")



def run_server():
    port = int(os.getenv('PORT'))
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Server starting on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
