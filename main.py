from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

app = App(
    token="TOKEN_AQUI",
    signing_secret="SIGNING_SECRET_AQUI"
)

CANAL_COMUNICADOS = "#comunicações-"

@app.command("/comunicado")
def comunicado(ack, respond, command):
    ack()

    texto = command["text"]

    if not texto:
        respond("Escreva uma mensagem após o comando.")
        return

    app.client.chat_postMessage(
        channel=CANAL_COMUNICADOS,
        text=f"📢 *Comunicado Guru Comercial*\n\n{texto}"
    )

    respond("✅ Comunicado enviado pelo Guru Comercial.")

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.route("/", methods=["POST"])
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(port=3000)