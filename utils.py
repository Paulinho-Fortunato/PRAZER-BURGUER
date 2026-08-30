"""
Funções utilitárias para validação, sanitização e integração
"""
import re
import bleach
import requests
import logging
from functools import wraps
from flask import session, flash, redirect, url_for, request
from werkzeug.security import generate_password_hash
from email_validator import validate_email, EmailNotValidError
import phonenumbers
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── VALIDAÇÃO ────────────────────────────────────────────────────
class Validador:
    """Classe para validações de dados"""
    
    @staticmethod
    def validar_email(email):
        """Validar e normalizar email"""
        try:
            valid = validate_email(email)
            return valid.email
        except EmailNotValidError as e:
            return None
    
    @staticmethod
    def validar_telefone(telefone, pais='AO'):
        """Validar e formatar telefone"""
        try:
            parsed = phonenumbers.parse(telefone, pais)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except:
            pass
        return None
    
    @staticmethod
    def validar_senha_forte(senha):
        """Validar força da senha"""
        if len(senha) < 12:
            return False, "Mínimo 12 caracteres"
        if not re.search(r'[A-Z]', senha):
            return False, "Requer letra maiúscula"
        if not re.search(r'[a-z]', senha):
            return False, "Requer letra minúscula"
        if not re.search(r'[0-9]', senha):
            return False, "Requer número"
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', senha):
            return False, "Requer caractere especial (!@#$%^&*)"
        return True, "Senha forte"
    
    @staticmethod
    def validar_nome(nome, max_length=100):
        """Validar nome de usuário"""
        if not nome or len(nome) < 2:
            return False
        if len(nome) > max_length:
            return False
        # Apenas letras, números, espaços e alguns caracteres
        if not re.match(r'^[\w\s\-\'.áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]+$', nome):
            return False
        return True
    
    @staticmethod
    def validar_morada(morada, max_length=200):
        """Validar endereço"""
        if not morada or len(morada) < 5:
            return False
        if len(morada) > max_length:
            return False
        return True
    
    @staticmethod
    def validar_preco(preco):
        """Validar preço (em centavos)"""
        try:
            preco_int = int(preco)
            if preco_int < 0 or preco_int > 10000000:  # Máx 100.000 Kz
                return False
            return True
        except (ValueError, TypeError):
            return False

# ─── SANITIZAÇÃO ──────────────────────────────────────────────────
class Sanitizador:
    """Classe para sanitização de dados"""
    
    @staticmethod
    def sanitizar_texto(texto, max_length=500):
        """Sanitizar texto do usuário contra XSS"""
        if not texto:
            return ""
        # Remove todas as tags HTML
        limpo = bleach.clean(texto, tags=[], strip=True)
        # Limita comprimento
        return limpo[:max_length].strip()
    
    @staticmethod
    def sanitizar_nome(nome, max_length=100):
        """Sanitizar nome"""
        if not nome:
            return ""
        # Mantém apenas caracteres alfanuméricos, espaço e alguns símbolos
        sanitizado = re.sub(r'[^a-zA-Z0-9\s\-\'.áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]', '', nome)
        return sanitizado[:max_length].strip()
    
    @staticmethod
    def sanitizar_morada(morada, max_length=200):
        """Sanitizar endereço"""
        if not morada:
            return ""
        sanitizado = re.sub(r'[^a-zA-Z0-9\s\-,./áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]', '', morada)
        return sanitizado[:max_length].strip()
    
    @staticmethod
    def sanitizar_telefone(telefone):
        """Sanitizar telefone"""
        if not telefone:
            return ""
        # Mantém apenas números e símbolos válidos
        sanitizado = re.sub(r'[^\d\+\-\s\(\)]', '', telefone)
        return sanitizado.strip()
    
    @staticmethod
    def sanitizar_comentario(comentario, max_length=500):
        """Sanitizar comentário mantendo quebras de linha"""
        if not comentario:
            return ""
        # Remove tags HTML mas permite quebras de linha
        limpo = bleach.clean(comentario, tags=[], strip=True)
        # Limita quebras de linha consecutivas
        limpo = re.sub(r'\n{3,}', '\n\n', limpo)
        return limpo[:max_length].strip()

