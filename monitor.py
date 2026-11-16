import os
import re
import smtplib
from email.message import EmailMessage
import requests
from bs4 import BeautifulSoup

URL = "https://sarzedo.mg.gov.br/diarios-eletronicos/"
ARQUIVO_CONTROLE = "ultima_edicao.txt"


def verificar_diario():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like"
            " Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    resposta = requests.get(URL, headers=headers, timeout=30)
    resposta.raise_for_status()
    soup = BeautifulSoup(resposta.text, "html.parser")

    # Procura no texto da página pelo padrão "Edição XXXX"
    texto_pagina = soup.get_text(" ", strip=True)
    match = re.search(r"Edição\s*(\d+)", texto_pagina)

    if not match:
        print("Não foi possível localizar o número da edição na página.")
        return

    edicao_atual = match.group(1)

    # Lê a última edição registrada
    if os.path.exists(ARQUIVO_CONTROLE):
        with open(ARQUIVO_CONTROLE, "r", encoding="utf-8") as f:
            ultima_edicao = f.read().strip()
    else:
        ultima_edicao = ""

    print(f"Edição no site: {edicao_atual} | Última salva: {ultima_edicao}")

    if edicao_atual != ultima_edicao:
        # Busca o primeiro link que termine em .pdf na página
        link_pdf = None
        for a in soup.find_all("a", href=True):
            if ".pdf" in a["href"].lower():
                link_pdf = a["href"]
                break

        if not link_pdf:
            print("Nova edição detectada, mas o link do PDF não foi encontrado.")
            return

        # Garante que a URL do PDF seja completa
        if link_pdf.startswith("/"):
            link_pdf = f"https://sarzedo.mg.gov.br{link_pdf}"

        print(f"Baixando PDF: {link_pdf}")
        pdf_resposta = requests.get(link_pdf, headers=headers, timeout=60)
        pdf_resposta.raise_for_status()

        nome_arquivo = f"Diario_Oficial_Sarzedo_Edicao_{edicao_atual}.pdf"
        enviar_email(nome_arquivo, pdf_resposta.content, edicao_atual, link_pdf)

        with open(ARQUIVO_CONTROLE, "w", encoding="utf-8") as f:
            f.write(edicao_atual)
        print("Controle atualizado com sucesso.")
    else:
        print("Nenhuma novidade por enquanto.")


def enviar_email(nome_arquivo, arquivo_bytes, edicao, link_pdf):
    remetente = os.environ["EMAIL_REMETENTE"]
    senha = os.environ["EMAIL_SENHA"]
    destinatario = os.environ["EMAIL_DESTINO"]

    msg = EmailMessage()
    msg["Subject"] = f"📰 Novo Diário Oficial de Sarzedo - Edição {edicao}"
    msg["From"] = remetente
    msg["To"] = destinatario
    msg.set_content(
        f"Olá!\n\nUma nova publicação foi detectada no portal de Sarzedo.\n"
        f"Edição: {edicao}\n"
        f"Link direto: {link_pdf}\n\n"
        f"O arquivo PDF segue em anexo."
    )

    msg.add_attachment(
        arquivo_bytes,
        maintype="application",
        subtype="pdf",
        filename=nome_arquivo,
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(remetente, senha)
        smtp.send_message(msg)
    print(f"E-mail enviado para {destinatario}!")


if __name__ == "__main__":
    verificar_diario()
