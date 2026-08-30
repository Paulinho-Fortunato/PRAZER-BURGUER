#!/usr/bin/env python
"""
Script para inicializar banco de dados com dados padrão
"""
import sys
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Adicionar raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, mongo
from database import Database
from utils import Seguranca

def init_database():
    """Inicializar banco de dados com dados padrão"""
    
    with app.app_context():
        print("\n🚀 Inicializando banco de dados...\n")
        
        # 1. Criar admin
        print("📝 Criando usuário admin...")
        try:
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@prazerburguer.ao')
            admin_senha = input(f"Senha para admin ({admin_email}): ") or "A1dmin@2026"
            
            usuario_existente = Database.buscar_usuario_email(admin_email)
            if usuario_existente:
                print(f"⚠️  Usuário {admin_email} já existe!")
            else:
                senha_hash = generate_password_hash(admin_senha)
                Database.criar_usuario(
                    email=admin_email,
                    nome="Administrador",
                    senha_hash=senha_hash,
                    admin=True
                )
                print(f"✅ Admin criado: {admin_email}")
        except Exception as e:
            print(f"❌ Erro ao criar admin: {str(e)}")
        
        # 2. Criar produtos
        print("\n🍔 Adicionando produtos...")
        produtos = [
            {
                'nome': 'Hambúrguer Clássico',
                'descricao': 'Pão macio, carne suculenta e molho especial.',
                'preco': 500000,  # 5000 Kz
                'categoria': 'burgers',
                'imagem': 'hamburger.svg',
                'estoque': 50
            },
            {
                'nome': 'Hambúrguer Duplo',
                'descricao': 'Dupla carne, queijo e cebola caramelizada.',
                'preco': 900000,  # 9000 Kz
                'categoria': 'burgers',
                'imagem': 'hamburger.svg',
                'estoque': 40
            },
            {
                'nome': 'Pizza Marguerita',
                'descricao': 'Molho de tomate, queijo e manjericão.',
                'preco': 800000,  # 8000 Kz
                'categoria': 'pizzas',
                'imagem': 'pizza.svg',
                'estoque': 30
            },
            {
                'nome': 'Batata Frita',
                'descricao': 'Crocante, sal e ervas aromáticas.',
                'preco': 150000,  # 1500 Kz
                'categoria': 'extras',
                'imagem': 'batata.svg',
                'estoque': 100
            },
            {
                'nome': 'Refrigerante 350ml',
                'descricao': 'Escolha entre cola, limão ou laranja.',
                'preco': 100000,  # 1000 Kz
                'categoria': 'bebidas',
                'imagem': 'refrigerante.svg',
                'estoque': 200
            },
            {
                'nome': 'Sundae de Chocolate',
                'descricao': 'Porção cremosa com topping de chocolate.',
                'preco': 200000,  # 2000 Kz
                'categoria': 'sobremesas',
                'imagem': 'sundae.svg',
                'estoque': 50
            },
        ]
        
        try:
            for produto in produtos:
                existente = Database.buscar_produto_nome(produto['nome'])
                if existente:
                    print(f"  ⚠️  {produto['nome']} já existe")
                else:
                    Database.criar_produto(
                        nome=produto['nome'],
                        descricao=produto['descricao'],
                        preco=produto['preco'],
                        categoria=produto['categoria'],
                        imagem=produto['imagem'],
                        estoque=produto['estoque']
                    )
                    print(f"  ✅ {produto['nome']}")
        except Exception as e:
            print(f"❌ Erro ao adicionar produtos: {str(e)}")
        
        # 3. Criar cupões
        print("\n🎟️  Adicionando cupões...")
        cupoes = [
            {
                'codigo': 'BURGER10',
                'desconto': 10,
                'tipo': 'percentagem',
                'data_expiracao': datetime.utcnow() + timedelta(days=30)
            },
            {
                'codigo': 'ANGOLA20',
                'desconto': 20,
                'tipo': 'percentagem',
                'data_expiracao': datetime.utcnow() + timedelta(days=30)
            },
            {
                'codigo': 'GRATIS',
                'desconto': 500000,  # 5000 Kz
                'tipo': 'valor',
                'data_expiracao': datetime.utcnow() + timedelta(days=15)
            },
        ]
        
        try:
            for cupao in cupoes:
                existente = Database.buscar_cupao(cupao['codigo'])
                if existente:
                    print(f"  ⚠️  {cupao['codigo']} já existe")
                else:
                    Database.criar_cupao(
                        codigo=cupao['codigo'],
                        desconto=cupao['desconto'],
                        tipo=cupao['tipo'],
                        data_expiracao=cupao['data_expiracao']
                    )
                    print(f"  ✅ {cupao['codigo']}")
        except Exception as e:
            print(f"❌ Erro ao adicionar cupões: {str(e)}")
        
        # 4. Criar índices
        print("\n📊 Criando índices...")
        try:
            mongo.db.usuarios.create_index('email', unique=True)
            mongo.db.cupoes.create_index('codigo', unique=True)
            print("  ✅ Índices criados")
        except Exception as e:
            print(f"  ⚠️  Índices já existem: {str(e)}")
        
        # 5. Verificar estatísticas
        print("\n📈 Estatísticas do banco de dados:")
        try:
            stats = Database.obter_estatisticas()
            print(f"  👥 Usuários: {stats['total_usuarios']}")
            print(f"  🍔 Produtos: {stats['produtos_total']}")
            print(f"  📦 Pedidos: {stats['total_pedidos']}")
            print(f"  💰 Receita: {stats['total_receita']} centavos")
        except Exception as e:
            print(f"❌ Erro ao obter estatísticas: {str(e)}")
        
        print("\n✅ Banco de dados inicializado com sucesso!\n")
        print("Próximos passos:")
        print(f"  1. Fazer login em http://localhost:5000/login")
        print(f"  2. Email: {os.environ.get('ADMIN_EMAIL', 'admin@prazerburguer.ao')}")
        print(f"  3. Senha: A1dmin@2026 (ou a que você definiu)")
        print(f"  4. Acessar admin: http://localhost:5000/admin\n")

if __name__ == '__main__':
    init_database()
