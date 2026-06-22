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

        resposta_google = urllib.request.urlopen(req, timeout=5)
        retorno = json.loads(resposta_google.read().decode("utf-8"))

        return retorno.get("status", "erro")

    except Exception as erro:
        print("Erro ao salvar no Google Sheets:", erro)
        return "erro"


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

    status_salvamento = salvar_no_sheets(
        tipo="Pesquisa",
        nome=treinamento,
        usuario=usuario_nome,
        resposta=f"{nota} - {texto_nota}"
    )

    if status_salvamento == "duplicate":
        client.chat_postEphemeral(
            channel=canal_origem,
            user=usuario_id,
            text="⚠️ Esta pesquisa já foi respondida por você. Sua resposta anterior já está registrada."
        )
        return

    if status_salvamento == "saved":
        client.chat_postMessage(
            channel=CANAL_RESPOSTAS,
            text=(
                "📊 *Nova resposta de pesquisa*\n\n"
                f"*Treinamento:* {treinamento}\n"
                f"*Usuário:* <@{usuario_id}>\n"
                f"*Nota:* {nota} - {texto_nota}"
            )
        )

        client.chat_postEphemeral(
            channel=canal_origem,
            user=usuario_id,
            text=f"Resposta registrada ✅\nSua nota foi: {texto_nota}"
        )
        return

    client.chat_postEphemeral(
        channel=canal_origem,
        user=usuario_id,
        text="⚠️ Não foi possível registrar sua resposta agora. Tente novamente em alguns instantes."
    )


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
                "text": "Pré-visualizar"
            },
            "close": {
                "type": "plain_text",
                "text": "Cancelar"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "banner_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "🖼️ Link do banner ou GIF"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "banner_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Cole o link da imagem ou GIF"
                        }
                    }
                },
                {
                    "type": "input",
                    "block_id": "titulo_block",
                    "optional": True,
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
                    "block_id": "periodo_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "📅 Período"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "periodo_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Ex: 01 a 15 de Julho"
                        }
                    }
                },
                {
                    "type": "input",
                    "block_id": "destaques_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "📢 Destaques da quinzena"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "destaques_input",
                        "multiline": True
                    }
                },
                {
                    "type": "input",
                    "block_id": "materiais_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "📚 Materiais"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "materiais_input",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Um por linha: Nome do material | link"
                        }
                    }
                },
                {
                    "type": "input",
                    "block_id": "imagem_dados_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "📊 Link da imagem dos dados"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "imagem_dados_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Cole o link da imagem dos dados"
                        }
                    }
                },
                {
                    "type": "input",
                    "block_id": "link_report_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "📈 Link do report completo"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "link_report_input"
                    }
                },
                {
                    "type": "input",
                    "block_id": "reconhecimentos_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "🏆 Reconhecimentos"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "reconhecimentos_input",
                        "multiline": True
                    }
                },
                {
                    "type": "input",
                    "block_id": "gif_reconhecimento_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "🎞️ Link do GIF de reconhecimento"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "gif_reconhecimento_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Cole o link do GIF"
                        }
                    }
                },
                {
                    "type": "input",
                    "block_id": "eventos_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "📅 Próximos eventos"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "eventos_input",
                        "multiline": True
                    }
                },
                {
                    "type": "input",
                    "block_id": "dica_block",
                    "optional": True,
                    "label": {
                        "type": "plain_text",
                        "text": "💡 Dica da semana"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "dica_input",
                        "multiline": True
                    }
                }
            ]
        }
    )


def guru_news_preview(ack, body, client, view):
    ack()

    usuario_id = body["user"]["id"]
    valores = view["state"]["values"]

def pegar_valor(block_id, action_id):
    valor = valores.get(block_id, {}).get(action_id, {}).get("value")
    return valor.strip() if valor else ""

    banner = pegar_valor("banner_block", "banner_input")
    titulo = pegar_valor("titulo_block", "titulo_input")
    periodo = pegar_valor("periodo_block", "periodo_input")
    destaques = pegar_valor("destaques_block", "destaques_input")
    materiais = pegar_valor("materiais_block", "materiais_input")
    imagem_dados = pegar_valor("imagem_dados_block", "imagem_dados_input")
    link_report = pegar_valor("link_report_block", "link_report_input")
    reconhecimentos = pegar_valor("reconhecimentos_block", "reconhecimentos_input")
    gif_reconhecimento = pegar_valor("gif_reconhecimento_block", "gif_reconhecimento_input")
    eventos = pegar_valor("eventos_block", "eventos_input")
    dica = pegar_valor("dica_block", "dica_input")

    blocks = []

    if banner:
        blocks.append({
            "type": "image",
            "image_url": banner,
            "alt_text": "Banner Guru News"
        })

    if titulo or periodo:
        texto_titulo = ""
        if titulo:
            texto_titulo += f"*{titulo}*"
        if periodo:
            texto_titulo += f"\n📅 {periodo}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": texto_titulo
            }
        })
        blocks.append({"type": "divider"})

    if destaques:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📢 *Destaques da quinzena*\n\n{destaques}"
            }
        })
        blocks.append({"type": "divider"})

    if materiais:
        linhas = [linha.strip() for linha in materiais.split("\n") if linha.strip()]

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "📚 *Materiais*"
            }
        })

        for i, linha in enumerate(linhas[:5], start=1):
            if "|" in linha:
                nome, link = linha.split("|", 1)
                nome = nome.strip()
                link = link.strip()

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• {nome}"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📎 Consultar",
                            "emoji": True
                        },
                        "url": link
                    }
                })
            else:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• {linha}"
                    }
                })

        blocks.append({"type": "divider"})

    if imagem_dados:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "📊 *Dados da quinzena*"
            }
        })
        blocks.append({
            "type": "image",
            "image_url": imagem_dados,
            "alt_text": "Dados da quinzena"
        })

        if link_report:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📈 Ver report completo",
                            "emoji": True
                        },
                        "url": link_report
                    }
                ]
            })

        blocks.append({"type": "divider"})

    if reconhecimentos:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🏆 *Reconhecimentos*\n\n{reconhecimentos}"
            }
        })

        if gif_reconhecimento:
            blocks.append({
                "type": "image",
                "image_url": gif_reconhecimento,
                "alt_text": "Reconhecimento"
            })

        blocks.append({"type": "divider"})

    if eventos:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📅 *Próximos eventos*\n\n{eventos}"
            }
        })
        blocks.append({"type": "divider"})

    if dica:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"💡 *Dica da semana*\n\n{dica}"
            }
        })
        blocks.append({"type": "divider"})

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*O que achou desta edição?*"
        }
    })

    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "👍 Curti",
                    "emoji": True
                },
                "value": titulo or "Guru News",
                "action_id": "guru_news_curti"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "👎 Pode melhorar",
                    "emoji": True
                },
                "value": titulo or "Guru News",
                "action_id": "guru_news_nao_curti"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "💬 Enviar sugestão",
                    "emoji": True
                },
                "value": titulo or "Guru News",
                "action_id": "guru_news_sugestao"
            }
        ]
    })

    client.chat_postMessage(
        channel=usuario_id,
        text="Pré-visualização do Guru News",
        blocks=blocks
    )

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)