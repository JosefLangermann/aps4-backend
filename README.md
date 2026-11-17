# Central de Eventos Acadêmicos — API

API REST feita em **FastAPI** para organizar a agenda de eventos de uma instituição de ensino: palestras,
workshops, minicursos, seminários e competições. Além do cadastro dos eventos, o sistema controla os
participantes, as inscrições e gera relatórios consolidados.

> **APS 4:** esta versão adiciona **autenticação e segurança** sobre a API da APS 3: cadastro de usuários,
> senhas guardadas com **hash Argon2**, login por e-mail e senha com **token JWT**, rotas protegidas e
> **controle de acesso por perfil** (`administrador` e `usuario`). Persistência (SQLite + SQLAlchemy), relatórios e
> regras de negócio das etapas anteriores continuam funcionando.

## Tecnologias

- Python 3.10+
- FastAPI, Pydantic, Uvicorn
- SQLite + SQLAlchemy ORM (2.x)
- **pwdlib (Argon2id)** — hash e verificação de senhas
- **PyJWT** — geração e validação dos tokens JWT (HS256)
- python-dotenv — leitura do arquivo `.env`
- Pytest + HTTPX — testes automatizados

## Instalação e execução

```bash
# 1. (opcional) crie e ative um ambiente virtual
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac

# 2. Instale as dependências
python -m pip install -r requirements.txt

# 3. Crie o arquivo .env (gera uma chave secreta aleatória e define o administrador inicial)
python gerar_env.py

# 4. Suba o servidor
python -m uvicorn main:app --reload
```

A API sobe em `http://127.0.0.1:8000` e o Swagger fica em `http://127.0.0.1:8000/docs`.

## Configuração da chave secreta (JWT) e do administrador

Nenhum segredo fica no código nem no repositório. Tudo vem de variáveis de ambiente, lidas do arquivo **`.env`**
(que está no `.gitignore`). O arquivo **`.env.example`** é o modelo, sem segredos reais.

| Variável | Para que serve | Padrão |
|---|---|---|
| `JWT_SECRET_KEY` | Chave que assina e valida os tokens JWT | *(veja abaixo)* |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token, em minutos | `30` |
| `ADMIN_NOME` | Nome do administrador inicial | `Administrador` |
| `ADMIN_EMAIL` | E-mail do administrador inicial | *(vazio = não cria)* |
| `ADMIN_SENHA` | Senha do administrador inicial | *(vazio = não cria)* |

**Como configurar a chave:** o jeito mais simples é rodar `python gerar_env.py`, que cria o `.env` com uma chave
aleatória nova. Para gerar uma manualmente:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

e colar o resultado em `JWT_SECRET_KEY=` dentro do `.env`. Também funciona definir direto no ambiente
(`set JWT_SECRET_KEY=...` no Windows, `export JWT_SECRET_KEY=...` no Linux/Mac).

> Se `JWT_SECRET_KEY` não estiver definida, a API sobe com uma **chave aleatória temporária** e avisa no terminal.
> É seguro, mas os tokens deixam de valer a cada reinicialização. Em uso normal, sempre defina a chave.

**Administrador inicial:** ao subir, se `ADMIN_EMAIL` e `ADMIN_SENHA` estiverem definidos e esse e-mail ainda não
existir, a API cria esse usuário com perfil `administrador`. É a única forma de nascer um administrador sem
outro administrador. O cadastro público (`POST /usuarios`) **sempre** cria o perfil `usuario`, e recusa (422)
qualquer tentativa de enviar `"perfil"` no corpo. Depois, um administrador pode promover outros usuários em
`PATCH /usuarios/{id}/perfil`. Os valores do `.env.example` (`admin@exemplo.com` / `Admin@12345`) são só para
uso local: troque a senha em qualquer outro ambiente.

## Organização do código

O projeto mantém o padrão **MVC** das etapas anteriores, com a camada `security` nova:

