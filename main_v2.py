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


@app.command("/guru-news")
def guru_news(ack, body, client):
    ack()

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "guru_news_modal",
            "title": {
                "type": "plain_text",
                "text": "Guru News"
            },
            "submit": {
                "type": "plain_text",
                "text": "Publicar"
            },
            "close": {
                "type": "plain_text",
                "text": "Cancelar"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "titulo_block",
                    "label": {
                        "type": "plain_text",
                        "text": "📰 Título da edição"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "titulo_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Ex: Guru News | Edição #01"
                        }
                    }
                },
                {
                    "type": "input",
                    "block_id": "banner_block",
                    "label": {
                        "type": "plain_text",
                        "text": "🖼️ Link do banner"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "banner_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Cole aqui o link do arquivo do Slack"
                        }
                    }
                },
                {
                    "type": "input",
                    "block_id": "destaques_block",
                    "label": {
                        "type": "plain_text",
                        "text": "📢 Destaques da quinzena"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "destaques_input",
                        "multiline": True
                    }
                }
            ]
        }
    )


handler = SlackRequestHandler(app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)