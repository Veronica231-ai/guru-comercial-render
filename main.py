import os

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

flask_app = Flask(__name__)

CANAL_COMUNICADOS = "#comunicações-"

@app.command("/comunicado")
def comunicado(ack, command):

    ack()

    texto = command["text"]



texto = request.form.get("text", "")

app.client.chat_postMessage(
    channel=CANAL_COMUNICADOS,
    text=f"📢 {texto}"
)

handler = SlackRequestHandler(app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)