```
.
├── main.py                 → cria o app, registra as rotas, cria o admin inicial e trata erros de banco
├── gerar_env.py            → cria o .env com uma chave JWT aleatória
├── requirements.txt
├── .env.example            → modelo das variáveis de ambiente (sem segredos reais)
├── eventos.db              → banco SQLite (criado automaticamente na 1ª execução)
├── tests/                  → testes automatizados
└── app/
    ├── config.py           → lê as variáveis de ambiente (chave JWT, validade, admin inicial)
    ├── database.py         → conexão com o SQLite, sessões e criação das tabelas
    ├── models/             → tabelas e relacionamentos (SQLAlchemy)
    │   ├── evento.py  participante.py  inscricao.py
    │   └── usuario.py      → tabela de usuários (senha_hash, perfil)
    ├── schemas/            → validação de entrada e formato das respostas (Pydantic)
    │   ├── evento.py  participante.py  inscricao.py  relatorio.py
    │   ├── usuario.py      → cadastro (sem perfil) e saída (sem senha/hash)
    │   └── auth.py         → login e token
    ├── security/           → segurança
    │   ├── security.py     → hash de senha (Argon2) e criação/validação do JWT
    │   └── dependencias.py → dependências do FastAPI: usuário autenticado e checagem de perfil
    ├── routers/            → recebe as requisições HTTP (Controller)
    │   ├── eventos.py  participantes.py  inscricoes.py  relatorios.py
    │   ├── usuarios.py     → cadastro de usuários e gestão de perfis
    │   └── auth.py         → login e /auth/me
    └── regras/             → regras de negócio e consultas (Service)
        ├── eventos.py  participantes.py  inscricoes.py  relatorios.py
        ├── usuarios.py     → cadastro, admin inicial, alteração de perfil
        └── auth.py         → verificação de credenciais e emissão do token
```

Correspondência com o MVC pedido: `routers/` = **Controller**, `regras/` = **Service**, `models/` = **Model**,
`schemas/` = **Schema**, `security/` = **Security**, `database.py` = **Database**. A lógica de autenticação e
autorização não fica nas rotas: elas só declaram `Depends(...)` e a verificação acontece em `security/dependencias.py`.

## Como cadastrar usuários e obter um token

**1. Cadastrar** (`POST /usuarios`, público):

```json
{ "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "senha": "senha_segura" }
```

Resposta (`201`) — sem senha e sem hash:

```json
{ "id": 2, "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "perfil": "usuario" }
```

Regras da senha: de 8 a 128 caracteres e não pode ser só espaços. O e-mail precisa ser válido e único.

**2. Fazer login** (`POST /auth/login`, público):

```json
{ "email": "aluno@exemplo.com", "senha": "senha_segura" }
```

Resposta (`200`):

```json
{ "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer" }
```

**3. Usar o token** nas rotas protegidas, no cabeçalho `Authorization`:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

No **Swagger** (`/docs`): execute `POST /auth/login`, copie o `access_token`, clique em **Authorize** (cadeado, no
topo), cole o token e confirme. Todas as requisições seguintes já vão autenticadas.

