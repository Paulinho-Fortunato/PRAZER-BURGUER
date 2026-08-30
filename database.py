"""
Configuração e modelos de banco de dados MongoDB
"""
from flask_pymongo import PyMongo
from datetime import datetime
from bson.objectid import ObjectId

mongo = PyMongo()

class Database:
    """Classe para gerenciar operações com MongoDB"""
    
    @staticmethod
    def init_db(app):
        """Inicializar conexão com MongoDB"""
        mongo.init_app(app)
        
    # ─── USUARIOS ────────────────────────────────────────────────
    @staticmethod
    def criar_usuario(email, nome, senha_hash, telefone=None, morada=None, admin=False):
        """Criar novo usuário"""
        usuario = {
            'email': email,
            'nome': nome,
            'senha_hash': senha_hash,
            'telefone': telefone,
            'morada': morada,
            'admin': admin,
            'ativo': True,
            'tentativas_login': 0,
            'bloqueado_ate': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        resultado = mongo.db.usuarios.insert_one(usuario)
        return str(resultado.inserted_id)
    
    @staticmethod
    def buscar_usuario_email(email):
        """Buscar usuário por email"""
        return mongo.db.usuarios.find_one({'email': email})
    
    @staticmethod
    def buscar_usuario_id(user_id):
        """Buscar usuário por ID"""
        return mongo.db.usuarios.find_one({'_id': ObjectId(user_id)})
    
    @staticmethod
    def atualizar_usuario(user_id, dados):
        """Atualizar dados do usuário"""
        dados['updated_at'] = datetime.utcnow()
        mongo.db.usuarios.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': dados}
        )
    
    @staticmethod
    def registrar_tentativa_login_falha(email):
        """Registrar tentativa de login falhada"""
        usuario = mongo.db.usuarios.find_one({'email': email})
        if usuario:
            tentativas = usuario.get('tentativas_login', 0) + 1
            mongo.db.usuarios.update_one(
                {'email': email},
                {'$set': {'tentativas_login': tentativas}}
            )
    
    @staticmethod
    def bloquear_usuario(email, minutos=15):
        """Bloquear usuário após múltiplas tentativas"""
        from datetime import timedelta
        bloqueado_ate = datetime.utcnow() + timedelta(minutes=minutos)
        mongo.db.usuarios.update_one(
            {'email': email},
            {'$set': {'bloqueado_ate': bloqueado_ate}}
        )
    
    @staticmethod
    def desbloquear_usuario(email):
        """Desbloquear usuário e resetar tentativas"""
        mongo.db.usuarios.update_one(
            {'email': email},
            {'$set': {'tentativas_login': 0, 'bloqueado_ate': None}}
        )
    
    # ─── PRODUTOS ────────────────────────────────────────────────
    @staticmethod
    def criar_produto(nome, descricao, preco, categoria, imagem, estoque=10):
        """Criar novo produto"""
        produto = {
            'nome': nome,
            'descricao': descricao,
            'preco': preco,  # em centavos
            'categoria': categoria,
            'imagem': imagem,
            'estoque': estoque,
            'ativo': True,
            'avaliacoes': [],
            'vendas': 0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        resultado = mongo.db.produtos.insert_one(produto)
        return str(resultado.inserted_id)
    
    @staticmethod
    def buscar_todos_produtos(categoria=None):
        """Buscar todos os produtos"""
        query = {'ativo': True}
        if categoria and categoria != 'todos':
            query['categoria'] = categoria
        return list(mongo.db.produtos.find(query).sort('nome', 1))
    
    @staticmethod
    def buscar_produto_id(produto_id):
        """Buscar produto por ID"""
        return mongo.db.produtos.find_one({'_id': ObjectId(produto_id)})
    
    @staticmethod
    def buscar_produto_nome(nome):
        """Buscar produto por nome"""
        return mongo.db.produtos.find_one({'nome': nome, 'ativo': True})
    
    @staticmethod
    def atualizar_produto(produto_id, dados):
        """Atualizar dados do produto"""
        dados['updated_at'] = datetime.utcnow()
        mongo.db.produtos.update_one(
            {'_id': ObjectId(produto_id)},
            {'$set': dados}
        )
    
    @staticmethod
    def decrementar_estoque(produto_id, quantidade):
        """Decrementar estoque de produto"""
        mongo.db.produtos.update_one(
            {'_id': ObjectId(produto_id)},
            {'$inc': {'estoque': -quantidade}}
        )
    
    @staticmethod
    def incrementar_vendas(produto_id, quantidade):
        """Incrementar contador de vendas"""
        mongo.db.produtos.update_one(
            {'_id': ObjectId(produto_id)},
            {'$inc': {'vendas': quantidade}}
        )
    
    @staticmethod
    def produtosPopulares(limite=10):
        """Buscar produtos mais vendidos"""
        return list(mongo.db.produtos.find({'ativo': True})
                   .sort('vendas', -1)
                   .limit(limite))
    
    # ─── PEDIDOS ──────────────────────────────────────────────────
    @staticmethod
    def criar_pedido(user_email, cliente, telefone, morada, itens, subtotal, desconto, total, metodo_pagamento, pedido_id):
        """Criar novo pedido"""
        pedido = {
            'pedido_id': pedido_id,
            'user_email': user_email,
            'cliente': cliente,
            'telefone': telefone,
            'morada': morada,
            'itens': itens,
            'subtotal': subtotal,
            'desconto': desconto,
            'total': total,
            'metodo_pagamento': metodo_pagamento,
            'status': 'pendente',
            'historico_status': [
                {
                    'status': 'pendente',
                    'timestamp': datetime.utcnow(),
                    'observacao': 'Pedido criado'
                }
            ],
            'whatsapp_enviado': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        resultado = mongo.db.pedidos.insert_one(pedido)
        return str(resultado.inserted_id)
    
    @staticmethod
    def buscar_pedido_id_string(pedido_id):
        """Buscar pedido por string ID"""
        return mongo.db.pedidos.find_one({'pedido_id': pedido_id})
    
    @staticmethod
    def buscar_pedidos_usuario(user_email):
        """Buscar todos os pedidos do usuário"""
        return list(mongo.db.pedidos.find({'user_email': user_email})
                   .sort('created_at', -1))
    
    @staticmethod
    def buscar_todos_pedidos(filtro=None, limite=100, pagina=1):
        """Buscar todos os pedidos (admin)"""
        query = {}
        if filtro:
            if 'status' in filtro:
                query['status'] = filtro['status']
            if 'data_inicio' in filtro and 'data_fim' in filtro:
                query['created_at'] = {
                    '$gte': filtro['data_inicio'],
                    '$lte': filtro['data_fim']
                }
        
        skip = (pagina - 1) * limite
        return list(mongo.db.pedidos.find(query)
                   .sort('created_at', -1)
                   .skip(skip)
                   .limit(limite))
    
    @staticmethod
    def atualizar_status_pedido(pedido_id, novo_status, observacao=''):
        """Atualizar status do pedido"""
        pedido = mongo.db.pedidos.find_one({'pedido_id': pedido_id})
        if pedido:
            novo_historico = pedido.get('historico_status', [])
            novo_historico.append({
                'status': novo_status,
                'timestamp': datetime.utcnow(),
                'observacao': observacao
            })
            
            mongo.db.pedidos.update_one(
                {'pedido_id': pedido_id},
                {'$set': {
                    'status': novo_status,
                    'historico_status': novo_historico,
                    'updated_at': datetime.utcnow()
                }}
            )
    
    @staticmethod
    def marcar_whatsapp_enviado(pedido_id):
        """Marcar que mensagem WhatsApp foi enviada"""
        mongo.db.pedidos.update_one(
            {'pedido_id': pedido_id},
            {'$set': {'whatsapp_enviado': True}}
        )
    
    # ─── AVALIACOES ───────────────────────────────────────────────
    @staticmethod
    def adicionar_avaliacao(produto_id, user_email, estrelas, comentario):
        """Adicionar avaliação a um produto"""
        avaliacao = {
            'user_email': user_email,
            'estrelas': estrelas,
            'comentario': comentario,
            'timestamp': datetime.utcnow()
        }
        mongo.db.produtos.update_one(
            {'_id': ObjectId(produto_id)},
            {'$push': {'avaliacoes': avaliacao}}
        )
    
    @staticmethod
    def buscar_avaliacoes_produto(produto_id):
        """Buscar avaliações de um produto"""
        produto = mongo.db.produtos.find_one({'_id': ObjectId(produto_id)})
        return produto.get('avaliacoes', []) if produto else []
    
    # ─── CUPOES ───────────────────────────────────────────────────
    @staticmethod
    def criar_cupao(codigo, desconto, tipo, data_expiracao=None):
        """Criar novo cupão"""
        cupao = {
            'codigo': codigo.upper(),
            'desconto': desconto,
            'tipo': tipo,  # 'percentagem' ou 'valor'
            'ativo': True,
            'data_expiracao': data_expiracao,
            'usos': 0,
            'created_at': datetime.utcnow(),
        }
        resultado = mongo.db.cupoes.insert_one(cupao)
        return str(resultado.inserted_id)
    
    @staticmethod
    def buscar_cupao(codigo):
        """Buscar cupão por código"""
        return mongo.db.cupoes.find_one({'codigo': codigo.upper(), 'ativo': True})
    
    @staticmethod
    def incrementar_uso_cupao(codigo):
        """Incrementar contador de usos do cupão"""
        mongo.db.cupoes.update_one(
            {'codigo': codigo.upper()},
            {'$inc': {'usos': 1}}
        )
    
    @staticmethod
    def buscar_todos_cupoes():
        """Buscar todos os cupões (admin)"""
        return list(mongo.db.cupoes.find().sort('created_at', -1))
    
    # ─── AUDITORIA ────────────────────────────────────────────────
    @staticmethod
    def registrar_auditoria(tipo, usuario_email, acao, detalhes=None, ip_address=None):
        """Registrar evento de auditoria"""
        evento = {
            'tipo': tipo,  # 'login', 'logout', 'pedido', 'admin_action'
            'usuario_email': usuario_email,
            'acao': acao,
            'detalhes': detalhes or {},
            'ip_address': ip_address,
            'timestamp': datetime.utcnow(),
        }
        mongo.db.auditoria.insert_one(evento)
    
    @staticmethod
    def buscar_auditoria(filtro=None, limite=100):
        """Buscar eventos de auditoria"""
        query = filtro or {}
        return list(mongo.db.auditoria.find(query)
                   .sort('timestamp', -1)
                   .limit(limite))
    
    # ─── ESTATISTICAS ────────────────────────────────────────────
    @staticmethod
    def obter_estatisticas():
        """Obter estatísticas gerais da plataforma"""
        total_pedidos = mongo.db.pedidos.count_documents({})
        total_usuarios = mongo.db.usuarios.count_documents({})
        total_receita = sum(p.get('total', 0) for p in mongo.db.pedidos.find({'status': {'$ne': 'cancelado'}}))
        
        pedidos_por_status = {}
        for status in ['pendente', 'confirmado', 'preparando', 'entregando', 'entregue', 'cancelado']:
            pedidos_por_status[status] = mongo.db.pedidos.count_documents({'status': status})
        
        return {
            'total_pedidos': total_pedidos,
            'total_usuarios': total_usuarios,
            'total_receita': total_receita,
            'pedidos_por_status': pedidos_por_status,
            'produtos_total': mongo.db.produtos.count_documents({'ativo': True}),
        }