# ─── DECORADORES ──────────────────────────────────────────────────
def login_required(f):
    """Decorador para requer login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Faça login para aceder à sua conta.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorador para requer admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Acesso restrito.', 'warning')
            return redirect(url_for('login'))
        
        from database import Database
        usuario = Database.buscar_usuario_email(session['user']['email'])
        if not usuario or not usuario.get('admin'):
            flash('Não tem permissão para esta página.', 'danger')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

# ─── FORMATAÇÃO ───────────────────────────────────────────────────
class Formatador:
    """Classe para formatação de dados"""
    
    @staticmethod
    def formatar_kz(valor_centavos):
        """Formata valor em centavos para kwanzas"""
        return f'Kz {valor_centavos / 100:.2f}'
    
    @staticmethod
    def formatar_data(data):
        """Formata data para português"""
        if isinstance(data, str):
            return data
        return data.strftime('%d/%m/%Y %H:%M')
    
    @staticmethod
    def formatar_data_curta(data):
        """Formata data curta"""
        if isinstance(data, str):
            return data
        return data.strftime('%d/%m/%Y')

# ─── WHATSAPP API ─────────────────────────────────────────────────
class WhatsAppAPI:
    """Integração com WhatsApp Business API"""
    
    def __init__(self, token, business_phone_id):
        self.token = token
        self.business_phone_id = business_phone_id
        self.api_url = f'https://graph.instagram.com/v18.0/{business_phone_id}/messages'
    
    def enviar_mensagem_pedido(self, numero_telefone, pedido_id, cliente, itens, total, link_pedido):
        """Enviar preview do pedido via WhatsApp"""
        try:
            # Formatar itens
            itens_texto = '\n'.join([
                f"• {item['nome']} x{item['quantidade']} - Kz {item['preco'] / 100 * item['quantidade']:.2f}"
                for item in itens
            ])
            
            mensagem = f"""
📦 *Seu Pedido foi Recebido!*

Olá {cliente}! 👋

*ID do Pedido:* #{pedido_id}
*Status:* Pendente de confirmação

*Itens do Pedido:*
{itens_texto}

*Total:* Kz {total / 100:.2f}

🔗 Ver detalhes: {link_pedido}

Obrigado por escolher PRAZER BURGUER! 🍔
Entraremos em contacto em breve.
            """.strip()
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': numero_telefone,
                'type': 'text',
                'text': {'body': mensagem}
            }
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"WhatsApp enviado para {numero_telefone} - Pedido #{pedido_id}")
                return True
            else:
                logger.error(f"Erro ao enviar WhatsApp: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Erro ao enviar WhatsApp: {str(e)}")
            return False
    
    def enviar_atualizacao_status(self, numero_telefone, pedido_id, novo_status, status_info):
        """Enviar atualização de status via WhatsApp"""
        try:
            status_label = status_info.get(novo_status, {}).get('label', novo_status)
            
            mensagem = f"""
📦 *Atualização do Seu Pedido*

Pedido #{pedido_id}

*Novo Status:* {status_label}

Visite: {request.host_url}rastreamento/{pedido_id}

PRAZER BURGUER 🍔
            """.strip()
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': numero_telefone,
                'type': 'text',
                'text': {'body': mensagem}
            }
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            return response.status_code == 200
        
        except Exception as e:
            logger.error(f"Erro ao enviar atualização: {str(e)}")
            return False

# ─── SEGURANÇA ────────────────────────────────────────────────────
class Seguranca:
    """Classe para funções de segurança"""
    
    @staticmethod
    def gerar_secret_key(tamanho=32):
        """Gerar chave secreta segura"""
        import secrets
        return secrets.token_hex(tamanho)
    
    @staticmethod
    def gerar_senha_admin():
        """Gerar senha aleatória segura para admin"""
        import secrets
        import string
        
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            senha = ''.join(secrets.choice(chars) for _ in range(16))
            # Verificar se atende requisitos
            if (re.search(r'[A-Z]', senha) and 
                re.search(r'[a-z]', senha) and 
                re.search(r'[0-9]', senha) and 
                re.search(r'[!@#$%^&*]', senha)):
                return senha
    
    @staticmethod
    def obter_ip_cliente():
        """Obter IP real do cliente"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0]
        return request.remote_addr
