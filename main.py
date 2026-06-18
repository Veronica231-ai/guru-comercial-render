import os
import json
import urllib.request

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

flask_app = Flask(__name__)

CANAL_COMUNICADOS = "#comunicações-"
CANAL_RESPOSTAS = "#nps-repostas"

GOOGLE_SHEETS_URL = "https://script.google.com/macros/s/AKfycbysiUIje08OUUmB0XxtMsQ8Z9_jj46ktl82gSmhuIj24XnB5KmTEiJzNrw6qDrnGnFq/exec"


def salvar_no_sheets(tipo, nome, usuario, resposta):
    try:
        dados = json.dumps({
            "tipo": tipo,
            "nome": nome,
            "usuario": usuario,
            "resposta": resposta
        }).encode("utf-8")

        req = urllib.request.Request(
            GOOGLE_SHEETS_URL,
            data=dados,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        urllib.request.urlopen(req, timeout=5)

    except Exception as erro:
        print("Erro ao salvar no Google Sheets:", erro)


@app.command("/comunicado")
def comunicado(ack, body, respond):
    ack()

    texto = body.get("text", "").strip()

    if not texto:
        respond("Digite a mensagem depois do comando. Exemplo: /comunicado texto do comunicado")
        return

    app.client.chat_postMessage(
        channel=CANAL_COMUNICADOS,
        text=f"📢 {texto}",
        mrkdwn=True,
        unfurl_links=True
    )

    respond("Comunicado enviado ✅")


@app.command("/pesquisa")
def pesquisa(ack, body, respond):
    ack()

    texto = body.get("text", "").strip()

    if not texto:
        respond("Digite assim: /pesquisa Nome do treinamento | Link do material")
        return

    partes = texto.split("|", 1)
    treinamento = partes[0].strip()
    link_material = partes[1].strip() if len(partes) > 1 else ""

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Pesquisa de satisfação* 🔥\n\nQueremos te ouvir e entender o que você achou do treinamento *{treinamento}*.\n\nSua opinião é muito importante para que possamos evoluir cada vez mais nossos conteúdos, treinamentos e iniciativas.\n\nConta pra gente como foi sua experiência!\n\n_Leva menos de 1 minuto... seu café nem vai esfriar_ 😅"
            }
        }
    ]

    if link_material:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📚 Conferir material do treinamento",
                        "emoji": True
                    },
                    "url": link_material
                }
            ]
        })

    blocks.extend([
        {"type": "divider"},
        {
            "type": "section",
            "block_id": f"pesquisa_{treinamento}",
            "text": {
                "type": "mrkdwn",
                "text": "*📊 Como você avalia este treinamento?*"
            },
            "accessory": {
                "type": "radio_buttons",
                "options": [
                    {"text": {"type": "plain_text", "text": "⭐ Muito Insatisfeito", "emoji": True}, "value": "1"},
                    {"text": {"type": "plain_text", "text": "⭐⭐ Insatisfeito", "emoji": True}, "value": "2"},
                    {"text": {"type": "plain_text", "text": "⭐⭐⭐ Neutro", "emoji": True}, "value": "3"},
                    {"text": {"type": "plain_text", "text": "⭐⭐⭐⭐ Satisfeito", "emoji": True}, "value": "4"},
                    {"text": {"type": "plain_text", "text": "⭐⭐⭐⭐⭐ Muito Satisfeito", "emoji": True}, "value": "5"}
                ],
                "action_id": "resposta_pesquisa"
            }
        }
    ])

    app.client.chat_postMessage(
        channel=CANAL_COMUNICADOS,
        text=f"Pesquisa de satisfação | {treinamento}",
        blocks=blocks
    )

    respond("Pesquisa enviada ✅")


@app.action("resposta_pesquisa")
def resposta_pesquisa(ack, body, client):
    ack()

    usuario_id = body["user"]["id"]

    info_usuario = client.users_info(user=usuario_id)
    usuario_nome = (
        info_usuario["user"].get("real_name")
        or info_usuario["user"].get("profile", {}).get("display_name")
        or info_usuario["user"].get("name")
        or usuario_id
    )

    canal_origem = body["channel"]["id"]

    opcao = body["actions"][0]["selected_option"]
    nota = opcao["value"]
    texto_nota = opcao["text"]["text"]

    titulo_mensagem = body["message"].get("text", "Pesquisa de satisfação")
    treinamento = titulo_mensagem.replace("Pesquisa de satisfação | ", "")

    client.chat_postMessage(
        channel=CANAL_RESPOSTAS,
        text=(
            "📊 *Nova resposta de pesquisa*\n\n"
            f"*Treinamento:* {treinamento}\n"
            f"*Usuário:* <@{usuario_id}>\n"
            f"*Nota:* {nota} - {texto_nota}"
        )
    )

    salvar_no_sheets(
        tipo="Pesquisa",
        nome=treinamento,
        usuario=usuario_nome,
        resposta=f"{nota} - {texto_nota}"
    )

    client.chat_postEphemeral(
        channel=canal_origem,
        user=usuario_id,
        text=f"Resposta registrada ✅\nSua nota foi: {texto_nota}"
    )


handler = SlackRequestHandler(app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)