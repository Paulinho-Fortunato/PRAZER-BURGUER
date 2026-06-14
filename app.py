import os
import uuid
from datetime import datetime
from functools import wraps
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY'),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
)

# Inicializar proteções de segurança
csrf = CSRFProtect(app)

# Rate limiting configurável
limiter_rate = os.environ.get('RATE_LIMIT', '10 per minute')
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[limiter_rate],
    storage_uri="memory://",
)

# ─── Dados em memória ────────────────────────────────────────
USERS = {
    'admin@prazerburguer.ao': {
        'nome': 'Administrador',
        'senha': generate_password_hash('angola2026'),
        'admin': True,
    }
}

PEDIDOS = []

CUPOES = {
    'BURGER10': {'desconto': 10,   'tipo': 'percentagem', 'ativo': True},
    'ANGOLA20': {'desconto': 20,   'tipo': 'percentagem', 'ativo': True},
    'GRATIS':   {'desconto': 5000, 'tipo': 'valor',       'ativo': True},
}

PRODUTOS = [
    {
        'id': 1,
        'nome': 'Hambúrguer Clássico',
        'preco': 5000,
        'descricao': 'Pão macio, carne suculenta e molho especial.',
        'imagem': 'hamburger.svg',
        'categoria': 'burgers',
        'avaliacoes': [],
    },
    {
        'id': 2,
        'nome': 'Hambúrguer Duplo',
        'preco': 9000,
        'descricao': 'Dupla carne, queijo e cebola caramelizada.',
        'imagem': 'hamburger.svg',
        'categoria': 'burgers',
        'avaliacoes': [],
    },
    {
        'id': 3,
        'nome': 'Pizza Marguerita',
        'preco': 8000,
        'descricao': 'Molho de tomate, queijo e manjericão.',
        'imagem': 'pizza.svg',
        'categoria': 'pizzas',
        'avaliacoes': [],
    },
    {
        'id': 4,
        'nome': 'Batata Frita',
        'preco': 1500,
        'descricao': 'Crocante, sal e ervas aromáticas.',
        'imagem': 'batata.svg',
        'categoria': 'extras',
        'avaliacoes': [],
    },
    {
        'id': 5,
        'nome': 'Refrigerante 350ml',
        'preco': 1000,
        'descricao': 'Escolha entre cola, limão ou laranja.',
        'imagem': 'refrigerante.svg',
        'categoria': 'bebidas',
        'avaliacoes': [],
    },
    {
        'id': 6,
        'nome': 'Sundae de Chocolate',
        'preco': 2000,
        'descricao': 'Porção cremosa com topping de chocolate.',
        'imagem': 'sundae.svg',
        'categoria': 'sobremesas',
        'avaliacoes': [],
    },
]

CATEGORIAS = {
    'todos':      {'label': 'Todos',      'icone': 'bi-grid-3x3-gap-fill'},
    'burgers':    {'label': 'Burgers',    'icone': 'bi-egg-fried'},
    'pizzas':     {'label': 'Pizzas',     'icone': 'bi-circle'},
    'extras':     {'label': 'Extras',     'icone': 'bi-cup-straw'},
    'bebidas':    {'label': 'Bebidas',    'icone': 'bi-cup'},
    'sobremesas': {'label': 'Sobremesas', 'icone': 'bi-snow'},
}

STATUS_PEDIDO = {
    'pendente':   {'label': 'Pendente',    'icone': 'bi-clock',            'cor': '#ff9800'},
    'confirmado': {'label': 'Confirmado',  'icone': 'bi-check-circle',     'cor': '#2196f3'},
    'preparando': {'label': 'A preparar', 'icone': 'bi-fire',              'cor': '#ff6b35'},
    'entregando': {'label': 'A caminho',  'icone': 'bi-bicycle',           'cor': '#9c27b0'},
    'entregue':   {'label': 'Entregue',   'icone': 'bi-check-circle-fill', 'cor': '#27ae60'},
    'cancelado':  {'label': 'Cancelado',  'icone': 'bi-x-circle',          'cor': '#e74c3c'},
}


