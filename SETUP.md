# 🚀 GUIA DE SETUP - PRAZER BURGUER

**Versão**: 2.0  
**Data**: 30/08/2026  
**Status**: Production Ready

---

## 📋 Pré-requisitos

- Python 3.8+
- Git
- Conta MongoDB Atlas (gratuito)
- Conta WhatsApp Business (opcional - pode usar número pessoal)

---

## 1️⃣ CONFIGURAÇÃO LOCAL (Desenvolvimento)

### 1.1 Clonar Repositório

```bash
git clone https://github.com/Paulinho-Fortunato/PRAZER-BURGUER.git
cd PRAZER-BURGUER
```

### 1.2 Criar Ambiente Virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 1.3 Instalar Dependências

```bash
pip install -r requirements.txt
```

### 1.4 Gerar Chaves Seguras

```bash
# Gerar SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Exemplo de saída:
# a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

### 1.5 Configurar Arquivo .env

```bash
# Copiar template
cp .env.example .env
```

**Editar `.env` com seus valores:**

```bash
# FLASK CONFIGURATION
FLASK_ENV=development
FLASK_DEBUG=true
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# DATABASE - MONGODB LOCAL (para dev) OU ATLAS
MONGODB_URI=mongodb://localhost:27017/prazer_burguer
# OU
# MONGODB_URI=mongodb+srv://usuario:senha@cluster0.mongodb.net/prazer_burguer?retryWrites=true&w=majority
MONGODB_DB_NAME=prazer_burguer

# ADMIN CREDENTIALS (ALTERAR OBRIGATORIAMENTE!)
ADMIN_EMAIL=seu-email@domain.com
ADMIN_PASSWORD_HASH=hashed_password_aqui

# WHATSAPP (opcional por enquanto)
WHATSAPP_BUSINESS_NUMBER=+244924123456

# SECURITY
SESSION_TIMEOUT_MINUTES=30
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15

# PRODUCTION
PORT=5000
HOST=0.0.0.0
```

### 1.6 Configurar MongoDB Local (Opcional)

```bash
# Se tiver MongoDB instalado localmente
mongod

# Verificar conexão
mongo
```

### 1.7 Rodar Aplicação

```bash
python app.py
```

**Acessar:**
- 🏠 Home: http://localhost:5000
- 📱 Cardápio: http://localhost:5000/cardapio
- 👤 Login: http://localhost:5000/login
- 🔧 Admin: http://localhost:5000/admin (após login como admin)

---

## 2️⃣ CONFIGURAR MONGODB ATLAS (Recomendado)

### 2.1 Criar Conta

1. Ir para https://www.mongodb.com/cloud/atlas
2. Criar conta gratuita
3. Criar novo projeto: `PRAZER-BURGUER`

### 2.2 Criar Cluster

1. **Build a Database** → **M0 Free** (gratuito)
2. Selecionar provider (AWS, Azure, Google)
3. Região: **Frankfurt** ou mais próxima
4. Esperar criação (~5 min)

### 2.3 Configurar Segurança

**Database Access:**
1. Add Database User
2. Username: `prazer_user`
3. Password: (Gerar senha segura - mínimo 12 caracteres)
4. Database User Privileges: `Atlas admin`
5. Save

**Network Access:**
1. Add IP Address
2. Allow Access from Anywhere: `0.0.0.0/0` (desenvolvimento)
3. Confirm

### 2.4 Obter Connection String

1. Cluster → **Connect**
2. Selecionar **Drivers**
3. Copiar connection string:

```
mongodb+srv://prazer_user:PASSWORD@cluster0.mongodb.net/prazer_burguer?retryWrites=true&w=majority
```

4. Substituir `PASSWORD` pela senha criada

### 2.5 Adicionar ao .env

```bash
MONGODB_URI=mongodb+srv://prazer_user:SUA_SENHA@cluster0.mongodb.net/prazer_burguer?retryWrites=true&w=majority
```

---

## 3️⃣ INICIALIZAR BANCO DE DADOS

### 3.1 Rodar Script de Setup

```bash
python scripts/init_db.py
```

**Isso vai:**
- ✅ Criar coleções no MongoDB
- ✅ Criar índices
- ✅ Adicionar usuário admin
- ✅ Adicionar produtos padrão
- ✅ Adicionar cupões de teste

### 3.2 Verificar Dados (Opcional)

```bash
python scripts/check_db.py
```

---

## 4️⃣ PRIMEIRO LOGIN

### 4.1 Credenciais Admin Padrão

```
Email: admin@prazerburguer.ao
Senha: A1dmin@2026 (ALTERAR IMEDIATAMENTE!)
```

### 4.2 Mudar Senha Admin

1. Fazer login em http://localhost:5000/login
2. Ir para conta
3. Mudar senha

---

## 5️⃣ CONFIGURAR WHATSAPP (Opcional)

### 5.1 Usando Número Pessoal (Simples)

A aplicação automaticamente cria links WhatsApp:

```
https://wa.me/+244924123456?text=Pedido%23ABC123...
```

**Não requer configuração extra!**

### 5.2 Usando WhatsApp Business API (Avançado)

1. Registrar em https://www.whatsapp.com/business/
2. Obter `Business Phone ID` e `API Token`
3. Adicionar ao `.env`:

```bash
WHATSAPP_BUSINESS_PHONE_ID=seu-phone-id
WHATSAPP_BUSINESS_ACCOUNT_ID=seu-account-id
WHATSAPP_API_TOKEN=seu-api-token
```

---

## 6️⃣ DEPLOY EM PRODUÇÃO

### 6.1 Preparar Aplicação

```bash
# Gerar nova SECRET_KEY para produção
python -c "import secrets; print(secrets.token_hex(32))"

