from flask import Flask, request

# 載入 json 標準函式庫，處理回傳的資料格式
import json
import os
import requests

# 載入 LINE Message API 相關函式庫
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction, LocationAction, MessageEvent, TextMessage
from dotenv import load_dotenv, find_dotenv

# Gemini
import google.generativeai as genai

# Whisper
import whisper

# Storage
import firebase_admin
from firebase_admin import credentials, initialize_app, storage
import firebase_admin.storage
from google.cloud import storage
from google.oauth2 import service_account

# dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

# gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"),)

# Set up the model
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
}

safety_settings = [
    {
      "category": "HARM_CATEGORY_HARASSMENT",
      "threshold": "BLOCK_NONE"
    },
    {
      "category": "HARM_CATEGORY_HATE_SPEECH",
      "threshold": "BLOCK_NONE"
    },
    {
      "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",    
      "threshold": "BLOCK_NONE"
    },
    {
      "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
      "threshold": "BLOCK_NONE"
    },
]

system_instruction = "你的名字叫Aetheria， \
                    主要幫助TOEFL考生獨立口說的練習，15秒準備，45秒發言\
                    給予考生TOP練習題目，\
                    並根據他們的口說內容進行評分，分別有General Description、Delivery、Language Use、Topic Development，總分5分，\
                    使用繁體中文評論與回答，只有題目使用英文，\
                    並且回覆格式為txt，不要用markdown的符號"
model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config,
                              system_instruction=system_instruction,
                              safety_settings=safety_settings)
chat = model.start_chat(history=[])

def gemini_ai(text):
    response = chat.send_message(text)
    return response.text

# whisper
def whisper_ai(fileName):
    model = whisper.load_model("base")
    result = model.transcribe(fileName)
    return result["text"]

# line bot
app = Flask(__name__)
@app.route("/", methods=['POST'])

def linebot():

    body = request.get_data(as_text=True)                    # 取得收到的訊息內容
    try:
        json_data = json.loads(body)                         # json 格式化訊息內容
        line_bot_api = LineBotApi(os.environ.get("LINE_BOT_TOKEN")) # 確認 token 是否正確
        handler = WebhookHandler(os.environ.get("LINE_BOT_SECRET")) # 確認 secret 是否正確
        signature = request.headers['X-Line-Signature']      # 加入回傳的 headers
        handler.handle(body, signature)                      # 綁定訊息回傳的相關資訊
        tk = json_data['events'][0]['replyToken']            # 取得回傳訊息的 Token
        type = json_data['events'][0]['message']['type']     # 取得 LINe 收到的訊息類型
        
        if type =='text':
            msg = json_data['events'][0]['message']['text']  # 取得 LINE 收到的文字訊息
            reply = gemini_ai(msg)
            
        elif type =='audio':
            msgID = json_data['events'][0]['message']['id']
            user_id = json_data['events'][0]['source']['userId']
            
            message_content = line_bot_api.get_message_content(msgID)
            filename = f'{user_id}.m4a'

            Path = filename
            
            with open(Path, 'wb') as fd:
                fd.write(message_content.content)
                
            msg = whisper_ai(filename)
            
            reply = "你的回答：" + msg + "\n" + "\n" + gemini_ai(msg)
            
            os.remove(Path)

        else:
            reply = '你傳的不是文字呦～'       
        line_bot_api.reply_message(tk,TextSendMessage(reply))# 回傳訊息
    except:
        print(body)                                          # 如果發生錯誤，印出收到的內容
    return 'OK'                                              # 驗證 Webhook 使用，不能省略

if __name__ == "__main__":
    app.run()


#ngrok http 127.0.0.1:5000