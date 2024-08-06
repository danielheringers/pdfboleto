import re
from reportlab.lib.units import mm
from banks import bank_names
from reportlab.pdfbase import pdfmetrics
from io import BytesIO
import qrcode
from reportlab.lib.utils import ImageReader
from PIL import Image
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('Arial', 'ARIAL.TTF'))
pdfmetrics.registerFont(TTFont('Arial-Bold', 'ARIALBD.TTF'))
pdfmetrics.registerFont(TTFont('Arial-Italic', 'ARIALI.TTF'))
pdfmetrics.registerFont(TTFont('Arial-BoldItalic', 'ARIALBI.TTF'))

def formatar_cnpj_cpf(numero):
    numero_str = re.sub(r'\D', '', str(numero))
    if len(numero_str) == 14:
        return f'{numero_str[:2]}.{numero_str[2:5]}.{numero_str[5:8]}/{numero_str[8:12]}-{numero_str[12:]}'
    elif len(numero_str) == 11:
        return f'{numero_str[:3]}.{numero_str[3:6]}.{numero_str[6:9]}-{numero_str[9:]}'
    else:
        return numero
    
def escrever_mensagens(canvas_draw, start_y, decrement_mm, messages, margin):
    startYPosition = start_y * mm
    decrement = decrement_mm * mm 
    canvas_draw.setFont("Arial", 7)

    for i, message in enumerate(messages):
        if i >= 14:
            break
        y_pos = startYPosition - i * decrement
        canvas_draw.drawString(margin + 2 * mm, y_pos, message)

def escrever_texto(canvas, texts, margin, width):

    for text, x, y, font_size, bold, string_width in texts:
        font_name = "Arial-Bold" if bold else "Arial"
        canvas.setFont(font_name, font_size)
        if isinstance(x, str):
            if 'right' in x:
                offset = float(x.split('-')[1].strip()) * mm
                x_pos = width - margin - offset
            else:
                offset = float(x.split('+')[1].strip()) * mm
                x_pos = margin + offset
        else:
            x_pos = x * mm
        if string_width:
            y_pos = y * mm
            canvas.drawRightString(x_pos, y_pos, str(text))
        else:
            y_pos = y * mm
            canvas.drawString(x_pos, y_pos, str(text))

# Função para quebrar texto em múltiplas linhas
def quebrar_linhas(text, max_width, canvas_draw, font_name, font_size):
    lines = []
    current_line = ""
    
    for char in text:
        test_line = current_line + char
        if canvas_draw.stringWidth(test_line, font_name, font_size) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    lines.append(current_line)
    return lines