# Gerar senha admin segura
python -c "from utils import Seguranca; print(Seguranca.gerar_senha_admin())"
```

### 6.2 Deploy no Vercel

**Criar arquivo `vercel.json`:**

```json
{
  "buildCommand": "pip install -r requirements.txt",
  "devCommand": "python app.py",
  "env": {
    "FLASK_ENV": "production",
    "FLASK_DEBUG": "false"
  },
  "functions": {
    "app.py": {
      "memory": 1024,
      "maxDuration": 60
    }
  }
}
```

**Via CLI:**

```bash
npm i -g vercel
vercel login
vercel --prod
```

**Adicionar variáveis de ambiente no Vercel:**

1. Project Settings → Environment Variables
2. Adicionar:
   - `FLASK_ENV`: production
   - `SECRET_KEY`: (nova chave)
   - `MONGODB_URI`: (connection string)
   - Outras variáveis

### 6.3 Deploy no Heroku

**Criar arquivo `Procfile`:**

```
web: gunicorn -w 4 -b 0.0.0.0:$PORT app:app
```

**Deploy:**

```bash
heroku login
heroku create prazer-burguer
git push heroku main
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=sua-chave-secreta
```

### 6.4 Deploy no Railway.app

1. Conectar GitHub
2. Selecionar repositório
3. Configurar variáveis de ambiente
4. Deploy automático

---

## 7️⃣ TESTES

### 7.1 Rodar Testes

```bash
python -m pytest tests/ -v
```

### 7.2 Testar Endpoints

```bash
# Home
curl http://localhost:5000/

# Cardápio
curl http://localhost:5000/cardapio

# Admin Dashboard
curl http://localhost:5000/admin
```

---

## 8️⃣ ESTRUTURA DE ARQUIVOS

```
PRAZER-BURGUER/
├── app.py                      # Aplicação principal
├── config.py                   # Configuração
├── database.py                 # Camada de banco de dados
├── utils.py                    # Utilitários
├── requirements.txt            # Dependências
├── .env.example               # Variáveis de ambiente (exemplo)
├── .gitignore                 # Arquivos para ignorar
├── SETUP.md                   # Este arquivo
├── README.md                  # Documentação geral
│
├── templates/
│   ├── base.html              # Template base
│   ├── index.html             # Home
│   ├── cardapio.html          # Cardápio
│   ├── carrinho.html          # Carrinho
│   ├── checkout.html          # Checkout com WhatsApp
│   ├── rastreamento.html      # Rastreamento
│   ├── login.html             # Login
│   ├── signup.html            # Signup
│   ├── conta.html             # Conta do usuário
│   ├── meus_pedidos.html      # Meus pedidos
│   ├── 404.html               # Página não encontrada
│   ├── 500.html               # Erro interno
│   │
│   └── admin/
│       ├── dashboard.html     # Dashboard com gráficos
│       ├── pedidos.html       # Gerenciar pedidos
│       ├── produtos.html      # CRUD de produtos
│       ├── cupoes.html        # Gerenciar cupões
│       └── auditoria.html     # Logs de auditoria
│
├── static/
│   ├── css/
│   │   ├── style.css          # Estilos principais
│   │   └── dashboard.css      # Estilos do admin
│   ├── js/
│   │   ├── main.js            # JavaScript principal
│   │   ├── chart.js           # Gráficos (Chart.js)
│   │   └── whatsapp.js        # Integração WhatsApp
│   └── images/
│       ├── produtos/          # Imagens dos produtos
│       └── icons/             # Ícones
│
└── scripts/
    ├── init_db.py             # Inicializar banco de dados
    └── check_db.py            # Verificar dados
```

---

## 9️⃣ TROUBLESHOOTING

### Erro: `ModuleNotFoundError`

```bash
# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

### Erro: `Connection refused` (MongoDB)

```bash
# Verificar se MongoDB está rodando
sudo systemctl status mongod  # Linux
brew services list             # macOS
```

### Erro: `SECRET_KEY not set`

```bash
# Adicionar ao .env
SECRET_KEY=sua-chave-aqui
```

### Erro: `CSRF token missing`

Adicionar `{{ csrf_token() }}` ao formulário:

```html
<form method="POST">
    {{ csrf_token() }}
    ...
</form>
```

---

## 🔟 PRÓXIMOS PASSOS

- [ ] Configurar SSL/TLS em produção
- [ ] Implementar 2FA para admin
- [ ] Adicionar testes automatizados
- [ ] Configurar CI/CD com GitHub Actions
- [ ] Implementar backup automático
- [ ] Monitoramento com Sentry
- [ ] Analytics com Google Analytics

---

## 📞 SUPORTE

**Problemas?** Abrir issue em: https://github.com/Paulinho-Fortunato/PRAZER-BURGUER/issues

---

**Versão**: 2.0  
**Última atualização**: 30/08/2026
