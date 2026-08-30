# 🚀 GUIA DE DEPLOYMENT - PRAZER BURGUER

**Status**: Production Ready  
**Data**: 30/08/2026

---

## 📋 Checklist Pré-Deployment

```
✅ SEGURANÇA
- [ ] SECRET_KEY gerada e segura (32+ caracteres)
- [ ] FLASK_DEBUG = false
- [ ] Senha admin alterada (mínimo 12 caracteres)
- [ ] .env NÃO está commitado
- [ ] HTTPS/SSL configurado
- [ ] CORS headers corretos
- [ ] Rate limiting ativo
- [ ] Logging de auditoria ativo

✅ BANCO DE DADOS
- [ ] MongoDB Atlas configurado
- [ ] Backup automático habilitado
- [ ] Índices criados
- [ ] Dados de teste removidos

✅ APLICAÇÃO
- [ ] Testes passando
- [ ] Sem erros de importação
- [ ] Templates renderizando
- [ ] Static files servindo

✅ DEPLOYMENT
- [ ] Domínio configurado
- [ ] Email transacional testado
- [ ] WhatsApp API funcionando
- [ ] Monitoramento configurado
```

---

## 1️⃣ DEPLOYMENT NO VERCEL

### 1.1 Preparação

```bash
# Instalar Vercel CLI
npm i -g vercel

# Login
vercel login
```

### 1.2 Criar vercel.json

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
  },
  "rewrites": [
    { "source": "/(.*)", "destination": "/app.py" }
  ]
}
```

### 1.3 Deploy

```bash
# Deploy de preview
vercel

# Deploy para produção
vercel --prod
```

### 1.4 Configurar Variáveis de Ambiente

1. Ir para Project Settings
2. Environment Variables
3. Adicionar:

```
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=sua-chave-secreta
MONGODB_URI=mongodb+srv://...
MONGODB_DB_NAME=prazer_burguer
ADMIN_EMAIL=seu-email@domain.com
```

---

## 2️⃣ DEPLOYMENT NO HEROKU

### 2.1 Preparação

```bash
# Instalar Heroku CLI
brew install heroku  # macOS
# ou
choco install heroku-cli  # Windows

# Login
heroku login
```

### 2.2 Criar app

```bash
# Criar novo app
heroku create prazer-burguer

# Verificar remote
git remote -v
```

### 2.3 Criar Procfile

```
web: gunicorn -w 4 -b 0.0.0.0:$PORT app:app
```

### 2.4 Deploy

```bash
# Push para Heroku
git push heroku main

# Ver logs
heroku logs --tail
```

### 2.5 Configurar Variáveis

```bash
# Via CLI
heroku config:set FLASK_ENV=production
heroku config:set FLASK_DEBUG=false
heroku config:set SECRET_KEY=sua-chave
heroku config:set MONGODB_URI=mongodb+srv://...

# Ou via dashboard
# Settings → Config Vars
```

---

## 3️⃣ DEPLOYMENT NO RAILWAY.APP

### 3.1 Preparação

1. Ir para https://railway.app
2. Login com GitHub
3. Selecionar repositório

### 3.2 Configurar

1. New Project → Deploy from GitHub
2. Selecionar `PRAZER-BURGUER`
3. Permitir instalação

### 3.3 Variáveis de Ambiente

1. Settings → Environment
2. Adicionar:

```
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=sua-chave
MONGODB_URI=mongodb+srv://...
PORT=5000
```

### 3.4 Deploy Automático

- Railway detecta `requirements.txt`
- Build automático ao fazer push
- Redeploy automático

---

## 4️⃣ DEPLOYMENT EM VPS (AWS EC2, DigitalOcean, etc)

### 4.1 Preparação do Servidor

```bash
# Update sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python 3.8+
sudo apt install python3-pip python3-venv -y

# Instalar MongoDB CLI
sudo apt install mongodb-clients -y

# Instalar Nginx
sudo apt install nginx -y

# Instalar Certbot (SSL)
sudo apt install certbot python3-certbot-nginx -y
```

### 4.2 Clonar Repositório

```bash
# Criar diretório
sudo mkdir -p /var/www/prazer-burguer
cd /var/www/prazer-burguer

# Clonar
sudo git clone https://github.com/Paulinho-Fortunato/PRAZER-BURGUER.git .

# Mudar permissões
sudo chown -R $USER:$USER /var/www/prazer-burguer
```

### 4.3 Ambiente Python

```bash
# Criar venv
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Gerar .env
cp .env.example .env
# Editar .env com valores reais
```

### 4.4 Configurar Gunicorn

**Criar `/etc/systemd/system/prazer-burguer.service`:**

```ini
[Unit]
Description=PRAZER BURGUER Flask App
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/prazer-burguer
ExecStart=/var/www/prazer-burguer/venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 app:app
Restart=always
Environment="FLASK_ENV=production"

[Install]
WantedBy=multi-user.target
```

```bash
# Ativar serviço
sudo systemctl daemon-reload
sudo systemctl enable prazer-burguer
sudo systemctl start prazer-burguer
```

### 4.5 Configurar Nginx

**Criar `/etc/nginx/sites-available/prazer-burguer`:**

```nginx
server {
    listen 80;
    server_name prazer-burguer.com www.prazer-burguer.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Ativar site
sudo ln -s /etc/nginx/sites-available/prazer-burguer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4.6 Configurar SSL (Let's Encrypt)

```bash
# Gerar certificado
sudo certbot --nginx -d prazer-burguer.com -d www.prazer-burguer.com

# Auto-renew
sudo certbot renew --dry-run
```

---

## 5️⃣ CONFIGURAR CI/CD (GitHub Actions)

**Criar `.github/workflows/deploy.yml`:**

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Vercel
        run: |
          npm i -g vercel
          vercel --prod --token ${{ secrets.VERCEL_TOKEN }}
```

---

## 6️⃣ MONITORAMENTO

### 6.1 Sentry (Error Tracking)

```bash
# Instalar
pip install sentry-sdk
```

**Em app.py:**

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

if os.environ.get('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1
    )
```

### 6.2 Uptime Monitoring

1. Ir para https://uptimerobot.com
2. Criar novo monitor
3. URL: https://seu-dominio.com
4. Intervalo: 5 minutos
5. Alertas por email

### 6.3 Logs

```bash
# Heroku
heroku logs --tail

# VPS
sudo tail -f /var/log/syslog
sudo journalctl -u prazer-burguer -f
```

---

## 7️⃣ BACKUP E RECUPERAÇÃO

### 7.1 Backup MongoDB Atlas

1. Dashboard → Cluster → Backup
2. Ativar Continuous Backup
3. Retenção: 30 dias

### 7.2 Backup Manual

```bash
# Exportar dados
mongodump --uri="mongodb+srv://user:pass@cluster0.mongodb.net/prazer_burguer" --out=./backup

# Restaurar
mongorestore --uri="mongodb+srv://user:pass@cluster0.mongodb.net/prazer_burguer" ./backup
```

---

## 8️⃣ CHECKLIST PÓS-DEPLOYMENT

```
- [ ] Site acessível via domínio
- [ ] HTTPS funcionando
- [ ] Admin dashboard acessível
- [ ] Produtos visíveis
- [ ] WhatsApp links funcionando
- [ ] Emails transacionais enviando
- [ ] Logs sendo registrados
- [ ] Monitoramento ativo
- [ ] Backups configurados
```

---

**Dúvidas?** Abrir issue: https://github.com/Paulinho-Fortunato/PRAZER-BURGUER/issues