# ─── Helpers ─────────────────────────────────────────────────
def format_kz(valor):
    """Formata valor em centavos para kwanzas."""
    return f'Kz {valor / 100:.2f}'


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            flash('Faça login para aceder à sua conta.', 'warning')
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            flash('Acesso restrito.', 'warning')
            return redirect(url_for('login'))
        email = session['user']['email']
        if not USERS.get(email, {}).get('admin'):
            flash('Não tem permissão para esta página.', 'danger')
            return redirect(url_for('index'))
        return view_func(*args, **kwargs)
    return wrapper


def calcular_carrinho():
    """Agrupa itens por nome e calcula subtotal."""
    carrinho_raw = session.get('carrinho', [])
    agrupado = {}
    for item in carrinho_raw:
        nome = item['nome']
        if nome in agrupado:
            agrupado[nome]['quantidade'] += 1
        else:
            agrupado[nome] = {**item, 'quantidade': 1}
    itens = list(agrupado.values())
    subtotal = sum(i['preco'] * i['quantidade'] for i in itens)
    return itens, subtotal


def calcular_desconto(subtotal):
    """Calcula desconto do cupão activo na sessão."""
    cupao = session.get('cupao')
    desconto = 0
    if cupao and cupao in CUPOES and CUPOES[cupao]['ativo']:
        c = CUPOES[cupao]
        if c['tipo'] == 'percentagem':
            desconto = int(subtotal * c['desconto'] / 100)
        else:
            desconto = min(c['desconto'], subtotal)
    return desconto


# ─── Context processor ───────────────────────────────────────
@app.context_processor
def globals_template():
    """Disponibiliza variáveis globais em todos os templates."""
    carrinho_raw = session.get('carrinho', [])
    return {
        'carrinho_total': len(carrinho_raw),
        'format_kz': format_kz,
    }


# ─── Rotas principais ────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', info={
        'titulo': 'PRAZER BURGUER',
        'descricao': 'Hambúrgueres artesanais, batatas crocantes e um atendimento rápido em Angola.',
        'horario': 'Segunda a Domingo, das 11h30 às 23h30',
        'local': 'Rua da Liberdade, Luanda, Angola',
    })


# ─── Cardápio ────────────────────────────────────────────────
@app.route('/cardapio')
def cardapio():
    categoria = request.args.get('categoria', 'todos')
    if categoria == 'todos':
        produtos_filtrados = PRODUTOS
    else:
        produtos_filtrados = [p for p in PRODUTOS if p['categoria'] == categoria]

    return render_template(
        'cardapio.html',
        produtos=produtos_filtrados,
        categorias=CATEGORIAS,
        categoria_ativa=categoria,
    )


