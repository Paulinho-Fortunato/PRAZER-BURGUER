"""
PRAZER BURGUER - Aplicação Flask com MongoDB
Cardápio online com redirecionamento para WhatsApp
"""
import os
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv

# Importar bibliotecas Flask
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Importar configuração e banco de dados
from config import config
from database import Database, mongo
from utils import (
    Validador, Sanitizador, Formatador, Seguranca,
    login_required, admin_required
)

# Carregar variáveis de ambiente
load_dotenv()

# ─── INICIALIZAÇÃO ────────────────────────────────────────────────
app = Flask(__name__)

# Configuração baseada no ambiente
flask_env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[flask_env])

# Inicializar banco de dados
Database.init_db(app)
mongo.init_app(app)

# Inicializar proteções de segurança
csrf = CSRFProtect(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[app.config['RATELIMIT_DEFAULT']],
    storage_uri="memory://",
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('prazer_burguer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── CONTEXT PROCESSOR ───────────────────────────────────────────
@app.context_processor
def globals_template():
    """Variáveis globais disponíveis em todos templates"""
    carrinho_raw = session.get('carrinho', [])
    user = session.get('user')
    return {
        'carrinho_total': len(carrinho_raw),
        'format_kz': Formatador.formatar_kz,
        'user_logado': user,
    }

# ─── HELPERS ──────────────────────────────────────────────────────
def calcular_carrinho():
    """Calcular itens e subtotal do carrinho"""
    carrinho_raw = session.get('carrinho', [])
    agrupado = {}
    
    for item in carrinho_raw:
        chave = item['produto_id']
        if chave in agrupado:
            agrupado[chave]['quantidade'] += 1
        else:
            agrupado[chave] = item.copy()
            agrupado[chave]['quantidade'] = 1
    
    itens = list(agrupado.values())
    subtotal = sum(i['preco'] * i['quantidade'] for i in itens)
    return itens, subtotal

def calcular_desconto(subtotal):
    """Calcular desconto de cupão ativo"""
    cupao_codigo = session.get('cupao')
    desconto = 0
    
    if cupao_codigo:
        cupao = Database.buscar_cupao(cupao_codigo)
        if cupao:
            if cupao['tipo'] == 'percentagem':
                desconto = int(subtotal * cupao['desconto'] / 100)
            else:
                desconto = min(cupao['desconto'], subtotal)
    
    return desconto

def gerar_link_whatsapp(pedido_id, cliente, itens, total, telefone_destino):
    """Gerar link WhatsApp com preview do pedido"""
    itens_texto = '\n'.join([
        f"• {item['nome']} x{item['quantidade']} - Kz {item['preco'] / 100 * item['quantidade']:.2f}"
        for item in itens
    ])
    
    mensagem = f"""
📦 *Novo Pedido - PRAZER BURGUER* 🍔

*ID do Pedido:* #{pedido_id}
*Cliente:* {cliente}

*Itens:*
{itens_texto}

*Total:* Kz {total / 100:.2f}

🔗 Detalhes: {request.host_url}rastreamento/{pedido_id}

Obrigado! ✨
    """.strip()
    
    # URL encode e gerar link WhatsApp
    import urllib.parse
    mensagem_encoded = urllib.parse.quote(mensagem)
    
    # Formatar telefone para WhatsApp (adicionar +244 se necessário)
    telefone_limpo = telefone_destino.replace(' ', '').replace('-', '').replace('+', '')
    if not telefone_limpo.startswith('244'):
        telefone_limpo = '244' + telefone_limpo[-9:]
    
    whatsapp_url = f"https://wa.me/{telefone_limpo}?text={mensagem_encoded}"
    return whatsapp_url

# ─── ROTAS - HOME ────────────────────────────────────────────────
@app.route('/')
def index():
    """Página inicial"""
    try:
        produtos_destaque = Database.produtosPopulares(limite=6)
        stats = Database.obter_estatisticas()
        
        return render_template('index.html',
            produtos_destaque=produtos_destaque,
            stats=stats,
            info={
                'titulo': 'PRAZER BURGUER',
                'descricao': 'Hambúrgueres artesanais, batatas crocantes e um atendimento rápido em Angola.',
                'horario': 'Segunda a Domingo, das 11h30 às 23h30',
                'local': 'Rua da Liberdade, Luanda, Angola',
            }
        )
    except Exception as e:
        logger.error(f"Erro na página inicial: {str(e)}")
        flash('Erro ao carregar página.', 'danger')
        return render_template('index.html', info={})

# ─── ROTAS - CARDÁPIO ────────────────────────────────────────────
@app.route('/cardapio')
def cardapio():
    """Exibir cardápio com filtro por categoria"""
    try:
        categoria = request.args.get('categoria', 'todos')
        produtos = Database.buscar_todos_produtos(categoria)
        
        categorias = {
            'todos': {'label': 'Todos', 'icone': 'bi-grid-3x3-gap-fill'},
            'burgers': {'label': 'Burgers', 'icone': 'bi-egg-fried'},
            'pizzas': {'label': 'Pizzas', 'icone': 'bi-circle'},
            'extras': {'label': 'Extras', 'icone': 'bi-cup-straw'},
            'bebidas': {'label': 'Bebidas', 'icone': 'bi-cup'},
            'sobremesas': {'label': 'Sobremesas', 'icone': 'bi-snow'},
        }
        
        return render_template('cardapio.html',
            produtos=produtos,
            categorias=categorias,
            categoria_ativa=categoria
        )
    except Exception as e:
        logger.error(f"Erro ao exibir cardápio: {str(e)}")
        flash('Erro ao carregar cardápio.', 'danger')
        return redirect(url_for('index'))

# ─── ROTAS - AVALIAÇÕES ──────────────────────────────────────────
@app.route('/avaliar/<produto_id>', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def avaliar(produto_id):
    """Avaliar um produto"""
    try:
        estrelas = int(request.form.get('estrelas', 0))
        comentario_raw = request.form.get('comentario', '').strip()
        
        # Validar entrada
        if not 1 <= estrelas <= 5:
            flash('Avaliação inválida (1-5 estrelas).', 'danger')
            return redirect(url_for('cardapio'))
        
        # Validar produto
        produto = Database.buscar_produto_id(produto_id)
        if not produto:
            flash('Produto não encontrado.', 'danger')
            return redirect(url_for('cardapio'))
        
        # Sanitizar comentário
        comentario = Sanitizador.sanitizar_comentario(comentario_raw)
        
        # Adicionar avaliação
        Database.adicionar_avaliacao(
            produto_id,
            session['user']['email'],
            estrelas,
            comentario
        )
        
        # Registrar auditoria
        Database.registrar_auditoria(
            'avaliacao',
            session['user']['email'],
            f'Avaliou produto {produto["nome"]}',
            {'produto_id': produto_id, 'estrelas': estrelas},
            Seguranca.obter_ip_cliente()
        )
        
        flash('Avaliação enviada com sucesso!', 'success')
        return redirect(url_for('cardapio'))
    
    except ValueError:
        flash('Dados inválidos.', 'danger')
        return redirect(url_for('cardapio'))
    except Exception as e:
        logger.error(f"Erro ao avaliar: {str(e)}")
        flash('Erro ao enviar avaliação.', 'danger')
        return redirect(url_for('cardapio'))

# ─── ROTAS - CARRINHO ────────────────────────────────────────────
@app.route('/carrinho')
def carrinho():
    """Exibir carrinho"""
    try:
        itens, subtotal = calcular_carrinho()
        desconto = calcular_desconto(subtotal)
        total = subtotal - desconto
        
        return render_template('carrinho.html',
            itens=itens,
            subtotal=subtotal,
            desconto=desconto,
            total=total,
            cupao=session.get('cupao')
        )
    except Exception as e:
        logger.error(f"Erro ao exibir carrinho: {str(e)}")
        flash('Erro ao carregar carrinho.', 'danger')
        return redirect(url_for('cardapio'))

@app.route('/adicionar_carrinho', methods=['POST'])
def adicionar_carrinho():
    """Adicionar item ao carrinho"""
    try:
        produto_id = request.form.get('produto_id')
        
        # Validar produto
        produto = Database.buscar_produto_id(produto_id)
        if not produto:
            flash('Produto não encontrado.', 'danger')
            return redirect(url_for('cardapio'))
        
        # Adicionar ao carrinho
        carrinho = session.get('carrinho', [])
        carrinho.append({
            'produto_id': produto_id,
            'nome': produto['nome'],
            'preco': produto['preco'],
            'imagem': produto['imagem']
        })
        session['carrinho'] = carrinho
        
        flash(f'{produto["nome"]} adicionado ao carrinho!', 'success')
        return redirect(url_for('cardapio'))
    
    except Exception as e:
        logger.error(f"Erro ao adicionar ao carrinho: {str(e)}")
        flash('Erro ao adicionar ao carrinho.', 'danger')
        return redirect(url_for('cardapio'))

@app.route('/atualizar_quantidade', methods=['POST'])
def atualizar_quantidade():
    """Aumentar/diminuir quantidade no carrinho"""
    try:
        produto_id = request.form.get('produto_id')
        acao = request.form.get('acao')
        carrinho = session.get('carrinho', [])
        
        if acao == 'aumentar':
            ref = next((i for i in carrinho if i['produto_id'] == produto_id), None)
            if ref:
                carrinho.append({**ref})
        
        elif acao == 'diminuir':
            for i, item in enumerate(carrinho):
                if item['produto_id'] == produto_id:
                    carrinho.pop(i)
                    break
        
        session['carrinho'] = carrinho
        return redirect(url_for('carrinho'))
    
    except Exception as e:
        logger.error(f"Erro ao atualizar quantidade: {str(e)}")
        return redirect(url_for('carrinho'))

@app.route('/remover_carrinho/<produto_id>', methods=['POST'])
def remover_carrinho(produto_id):
    """Remover produto do carrinho"""
    try:
        carrinho = session.get('carrinho', [])
        carrinho = [i for i in carrinho if i['produto_id'] != produto_id]
        session['carrinho'] = carrinho
        flash('Produto removido do carrinho.', 'info')
        return redirect(url_for('carrinho'))
    except Exception as e:
        logger.error(f"Erro ao remover do carrinho: {str(e)}")
        return redirect(url_for('carrinho'))

@app.route('/limpar_carrinho', methods=['POST'])
def limpar_carrinho():
    """Limpar todo o carrinho"""
    try:
        session['carrinho'] = []
        session.pop('cupao', None)
        flash('Carrinho esvaziado.', 'info')
        return redirect(url_for('carrinho'))
    except Exception as e:
        logger.error(f"Erro ao limpar carrinho: {str(e)}")
        return redirect(url_for('carrinho'))

# ─── ROTAS - CUPÕES ──────────────────────────────────────────────
@app.route('/aplicar_cupao', methods=['POST'])
@limiter.limit("5 per minute")
def aplicar_cupao():
    """Aplicar cupão de desconto"""
    try:
        codigo = request.form.get('cupao', '').strip().upper()
        
        # Validar entrada
        if not codigo or len(codigo) > 20:
            flash('Cupão inválido.', 'danger')
            return redirect(url_for('carrinho'))
        
        # Buscar cupão
        cupao = Database.buscar_cupao(codigo)
        if cupao:
            # Validar expiração
            if cupao.get('data_expiracao') and cupao['data_expiracao'] < datetime.utcnow():
                flash('Cupão expirado.', 'danger')
            else:
                session['cupao'] = codigo
                Database.incrementar_uso_cupao(codigo)
                flash(f'Cupão "{codigo}" aplicado com sucesso!', 'success')
        else:
            flash('Cupão inválido ou expirado.', 'danger')
        
        return redirect(url_for('carrinho'))
    
    except Exception as e:
        logger.error(f"Erro ao aplicar cupão: {str(e)}")
        flash('Erro ao aplicar cupão.', 'danger')
        return redirect(url_for('carrinho'))

@app.route('/remover_cupao', methods=['POST'])
def remover_cupao():
    """Remover cupão ativo"""
    try:
        session.pop('cupao', None)
        flash('Cupão removido.', 'info')
        return redirect(url_for('carrinho'))
    except Exception as e:
        logger.error(f"Erro ao remover cupão: {str(e)}")
        return redirect(url_for('carrinho'))

# ─── ROTAS - CHECKOUT ────────────────────────────────────────────
@app.route('/checkout', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def checkout():
    """Processar checkout"""
    try:
        itens, subtotal = calcular_carrinho()
        
        if not itens:
            flash('Seu carrinho está vazio.', 'warning')
            return redirect(url_for('carrinho'))
        
        desconto = calcular_desconto(subtotal)
        total = subtotal - desconto
        
        if request.method == 'POST':
            # Validar inputs
            nome = request.form.get('nome', '').strip()
            telefone = request.form.get('telefone', '').strip()
            morada = request.form.get('morada', '').strip()
            metodo_pagamento = request.form.get('pagamento', '').strip()
            
            # Validar campos obrigatórios
            if not all([nome, telefone, morada, metodo_pagamento]):
                flash('Preencha todos os campos.', 'danger')
                return render_template('checkout.html',
                    itens=itens,
                    subtotal=subtotal,
                    desconto=desconto,
                    total=total,
                    user=session.get('user')
                )
            
            # Validar e sanitizar dados
            if not Validador.validar_nome(nome):
                flash('Nome inválido.', 'danger')
                return render_template('checkout.html',
                    itens=itens,
                    subtotal=subtotal,
                    desconto=desconto,
                    total=total,
                    user=session.get('user')
                )
            
            telefone_valido = Validador.validar_telefone(telefone)
            if not telefone_valido:
                flash('Telefone inválido. Use o formato: +244 924 123 456', 'danger')
                return render_template('checkout.html',
                    itens=itens,
                    subtotal=subtotal,
                    desconto=desconto,
                    total=total,
                    user=session.get('user')
                )
            
            if not Validador.validar_morada(morada):
                flash('Endereço inválido (mínimo 5 caracteres).', 'danger')
                return render_template('checkout.html',
                    itens=itens,
                    subtotal=subtotal,
                    desconto=desconto,
                    total=total,
                    user=session.get('user')
                )
            
            # Sanitizar dados
            nome_sanitizado = Sanitizador.sanitizar_nome(nome)
            morada_sanitizada = Sanitizador.sanitizar_morada(morada)
            telefone_sanitizado = Sanitizador.sanitizar_telefone(telefone_valido)
            
            # Gerar ID do pedido
            pedido_id = str(uuid.uuid4())[:8].upper()
            
            # Criar pedido no banco de dados
            user_email = session.get('user', {}).get('email', 'anonimo')
            Database.criar_pedido(
                user_email=user_email,
                cliente=nome_sanitizado,
                telefone=telefone_sanitizado,
                morada=morada_sanitizada,
                itens=itens,
                subtotal=subtotal,
                desconto=desconto,
                total=total,
                metodo_pagamento=metodo_pagamento,
                pedido_id=pedido_id
            )
            
            # Decrementar estoque
            for item in itens:
                Database.decrementar_estoque(item['produto_id'], item['quantidade'])
                Database.incrementar_vendas(item['produto_id'], item['quantidade'])
            
            # Registrar auditoria
            Database.registrar_auditoria(
                'pedido',
                user_email,
                f'Criou pedido #{pedido_id}',
                {'pedido_id': pedido_id, 'total': total},
                Seguranca.obter_ip_cliente()
            )
            
            # Limpar carrinho
            session['carrinho'] = []
            session.pop('cupao', None)
            
            # Gerar link WhatsApp
            whatsapp_link = gerar_link_whatsapp(
                pedido_id,
                nome_sanitizado,
                itens,
                total,
                telefone_sanitizado
            )
            
            flash(f'Pedido #{pedido_id} criado com sucesso!', 'success')
            return redirect(whatsapp_link)
        
        return render_template('checkout.html',
            itens=itens,
            subtotal=subtotal,
            desconto=desconto,
            total=total,
            user=session.get('user')
        )
    
    except Exception as e:
        logger.error(f"Erro no checkout: {str(e)}")
        flash('Erro ao processar pedido.', 'danger')
        return redirect(url_for('carrinho'))

# ─── ROTAS - RASTREAMENTO ────────────────────────────────────────
@app.route('/rastreamento/<pedido_id>')
def rastreamento(pedido_id):
    """Rastrear pedido"""
    try:
        pedido = Database.buscar_pedido_id_string(pedido_id)
        if not pedido:
            flash('Pedido não encontrado.', 'danger')
            return redirect(url_for('index'))
        
        status_info = {
            'pendente': {'label': 'Pendente', 'icone': 'bi-clock', 'cor': '#ff9800'},
            'confirmado': {'label': 'Confirmado', 'icone': 'bi-check-circle', 'cor': '#2196f3'},
            'preparando': {'label': 'A preparar', 'icone': 'bi-fire', 'cor': '#ff6b35'},
            'entregando': {'label': 'A caminho', 'icone': 'bi-bicycle', 'cor': '#9c27b0'},
            'entregue': {'label': 'Entregue', 'icone': 'bi-check-circle-fill', 'cor': '#27ae60'},
            'cancelado': {'label': 'Cancelado', 'icone': 'bi-x-circle', 'cor': '#e74c3c'},
        }
        
        return render_template('rastreamento.html',
            pedido=pedido,
            status_info=status_info
        )
    
    except Exception as e:
        logger.error(f"Erro ao rastrear pedido: {str(e)}")
        flash('Erro ao carregar pedido.', 'danger')
        return redirect(url_for('index'))

@app.route('/meus_pedidos')
@login_required
def meus_pedidos():
    """Exibir pedidos do usuário"""
    try:
        email = session['user']['email']
        pedidos = Database.buscar_pedidos_usuario(email)
        
        status_info = {
            'pendente': {'label': 'Pendente', 'icone': 'bi-clock'},
            'confirmado': {'label': 'Confirmado', 'icone': 'bi-check-circle'},
            'preparando': {'label': 'A preparar', 'icone': 'bi-fire'},
            'entregando': {'label': 'A caminho', 'icone': 'bi-bicycle'},
            'entregue': {'label': 'Entregue', 'icone': 'bi-check-circle-fill'},
            'cancelado': {'label': 'Cancelado', 'icone': 'bi-x-circle'},
        }
        
        return render_template('meus_pedidos.html',
            pedidos=pedidos,
            status_info=status_info
        )
    
    except Exception as e:
        logger.error(f"Erro ao exibir pedidos do usuário: {str(e)}")
        flash('Erro ao carregar pedidos.', 'danger')
        return redirect(url_for('index'))

# ─── ROTAS - AUTENTICAÇÃO ────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Fazer login"""
    try:
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            senha = request.form.get('senha', '')
            
            # Validar entrada
            if not email or not senha:
                flash('Preencha todos os campos.', 'danger')
                return render_template('login.html')
            
            # Buscar usuário
            usuario = Database.buscar_usuario_email(email)
            
            # Verificar bloqueio
            if usuario and usuario.get('bloqueado_ate'):
                if usuario['bloqueado_ate'] > datetime.utcnow():
                    flash('Conta bloqueada. Tente novamente mais tarde.', 'warning')
                    return render_template('login.html')
                else:
                    Database.desbloquear_usuario(email)
            
            # Validar credenciais
            if usuario and check_password_hash(usuario['senha_hash'], senha):
                session.clear()
                session['user'] = {
                    'email': email,
                    'nome': usuario['nome'],
                    'admin': usuario.get('admin', False)
                }
                session.regenerate = True
                
                # Registrar auditoria
                Database.registrar_auditoria(
                    'login',
                    email,
                    'Fez login com sucesso',
                    {},
                    Seguranca.obter_ip_cliente()
                )
                
                flash('Bem-vindo de volta à PRAZER BURGUER!', 'success')
                return redirect(url_for('conta'))
            
            # Login falhou
            Database.registrar_tentativa_login_falha(email)
            
            # Registrar auditoria de falha
            Database.registrar_auditoria(
                'login',
                email,
                'Tentativa de login falhou',
                {},
                Seguranca.obter_ip_cliente()
            )
            
            # Verificar se deve bloquear
            if usuario:
                tentativas = usuario.get('tentativas_login', 0) + 1
                if tentativas >= app.config['MAX_LOGIN_ATTEMPTS']:
                    Database.bloquear_usuario(email, app.config['LOCKOUT_DURATION'])
                    flash('Muitas tentativas falhadas. Conta bloqueada por 15 minutos.', 'danger')
                else:
                    flash('E-mail ou palavra-passe inválidos.', 'danger')
            else:
                flash('E-mail ou palavra-passe inválidos.', 'danger')
        
        return render_template('login.html')
    
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        flash('Erro ao fazer login.', 'danger')
        return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def signup():
    """Criar nova conta"""
    try:
        if request.method == 'POST':
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip().lower()
            senha = request.form.get('senha', '')
            confirmar = request.form.get('confirmar_senha', '')
            
            # Validar entrada
            if not all([nome, email, senha, confirmar]):
                flash('Preencha todos os campos.', 'danger')
                return render_template('signup.html')
            
            # Validar nome
            if not Validador.validar_nome(nome):
                flash('Nome inválido (mínimo 2 caracteres).', 'danger')
                return render_template('signup.html')
            
            # Validar email
            email_valido = Validador.validar_email(email)
            if not email_valido:
                flash('E-mail inválido.', 'danger')
                return render_template('signup.html')
            
            # Verificar se email já existe
            if Database.buscar_usuario_email(email_valido):
                flash('Este e-mail já está registado.', 'danger')
                return render_template('signup.html')
            
            # Validar senha
            if senha != confirmar:
                flash('As palavras-passe não coincidem.', 'danger')
                return render_template('signup.html')
            
            senha_forte, msg = Validador.validar_senha_forte(senha)
            if not senha_forte:
                flash(f'Senha fraca: {msg}', 'danger')
                return render_template('signup.html')
            
            # Criar usuário
            senha_hash = generate_password_hash(senha)
            nome_sanitizado = Sanitizador.sanitizar_nome(nome)
            
            Database.criar_usuario(
                email=email_valido,
                nome=nome_sanitizado,
                senha_hash=senha_hash,
                admin=False
            )
            
            # Registrar auditoria
            Database.registrar_auditoria(
                'signup',
                email_valido,
                'Criou nova conta',
                {},
                Seguranca.obter_ip_cliente()
            )
            
            # Fazer login automático
            session.clear()
            session['user'] = {
                'email': email_valido,
                'nome': nome_sanitizado,
                'admin': False
            }
            
            flash('Conta criada com sucesso! Já pode fazer pedidos.', 'success')
            return redirect(url_for('conta'))
        
        return render_template('signup.html')
    
    except Exception as e:
        logger.error(f"Erro no signup: {str(e)}")
        flash('Erro ao criar conta.', 'danger')
        return render_template('signup.html')

@app.route('/logout')
def logout():
    """Fazer logout"""
    try:
        email = session.get('user', {}).get('email', 'anonimo')
        
        Database.registrar_auditoria(
            'logout',
            email,
            'Fez logout',
            {},
            Seguranca.obter_ip_cliente()
        )
        
        session.clear()
        flash('Saiu da sua conta com sucesso.', 'info')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Erro ao fazer logout: {str(e)}")
        return redirect(url_for('index'))

# ─── ROTAS - CONTA ───────────────────────────────────────────────
@app.route('/conta')
@login_required
def conta():
    """Página da conta do usuário"""
    try:
        email = session['user']['email']
        usuario = Database.buscar_usuario_email(email)
        pedidos = Database.buscar_pedidos_usuario(email)
        
        return render_template('conta.html',
            user=session['user'],
            usuario=usuario,
            pedidos=pedidos
        )
    except Exception as e:
        logger.error(f"Erro ao exibir conta: {str(e)}")
        flash('Erro ao carregar sua conta.', 'danger')
        return redirect(url_for('index'))

# ─── ROTAS - ADMIN ───────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin():
    """Dashboard admin"""
    try:
        stats = Database.obter_estatisticas()
        pedidos_recentes = Database.buscar_todos_pedidos(limite=10)
        
        return render_template('admin/dashboard.html',
            stats=stats,
            pedidos_recentes=pedidos_recentes
        )
    except Exception as e:
        logger.error(f"Erro no admin dashboard: {str(e)}")
        flash('Erro ao carregar dashboard.', 'danger')
        return redirect(url_for('index'))

@app.route('/admin/pedidos')
@admin_required
def admin_pedidos():
    """Gerenciar pedidos (admin)"""
    try:
        pagina = request.args.get('pagina', 1, type=int)
        status_filtro = request.args.get('status', '')
        
        filtro = {}
        if status_filtro:
            filtro['status'] = status_filtro
        
        pedidos = Database.buscar_todos_pedidos(filtro=filtro, limite=20, pagina=pagina)
        
        status_info = {
            'pendente': {'label': 'Pendente', 'icone': 'bi-clock'},
            'confirmado': {'label': 'Confirmado', 'icone': 'bi-check-circle'},
            'preparando': {'label': 'A preparar', 'icone': 'bi-fire'},
            'entregando': {'label': 'A caminho', 'icone': 'bi-bicycle'},
            'entregue': {'label': 'Entregue', 'icone': 'bi-check-circle-fill'},
            'cancelado': {'label': 'Cancelado', 'icone': 'bi-x-circle'},
        }
        
        return render_template('admin/pedidos.html',
            pedidos=pedidos,
            status_info=status_info,
            pagina=pagina,
            status_filtro=status_filtro
        )
    except Exception as e:
        logger.error(f"Erro ao listar pedidos (admin): {str(e)}")
        flash('Erro ao carregar pedidos.', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/pedido/<pedido_id>/status', methods=['POST'])
@admin_required
@limiter.limit("20 per minute")
def admin_atualizar_status(pedido_id):
    """Atualizar status do pedido (admin)"""
    try:
        novo_status = request.form.get('status', '').strip()
        observacao = request.form.get('observacao', '').strip()
        
        status_validos = ['pendente', 'confirmado', 'preparando', 'entregando', 'entregue', 'cancelado']
        if novo_status not in status_validos:
            flash('Status inválido.', 'danger')
            return redirect(url_for('admin_pedidos'))
        
        # Atualizar status
        Database.atualizar_status_pedido(pedido_id, novo_status, observacao)
        
        # Registrar auditoria
        admin_email = session['user']['email']
        Database.registrar_auditoria(
            'admin_action',
            admin_email,
            f'Atualizou status do pedido #{pedido_id} para {novo_status}',
            {'pedido_id': pedido_id, 'novo_status': novo_status},
            Seguranca.obter_ip_cliente()
        )
        
        flash(f'Pedido atualizado para "{novo_status}".', 'success')
        return redirect(url_for('admin_pedidos'))
    
    except Exception as e:
        logger.error(f"Erro ao atualizar status do pedido: {str(e)}")
        flash('Erro ao atualizar status.', 'danger')
        return redirect(url_for('admin_pedidos'))

@app.route('/admin/produtos')
@admin_required
def admin_produtos():
    """Gerenciar produtos (admin)"""
    try:
        produtos = Database.buscar_todos_produtos()
        return render_template('admin/produtos.html', produtos=produtos)
    except Exception as e:
        logger.error(f"Erro ao listar produtos (admin): {str(e)}")
        flash('Erro ao carregar produtos.', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/cupoes')
@admin_required
def admin_cupoes():
    """Gerenciar cupões (admin)"""
    try:
        cupoes = Database.buscar_todos_cupoes()
        return render_template('admin/cupoes.html', cupoes=cupoes)
    except Exception as e:
        logger.error(f"Erro ao listar cupões (admin): {str(e)}")
        flash('Erro ao carregar cupões.', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/auditoria')
@admin_required
def admin_auditoria():
    """Ver logs de auditoria (admin)"""
    try:
        pagina = request.args.get('pagina', 1, type=int)
        limite = 50
        skip = (pagina - 1) * limite
        
        eventos = Database.buscar_auditoria(limite=limite)
        return render_template('admin/auditoria.html',
            eventos=eventos,
            pagina=pagina
        )
    except Exception as e:
        logger.error(f"Erro ao exibir auditoria: {str(e)}")
        flash('Erro ao carregar auditoria.', 'danger')
        return redirect(url_for('admin'))

# ─── ERROR HANDLERS ───────────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    """Página não encontrada"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    """Erro interno do servidor"""
    logger.error(f"Erro 500: {str(error)}")
    return render_template('500.html'), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """Rate limit excedido"""
    flash('Muitas requisições. Tente novamente mais tarde.', 'danger')
    return redirect(url_for('index')), 429

# ─── INICIALIZAÇÃO ───────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        # Criar índices no MongoDB
        try:
            mongo.db.usuarios.create_index('email', unique=True)
            mongo.db.cupoes.create_index('codigo', unique=True)
            logger.info("Índices do MongoDB criados com sucesso")
        except Exception as e:
            logger.warning(f"Índices já existem: {str(e)}")
    
    # Obter configuração
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    # Rodaro app
    app.run(debug=debug_mode, host=host, port=port)