Com `curl`:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"aluno@exemplo.com","senha":"senha_segura"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/auth/me
```

## Perfis e permissões

| Perfil | Pode |
|---|---|
| **usuario** | consultar eventos; consultar participantes; cadastrar participantes; **realizar inscrições**; consultar os próprios dados (`/auth/me`) |
| **administrador** | tudo que o usuário faz, mais: **cadastrar, atualizar e excluir eventos**; atualizar e excluir participantes; consultar as inscrições de um evento; **consultar os relatórios**; listar usuários e alterar perfis |

A autorização é feita **no servidor**: o perfil é lido do banco a cada requisição, nunca do token nem de algo
enviado pelo cliente. Por isso, promover ou rebaixar um usuário vale imediatamente, mesmo com o token antigo.

## Rotas: públicas e protegidas

**Públicas** (não exigem token): `GET /`, `POST /usuarios`, `POST /auth/login` e a documentação (`/docs`).
**Todas as demais exigem token.**

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| POST | `/usuarios` | pública | cadastra usuário (perfil sempre `usuario`) |
| POST | `/auth/login` | pública | autentica e devolve o JWT |
| GET | `/auth/me` | autenticado | dados do usuário dono do token |
| GET | `/usuarios` | administrador | lista os usuários |
| PATCH | `/usuarios/{id}/perfil` | administrador | altera o perfil de um usuário |
| POST | `/eventos` | administrador | cria um evento |
| GET | `/eventos` · `/eventos/{id}` | autenticado | lista / busca eventos |
| PUT | `/eventos/{id}` | administrador | atualiza um evento |
| DELETE | `/eventos/{id}` | administrador | remove um evento (e suas inscrições) |
| POST | `/participantes` | autenticado | cria um participante |
| GET | `/participantes` · `/participantes/{id}` | autenticado | lista / busca participantes |
| PUT | `/participantes/{id}` | administrador | atualiza um participante |
| DELETE | `/participantes/{id}` | administrador | remove um participante (e suas inscrições) |
| POST | `/eventos/{evento_id}/inscricoes/{participante_id}` | autenticado | inscreve um participante em um evento |
| GET | `/eventos/{evento_id}/inscricoes` | administrador | lista quem está inscrito em um evento |
| GET | `/relatorios/eventos/ocupacao` | administrador | ocupação de cada evento |
| GET | `/relatorios/eventos/categorias` | administrador | consolidado por categoria |
| GET | `/relatorios/participantes/cursos` | administrador | consolidado por curso |

## Como a segurança funciona

- **Senhas:** guardadas só como hash **Argon2id** (biblioteca `pwdlib`), com salt aleatório (a mesma senha gera hashes
  diferentes). A verificação usa a função da própria biblioteca. Nenhum algoritmo foi implementado à mão e não há MD5/SHA-1.
- **Respostas:** nenhum schema de saída tem campo de senha ou hash.
- **Login:** e-mail inexistente e senha errada retornam o **mesmo** `401` e a mesma mensagem, e a verificação do hash
  roda nos dois casos (para o tempo de resposta também não entregar qual falhou). O e-mail não diferencia maiúsculas.
- **JWT:** algoritmo `HS256`, assinado com `JWT_SECRET_KEY`. Claims: `sub` (id do usuário), `iat` (emissão) e `exp`
  (expiração, 30 min por padrão). O token **não** carrega senha nem perfil. Na validação, a assinatura e a expiração são
  verificadas, a lista de algoritmos aceitos é fixa (recusa `alg: none`) e o usuário do `sub` precisa existir no banco.
  Token ausente, inválido, adulterado ou expirado → `401`.
- **Dependências do FastAPI:** `obter_usuario_atual` (autenticação) e `exigir_administrador` (autorização) ficam em
  `app/security/dependencias.py` e são aplicadas nas rotas via `Depends`, sem repetir lógica em cada uma.
  A autenticação é checada **antes** da validação do corpo da requisição.
- **Erros de banco:** continuam retornando uma mensagem genérica (`500`), sem detalhes técnicos.

## Erros tratados

| Situação | Status | Resposta |
|---|---|---|
| Credenciais inválidas no login | 401 | `{"detail": "E-mail ou senha inválidos."}` |
| Token ausente, inválido, adulterado ou expirado | 401 | `{"detail": "Não foi possível validar as credenciais."}` |
| Autenticado, mas sem permissão | 403 | `{"detail": "Você não possui permissão para executar esta operação."}` |
| E-mail de usuário já cadastrado | 409 | `{"detail": "Já existe um usuário cadastrado com este e-mail."}` |
| Alterar o próprio perfil (admin) | 409 | `{"detail": "Você não pode alterar o seu próprio perfil."}` |
| Evento não existe | 404 | `{"detail": "Evento não encontrado."}` |
| Participante não existe | 404 | `{"detail": "Participante não encontrado."}` |
| Usuário não existe (alterar perfil) | 404 | `{"detail": "Usuário não encontrado."}` |
| Participante já inscrito | 409 | `{"detail": "Participante já está inscrito neste evento."}` |
| Evento sem vaga | 409 | `{"detail": "Não existem vagas disponíveis para este evento."}` |
| E-mail de participante já cadastrado | 409 | `{"detail": "Já existe um participante cadastrado com este e-mail."}` |
| Capacidade menor que o nº de inscritos | 409 | `{"detail": "A capacidade não pode ser menor que o número de inscritos no evento."}` |
| Dado inválido (e-mail, senha curta, capacidade ≤ 0, campo vazio, `perfil` no cadastro...) | 422 | detalhamento automático do Pydantic |
| Falha inesperada do banco | 500 | `{"detail": "Erro ao processar a operação no banco de dados."}` |

## Banco de dados

- **SQLite**, arquivo `eventos.db` na **raiz do projeto**, criado sozinho na primeira execução. Os dados continuam lá
  depois de reiniciar. Para zerar tudo, pare a API e apague o arquivo (o administrador inicial é recriado ao subir).
- `app/database.py` configura o `engine`, a `SessionLocal` e `obter_sessao()` (uma sessão por requisição, fechada no final).
- Tabelas: `eventos`, `participantes`, `inscricoes` e **`usuarios`** (`id`, `nome`, `email` único, `senha_hash`, `perfil`
  com `CHECK` limitando a `administrador`/`usuario`). Criadas por `Base.metadata.create_all`, sem Alembic.
- Integridade da APS 3 mantida: `UNIQUE(evento_id, participante_id)`, e-mail de participante único, `CHECK (capacidade > 0)`
  e exclusão em cascata das inscrições (sem registros órfãos). Os **participantes** (quem se inscreve) e os **usuários**
  (quem acessa a API) são cadastros separados.

## Relatórios (resumo)

Calculados na hora, com consultas do SQLAlchemy (`JOIN`, `GROUP BY`, `COUNT`, `SUM`), e restritos a administradores:

- `GET /relatorios/eventos/ocupacao` — por evento: capacidade, inscritos, vagas e percentual (inclui eventos sem inscrições; sem divisão por zero).
- `GET /relatorios/eventos/categorias` — por categoria: total de eventos, capacidade total e total de inscrições.
- `GET /relatorios/participantes/cursos` — por curso: participantes (`COUNT DISTINCT`) e total de inscrições.

Sem registros, a resposta é uma lista vazia `[]`.

## Exemplos

Evento criado por um **administrador** (`POST /eventos`, com `Authorization: Bearer <token do admin>`):

```json
{
  "titulo": "Semana de Tecnologia", "descricao": "Palestras sobre Inteligência Artificial",
  "data": "2026-10-15", "horario": "14:00:00", "local": "Auditório Central",
  "capacidade": 2, "categoria": "Palestra"
}
```

O mesmo pedido feito por um **usuário comum** retorna `403`:

```json
{ "detail": "Você não possui permissão para executar esta operação." }
```

Sem o cabeçalho `Authorization` (ou com token inválido/expirado) retorna `401`:

```json
{ "detail": "Não foi possível validar as credenciais." }
```

`GET /auth/me` com o token de um usuário comum:

```json
{ "id": 2, "nome": "Aluno Exemplo", "email": "aluno@exemplo.com", "perfil": "usuario" }
```

Inscrição feita por um usuário comum (`POST /eventos/1/inscricoes/1`, resposta `201`):

```json
{ "id": 1, "evento_id": 1, "participante_id": 1, "data_inscricao": "2026-11-17T19:53:44.675658" }
```

Relatório de ocupação, consultado por um administrador (`GET /relatorios/eventos/ocupacao`):

```json
[ { "evento_id": 1, "titulo": "Semana de Tecnologia", "capacidade": 2, "total_inscritos": 1,
    "vagas_disponiveis": 1, "percentual_ocupacao": 50.0 } ]
