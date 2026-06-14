# 🔒 Guia de Segurança - PRAZER BURGER

## Mudanças Implementadas

### ✅ Crítico (Resolvido)

1. **SECRET_KEY via Environment Variable**
   - Removido hardcoded `prazer-burguer-2026`
   - Agora usa `os.environ.get('SECRET_KEY')`
   - Ver `.env.example` para configuração

2. **Debug Mode Desativado**
   - `debug=True` removido do código
   - Controlado por `FLASK_DEBUG` environment variable
   - Padrão: `false` (seguro para produção)

3. **Proteção CSRF**
   - Flask-WTF CSRFProtect implementado
   - Todos os forms POST agora protegidos
   - Token CSRF necessário em submissões

4. **Validação de Preço no Backend**
   - Preço não vem mais diretamente do POST
   - Busca preço real da lista de PRODUTOS
   - Previne manipulação de preços pelo usuário

5. **Session Fixation Prevention**
   - Session regenerada após login
   - `session.regenerate = True` implementado

### ✅ Alto (Resolvido)

6. **Rate Limiting**
   - Flask-Limiter implementado
   - Login: 10 requests/minuto
   - Signup: 5 requests/minuto
   - Cupons: 5 requests/minuto
   - Checkout: 10 requests/minuto
   - Admin: 20 requests/minuto

7. **Headers de Segurança**
   - `SESSION_COOKIE_HTTPONLY=True` (previne XSS access)
   - `SESSION_COOKIE_SAMESITE='Lax'` (previne CSRF)
   - `SESSION_COOKIE_SECURE` (em produção)

8. **Validação de Inputs**
   - Email: formato validado, max 120 chars
   - Senha: min 8 chars, requer letras e números
   - Nome: sanitizado, max 50 chars
   - Comentários: apenas caracteres imprimíveis, max 500 chars
   - Telefone: apenas dígitos e símbolos válidos

### ✅ Médio (Resolvido)

9. **Templates Criados**
   - `templates/meus_pedidos.html` criado
   - `templates/admin/dashboard.html` criado

10. **Sanitização XSS**
    - Nomes de usuário sanitizados
    - Comentários de avaliação sanitizados
    - Dados de checkout sanitizados

### 📋 Configuração

#### Desenvolvimento
```bash
cp .env.example .env
# Edite .env com suas configurações
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export FLASK_ENV=development
export FLASK_DEBUG=true
pip install -r requirements.txt
python app.py
```

#### Produção
```bash
export SECRET_KEY=<sua-chave-segura-gerada>
export FLASK_ENV=production
export FLASK_DEBUG=false
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:5000 app:app
```

### 🔐 Gerar SECRET_KEY Segura
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 📊 Próximos Passos Recomendados

1. **Banco de Dados**
   - Migrar de memória para SQLite/PostgreSQL
   - Implementar SQLAlchemy com migrations

2. **HTTPS**
   - Configurar SSL/TLS em produção
   - Redirect HTTP → HTTPS

3. **Logging**
   - Implementar log de auditoria
   - Monitorar tentativas de login falhas

4. **Validação de Upload**
   - Se permitir upload de imagens, validar tipos e tamanhos

5. **Testes de Segurança**
   - Rodar OWASP ZAP ou similar
   - Testes de penetração regulares

## Referências
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/stable/security/)
- [Python Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Python_Security_Cheat_Sheet.html)