# Função principal para desenhar instruções de pagamento
def instrucoes_de_pagamento(canvas_draw, start_y, decrement_mm, data, margin):
    instructions = []

    # Converter bank_code em Nome do Banco
    bank_code = data["bank_account"]["bank"]
    bank_name = bank_names.get(bank_code, "Banco desconhecido")

    amount_details = data.get("billing", {}).get("amount_details", {})
    discount = amount_details.get("discount", {})
    fine = amount_details.get("fine", {})
    interest = amount_details.get("interest", {})
    rebate = amount_details.get("rebate", {})

    if not discount and not fine and not interest and not rebate:
        # Instruções padrão quando não há descontos, multas, juros ou abatimentos configurados
        instructions = [
            "Instruções de Pagamento:",
            f"1. Pagamento deve ser realizado até a data de vencimento preferencialmente no {bank_name}.", 
            "2. Em caso de dúvidas, entre em contato com o beneficiário pelo telefone (31) 9-9153-1299."
        ]
    else:
        instructions.append("Instruções de Pagamento:")
        instructions.append(f"1. Pagamento deve ser realizado até a data de vencimento preferencialmente no {bank_name}.")

        if "value" in interest and interest["value"] > 0:
            modality = interest["modality"]
            if modality == 1:
                instructions.append(f"2. Juros de R$ {interest['value']} por dia corrido após o vencimento.")
            elif modality == 2:
                instructions.append(f"2. Juros de {interest['value']}% ao dia corrido após o vencimento.")
            elif modality == 3:
                instructions.append(f"2. Juros de {interest['value']}% ao mês corrido após o vencimento.")
            elif modality == 4:
                instructions.append(f"2. Juros de {interest['value']}% ao ano corrido após o vencimento.")
            elif modality == 5:
                instructions.append(f"2. Juros de R$ {interest['value']} por dia útil após o vencimento.")
            elif modality == 6:
                instructions.append(f"2. Juros de {interest['value']}% ao dia útil após o vencimento.")
            elif modality == 7:
                instructions.append(f"2. Juros de {interest['value']}% ao mês útil após o vencimento.")
            elif modality == 8:
                instructions.append(f"2. Juros de {interest['value']}% ao ano útil após o vencimento.")
        else:
            instructions.append("2. Não há aplicação de juros em caso de atraso no pagamento.")

        if "value" in discount and discount["value"] > 0:
            modality = discount["modality"]
            if modality == 3:
                instructions.append(f"3. Desconto de R$ {discount['value']} por dia corrido para pagamento antecipado.")
            elif modality == 4:
                instructions.append(f"3. Desconto de R$ {discount['value']} por dia útil para pagamento antecipado.")
            elif modality == 5:
                instructions.append(f"3. Desconto de {discount['value']}% por dia corrido para pagamento antecipado.")
            elif modality == 6:
                instructions.append(f"3. Desconto de {discount['value']}% por dia útil para pagamento antecipado.")
        else:
            instructions.append("3. Não há concessão de descontos para pagamento antecipado.")

        if "value" in fine and fine["value"] > 0:
            modality = fine["modality"]
            if modality == 1:
                instructions.append(f"4. Multa de R$ {fine['value']} em caso de atraso no pagamento.")
            elif modality == 2:
                instructions.append(f"4. Multa de {fine['value']}% em caso de atraso no pagamento.")
        else:
            instructions.append("4. Não há aplicação de multas em caso de atraso no pagamento.")

        if "value" in rebate and rebate["value"] > 0:
            modality = rebate["modality"]
            if modality == 1:
                instructions.append(f"5. Abatimento de R$ {rebate['value']} no valor do boleto.")
            elif modality == 2:
                instructions.append(f"5. Abatimento de {rebate['value']}% no valor do boleto.")
        else:
            instructions.append("5. Não há abatimentos no valor do boleto.")

        instructions.append("6. Em caso de dúvidas, entre em contato com o beneficiário pelo telefone (31) 9-9153-1299.")

    startYPosition = start_y * mm
    decrement = decrement_mm * mm
    max_text_width = 117 * mm
    font_name = "Arial"
    font_size = 7

    canvas_draw.setFont(font_name, font_size)

    line_count = 0
    for instruction in instructions:
        if line_count >= 14:
            break

        wrapped_lines = quebrar_linhas(instruction, max_text_width, canvas_draw, font_name, font_size)

        for line in wrapped_lines:
            if line_count >= 14:
                break
            y_pos = startYPosition - line_count * decrement
            canvas_draw.drawString(margin + 2 * mm, y_pos, line)
            line_count += 1


# Logo No QR CODE NÃO UTILIZAR AINDA VAMOS DEFINIR NO FUTURO
def create_qr_with_logo(qr_data, logo_path):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Salvar logo na variavel
    logo = Image.open(logo_path)

    # Calcular Tamanho da logo
    qr_width, qr_height = qr_img.size
    logo_size = int(qr_width / 4)
    logo = logo.resize((logo_size, logo_size))
    logo_pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)

    # Colar Logo No Qr Code
    qr_img.paste(logo, logo_pos, mask=logo)

    # Salvar QR Code no buffer
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)        