```

## Testes

### Automatizados

```bash
python -m pytest -v
```

Usam um banco temporário, uma chave JWT e um administrador de teste (não mexem no `eventos.db` nem no `.env`).
São **35 testes**: os da APS 3 (CRUD, inscrições, relatórios, integridade), executados agora como administrador, mais os
da APS 4:

- cadastro de usuário, resposta sem senha/hash e senha guardada como hash Argon2 (conferido direto no SQLite);
- e-mail duplicado, validações do cadastro e bloqueio de `"perfil": "administrador"` no corpo;
- login válido (conteúdo e validade do JWT), login inválido sem revelar o motivo;
- **todas** as rotas protegidas sem token → 401;
- tokens inválidos, adulterados, expirados, assinados com outra chave, sem `exp`, `alg: none` e de usuário inexistente → 401;
- usuário comum nas operações de administrador → 403; administrador nas mesmas operações → sucesso;
- `/auth/me` (ignora qualquer id enviado pelo cliente), perfil checado no servidor e gestão de perfis.

### Manuais, pelo Swagger (`/docs`)

Antes: `python gerar_env.py` e subir a API. O administrador é o definido no `.env`
(`admin@exemplo.com` / `Admin@12345` por padrão).

1. `POST /usuarios` com `aluno@exemplo.com` → **201**, sem senha nem hash na resposta.
2. Confira o hash no banco: `python -c "import sqlite3; print(sqlite3.connect('eventos.db').execute('select email, senha_hash from usuarios').fetchall())"` → começa com `$argon2id$`.
3. Repita o `POST /usuarios` com o mesmo e-mail → **409**.
4. `POST /auth/login` com a senha correta → **200** com `access_token`.
5. `POST /auth/login` com senha errada (e depois com e-mail inexistente) → **401**, mesma mensagem.
6. Sem clicar em Authorize, chame `GET /eventos` → **401**.
7. Clique em **Authorize**, cole o token do aluno e chame `GET /eventos` → **200**.
8. Clique em Authorize e cole um texto qualquer como token → **401**. Para testar a expiração, ponha
   `ACCESS_TOKEN_EXPIRE_MINUTES=1` no `.env`, reinicie, faça login, espere 1 minuto e use o token → **401**.
9. Com o token do **aluno**, `POST /eventos` → **403**.
10. Faça login como **administrador**, use o token dele e `POST /eventos` → **201**.
11. `GET /auth/me` (com cada token) → dados do próprio usuário.
12. Como aluno: `POST /participantes`, `POST /eventos/{id}/inscricoes/{participante_id}` → **201**, e
    `GET /relatorios/eventos/ocupacao` → **403**. Como administrador, os três relatórios → **200**, refletindo
    a inscrição feita. Excluir/atualizar registros e consultar de novo mostra os números acompanhando o banco.
