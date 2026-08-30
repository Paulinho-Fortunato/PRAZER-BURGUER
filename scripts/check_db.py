#!/usr/bin/env python
"""
Script para verificar estado do banco de dados
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import Database

def check_database():
    """Verificar integridade do banco de dados"""
    
    with app.app_context():
        print("\n🔍 Verificando banco de dados...\n")
        
        # 1. Estatísticas gerais
        print("📊 Estatísticas Gerais:")
        try:
            stats = Database.obter_estatisticas()
            print(f"  ✅ Usuários: {stats['total_usuarios']}")
            print(f"  ✅ Produtos: {stats['produtos_total']}")
            print(f"  ✅ Pedidos: {stats['total_pedidos']}")
            print(f"  ✅ Receita: Kz {stats['total_receita'] / 100:.2f}")
            print(f"\n  Pedidos por Status:")
            for status, count in stats['pedidos_por_status'].items():
                print(f"    - {status}: {count}")
        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")
        
        # 2. Produtos
        print("\n🍔 Produtos:")
        try:
            produtos = Database.buscar_todos_produtos()
            if produtos:
                for produto in produtos[:5]:  # Primeiros 5
                    print(f"  ✅ {produto['nome']} - Kz {produto['preco'] / 100:.2f}")
                if len(produtos) > 5:
                    print(f"  ... e mais {len(produtos) - 5} produtos")
            else:
                print("  ⚠️  Nenhum produto encontrado")
        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")
        
        # 3. Cupões
        print("\n🎟️  Cupões:")
        try:
            cupoes = Database.buscar_todos_cupoes()
            if cupoes:
                for cupao in cupoes:
                    valor = f"{cupao['desconto']}%" if cupao['tipo'] == 'percentagem' else f"Kz {cupao['desconto'] / 100:.2f}"
                    print(f"  ✅ {cupao['codigo']} - {valor}")
            else:
                print("  ⚠️  Nenhum cupão encontrado")
        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")
        
        # 4. Coleções
        print("\n📚 Coleções:")
        try:
            db = app.extensions.get('pymongo').db
            collections = db.list_collection_names()
            for col in sorted(collections):
                count = db[col].count_documents({})
                print(f"  ✅ {col}: {count} documentos")
        except Exception as e:
            print(f"  ❌ Erro: {str(e)}")
        
        print("\n✅ Verificação concluída!\n")

if __name__ == '__main__':
    check_database()