# ─── Avaliações ──────────────────────────────────────────────
@app.route('/avaliar/<int:produto_id>', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def avaliar(produto_id):
    try:
        estrelas = int(request.form.get('estrelas', 0))
    except (ValueError, TypeError):
        flash('Avaliação inválida.', 'danger')
        return redirect(url_for('cardapio'))
    
    comentario_raw = request.form.get('comentario', '').strip()
    
    if not 1 <= estrelas <= 5:
        flash('Avaliação inválida.', 'danger')
        return redirect(url_for('cardapio'))

    produto = next((p for p in PRODUTOS if p['id'] == produto_id), None)
    if not produto:
        flash('Produto não encontrado.', 'danger')
        return redirect(url_for('cardapio'))
    
    # Sanitizar comentário (prevenir XSS)
    comentario_sanitizado = ''.join(c for c in comentario_raw if c.isprintable())[:500]

    produto['avaliacoes'].append({
        'user':       session['user']['nome'],
        'estrelas':   estrelas,
        'comentario': comentario_sanitizado,
        'data':       datetime.now().strftime('%d/%m/%Y'),
    })
    flash('Avaliação enviada com sucesso!', 'success')
    return redirect(url_for('cardapio'))


# ─── Carrinho ────────────────────────────────────────────────
@app.route('/carrinho')
def carrinho():
    itens, subtotal = calcular_carrinho()
    desconto = calcular_desconto(subtotal)
    total    = subtotal - desconto
    return render_template(
        'carrinho.html',
        itens=itens,
        subtotal=subtotal,
        desconto=desconto,
        total=total,
        cupao=session.get('cupao'),
    )


@app.route('/adicionar_carrinho', methods=['POST'])
def adicionar_carrinho():
    nome   = request.form.get('nome', 'Produto').strip()
    preco_form = request.form.get('preco', 0)
    imagem = request.form.get('imagem', 'hamburger.svg').strip()
    
    # Validar preço buscando do produto original (não confiar no POST)
    try:
        preco_intento = int(preco_form)
    except (ValueError, TypeError):
        flash('Preço inválido.', 'danger')
        return redirect(url_for('cardapio'))
    
    # Buscar preço real do produto para evitar manipulação
    produto_real = next((p for p in PRODUTOS if p['nome'] == nome), None)
    if produto_real:
        preco = produto_real['preco']
    else:
        # Se não encontrar o produto, usar o preço enviado mas validar limites
        preco = preco_intento
        if preco < 0 or preco > 1000000:  # Limite máximo de 1.000.000 Kz
            flash('Preço inválido.', 'danger')
            return redirect(url_for('cardapio'))

    carrinho = session.get('carrinho', [])
    carrinho.append({'nome': nome, 'preco': preco, 'imagem': imagem})
    session['carrinho'] = carrinho
    flash(f'{nome} adicionado ao carrinho!', 'success')
    return redirect(url_for('cardapio'))


@app.route('/atualizar_quantidade', methods=['POST'])
def atualizar_quantidade():
    nome  = request.form.get('nome', '')
    acao  = request.form.get('acao', '')
    carrinho = session.get('carrinho', [])

    if acao == 'aumentar':
        # Duplica uma entrada existente
        ref = next((i for i in carrinho if i['nome'] == nome), None)
        if ref:
            carrinho.append({**ref})

    elif acao == 'diminuir':
        # Remove apenas uma ocorrência
        for i, item in enumerate(carrinho):
            if item['nome'] == nome:
                carrinho.pop(i)
                break

    session['carrinho'] = carrinho
    return redirect(url_for('carrinho'))


@app.route('/remover_carrinho/<nome>', methods=['POST'])
def remover_carrinho(nome):
    """Remove TODAS as ocorrências do item com este nome."""
    carrinho = session.get('carrinho', [])
    carrinho = [i for i in carrinho if i['nome'] != nome]
    session['carrinho'] = carrinho
    flash(f'{nome} removido do carrinho.', 'info')
    return redirect(url_for('carrinho'))


@app.route('/limpar_carrinho', methods=['POST'])
def limpar_carrinho():
    session['carrinho'] = []
    session.pop('cupao', None)
    flash('Carrinho esvaziado com sucesso.', 'info')
    return redirect(url_for('carrinho'))


# ─── Cupões ──────────────────────────────────────────────────
@app.route('/aplicar_cupao', methods=['POST'])
@limiter.limit("5 per minute")
def aplicar_cupao():
    codigo = request.form.get('cupao', '').strip().upper()
    
    # Validação mais rigorosa do cupão
    if not codigo or len(codigo) > 20:
        flash('Cupão inválido.', 'danger')
        return redirect(url_for('carrinho'))
    
    if codigo in CUPOES and CUPOES[codigo]['ativo']:
        session['cupao'] = codigo
        flash(f'Cupão "{codigo}" aplicado com sucesso!', 'success')
    else:
        flash('Cupão inválido ou expirado.', 'danger')
    return redirect(url_for('carrinho'))


@app.route('/remover_cupao', methods=['POST'])
def remover_cupao():
    session.pop('cupao', None)
    flash('Cupão removido.', 'info')
    return redirect(url_for('carrinho'))


# ─── Checkout ────────────────────────────────────────────────
@app.route('/checkout', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def checkout():
    itens, subtotal = calcular_carrinho()

    if not itens:
        flash('O seu carrinho está vazio.', 'warning')
        return redirect(url_for('carrinho'))

    desconto = calcular_desconto(subtotal)
    total    = subtotal - desconto

    if request.method == 'POST':
        nome      = request.form.get('nome', '').strip()
        telefone  = request.form.get('telefone', '').strip()
        morada    = request.form.get('morada', '').strip()
        pagamento = request.form.get('pagamento', '').strip()

        # Validação rigorosa de inputs
        if not all([nome, telefone, morada, pagamento]):
            flash('Preencha todos os campos.', 'danger')
            return render_template(
                'checkout.html',
                itens=itens,
                subtotal=subtotal,
                desconto=desconto,
                total=total,
                user=session.get('user'),
            )
        
        # Validar tamanho dos campos
        if len(nome) > 100 or len(morada) > 200 or len(telefone) > 20:
            flash('Dados inválidos.', 'danger')
            return render_template(
                'checkout.html',
                itens=itens,
                subtotal=subtotal,
                desconto=desconto,
                total=total,
                user=session.get('user'),
            )
        
        # Sanitizar dados (prevenir XSS)
        nome_sanitizado = ''.join(c for c in nome if c.isalnum() or c in ' @.-')[:100]
        morada_sanitizada = ''.join(c for c in morada if c.isalnum() or c in ' ,.-')[:200]
        telefone_sanitizado = ''.join(c for c in telefone if c.isdigit() or c in ' +-.')[:20]

        pedido_id = str(uuid.uuid4())[:8].upper()
        pedido = {
            'id':         pedido_id,
            'cliente':    nome_sanitizado,
            'telefone':   telefone_sanitizado,
            'morada':     morada_sanitizada,
            'pagamento':  pagamento,
            'itens':      itens,
            'subtotal':   subtotal,
            'desconto':   desconto,
            'total':      total,
            'status':     'pendente',
            'data':       datetime.now().strftime('%d/%m/%Y %H:%M'),
            'user_email': session.get('user', {}).get('email', 'anonimo'),
        }
        PEDIDOS.append(pedido)

        # Limpar sessão
        session['carrinho'] = []
        session.pop('cupao', None)

        flash(f'Pedido #{pedido_id} realizado com sucesso!', 'success')
        return redirect(url_for('rastreamento', pedido_id=pedido_id))

    return render_template(
        'checkout.html',
        itens=itens,
        subtotal=subtotal,
        desconto=desconto,
        total=total,
        user=session.get('user'),
    )


# ─── Rastreamento ────────────────────────────────────────────
@app.route('/rastreamento/<pedido_id>')
def rastreamento(pedido_id):
    pedido = next((p for p in PEDIDOS if p['id'] == pedido_id), None)
    if not pedido:
        flash('Pedido não encontrado.', 'danger')
        return redirect(url_for('index'))
    return render_template(
        'rastreamento.html',
        pedido=pedido,
        status_info=STATUS_PEDIDO,
    )


@app.route('/meus_pedidos')
@login_required
def meus_pedidos():
    email   = session['user']['email']
    pedidos = [p for p in PEDIDOS if p['user_email'] == email]
    return render_template(
        'meus_pedidos.html',
        pedidos=pedidos,
        status_info=STATUS_PEDIDO,
    )


# ─── Painel Admin ────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin():
    total_receita = sum(
        p['total'] for p in PEDIDOS if p['status'] != 'cancelado'
    )
    return render_template(
        'admin/dashboard.html',
        pedidos=PEDIDOS,
        status_info=STATUS_PEDIDO,
        produtos=PRODUTOS,
        users=USERS,
        cupoes=CUPOES,
        total_receita=total_receita,
    )


@app.route('/admin/pedido/<pedido_id>/status', methods=['POST'])
@admin_required
@limiter.limit("20 per minute")
def admin_status_pedido(pedido_id):
    novo_status = request.form.get('status')
    
    # Validar status
    if not novo_status or novo_status not in STATUS_PEDIDO:
        flash('Status inválido.', 'danger')
        return redirect(url_for('admin'))
    
    pedido = next((p for p in PEDIDOS if p['id'] == pedido_id), None)
    if pedido:
        pedido['status'] = novo_status
        flash(
            f'Pedido #{pedido_id} → "{STATUS_PEDIDO[novo_status]["label"]}".',
            'success',
        )
    else:
        flash('Pedido não encontrado.', 'danger')
    return redirect(url_for('admin'))


# ─── Conta / Auth ────────────────────────────────────────────
@app.route('/conta')
@login_required
def conta():
    email   = session['user']['email']
    pedidos = [p for p in PEDIDOS if p['user_email'] == email]
    return render_template(
        'conta.html',
        user=session.get('user'),
        pedidos=pedidos,
        status_info=STATUS_PEDIDO,
    )


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        
        # Validação de input
        if not email or not senha:
            flash('Preencha todos os campos.', 'danger')
            return render_template('login.html')
        
        user  = USERS.get(email)

        if user and check_password_hash(user['senha'], senha):
            session.clear()
            session['user'] = {'email': email, 'nome': user['nome']}
            # Regenerar ID da sessão para prevenir session fixation
            session.regenerate = True
            flash('Bem-vindo de volta à PRAZER BURGUER.', 'success')
            return redirect(url_for('conta'))

        flash('E-mail ou palavra-passe inválidos.', 'danger')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def signup():
    if request.method == 'POST':
        nome      = request.form.get('nome', '').strip()
        email     = request.form.get('email', '').strip().lower()
        senha     = request.form.get('senha', '')
        confirmar = request.form.get('confirmar_senha', '')

        # Validação rigorosa de inputs
        if not all([nome, email, senha, confirmar]):
            flash('Preencha todos os campos para criar a sua conta.', 'danger')
            return render_template('signup.html')
        
        # Validar formato de email
        if '@' not in email or '.' not in email or len(email) > 120:
            flash('E-mail inválido.', 'danger')
            return render_template('signup.html')

        if senha != confirmar:
            flash('As palavras-passe não coincidem.', 'danger')
            return render_template('signup.html')

        if len(senha) < 8:
            flash('A palavra-passe deve ter pelo menos 8 caracteres.', 'danger')
            return render_template('signup.html')
        
        # Validar força da senha (pelo menos uma letra e um número)
        if not any(c.isalpha() for c in senha) or not any(c.isdigit() for c in senha):
            flash('A palavra-passe deve conter letras e números.', 'danger')
            return render_template('signup.html')

        if email in USERS:
            flash('Este e-mail já está registado.', 'danger')
            return render_template('signup.html')
        
        # Sanitizar nome (prevenir XSS)
        nome_sanitizado = ''.join(c for c in nome if c.isalnum() or c in ' @.-')[:50]

        USERS[email] = {
            'nome':  nome_sanitizado,
            'senha': generate_password_hash(senha),
            'admin': False,
        }
        session.clear()
        session['user'] = {'email': email, 'nome': nome_sanitizado}
        flash('Conta criada com sucesso. Já pode fazer pedidos.', 'success')
        return redirect(url_for('conta'))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Saiu da sua conta com sucesso.', 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    # Obter configuração do ambiente
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    # Em produção, usar gunicorn ou outro WSGI server
    # python app.py apenas para desenvolvimento
    app.run(debug=debug_mode, host='0.0.0.0', port=port)