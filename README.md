# API de Eventos Acadêmicos — APS 3 (Persistência e Consolidação de Dados)

API RESTful para gerenciar **eventos**, **participantes** e **inscrições** de uma instituição de ensino.
Evolução da APS 2: os dados deixam de ficar em memória e passam a ser gravados em um banco
**SQLite**, acessado com **SQLAlchemy ORM**. A API também gera **relatórios consolidados**
(ocupação dos eventos, eventos por categoria e participação por curso).

> Equipe: _preencher nomes_ · Repositório: _preencher link do GitHub_

## Tecnologias

- Python 3.10+
- FastAPI (rotas e Swagger/OpenAPI em `/docs`) e Uvicorn
- SQLite + SQLAlchemy 2.x (ORM)
- Pydantic v2 (validação de entrada e formato das respostas)
- Pytest + pytest-cov + httpx (testes)

## Instalação

```bash
git clone <URL_DO_REPOSITORIO>
cd api_eventos

python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

## Execução

```bash
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger UI (documentação e testes manuais): http://127.0.0.1:8000/docs

Na primeira execução o arquivo do banco e as tabelas são criados automaticamente.
Nas execuções seguintes os dados existentes são mantidos.

## Testes

```bash
pytest                 # executa todos os testes
pytest --cov=.         # com relatório de cobertura
```

Os testes usam um banco SQLite **temporário** (um arquivo novo por teste), então nunca alteram o
`eventos.db` real. Eles cobrem os cenários pedidos na atividade, incluindo reinício da aplicação
com verificação da persistência e atualização dos relatórios após inserir, atualizar e excluir registros.

## Estrutura do projeto

```
api_eventos/
├── main.py                        # cria o app, registra rotas e traduz exceções em respostas HTTP
├── database.py                    # conexão SQLite, sessões, criação das tabelas, get_db
├── dependencies.py                # injeção de dependência (sessão -> service)
├── controller/                    # CONTROLLER: rotas e requisições HTTP (sem regra de negócio)
│   ├── evento_controller.py
│   ├── participante_controller.py
│   ├── inscricao_controller.py
│   └── relatorio_controller.py
├── model/                         # MODEL: entidades e relacionamentos (SQLAlchemy)
│   ├── evento.py
│   ├── participante.py
│   └── inscricao.py
├── schema/                        # SCHEMA: validação e formato das respostas (Pydantic)
│   ├── evento_schema.py
│   ├── participante_schema.py
│   ├── inscricao_schema.py
│   └── relatorio_schema.py
├── service/                       # SERVICE: regras de negócio, persistência e consolidação
│   ├── evento_service.py
│   ├── participante_service.py
│   ├── inscricao_service.py
│   ├── relatorio_service.py
│   └── exceptions.py              # exceções de negócio e tradução de erros do banco
├── tests/
├── requirements.txt
└── README.md
```

Fluxo de uma requisição: **Controller → Service → Banco (SQLAlchemy)**. O Controller só recebe a
requisição e delega; o Service aplica as regras, executa as consultas e lança exceções
(`NaoEncontradoError`, `ConflitoError`, `ErroPersistenciaError`) sem conhecer HTTP; o `main.py`
converte essas exceções em **404**, **409** e **500**. O acesso ao banco, que na APS 2 ficava em
uma camada `repository/` em memória, agora é feito diretamente pelos Services com a sessão do
SQLAlchemy, como sugere a organização do enunciado.

## Configuração do banco de dados

- **Arquivo:** `eventos.db`, criado na **raiz do projeto** (ao lado de `main.py`). Está no `.gitignore`
  porque é gerado automaticamente. Para apagar todos os dados, pare a API e remova esse arquivo.
- **Outro local:** defina a variável de ambiente `EVENTOS_DATABASE_URL`, por exemplo
  `EVENTOS_DATABASE_URL=sqlite:///./outro.db uvicorn main:app`.
- **Sessões:** `database.py` define `SessionLocal`. A dependência `get_db` abre **uma sessão por
  requisição** e a **fecha ao final** (bloco `finally`). Ela é entregue às rotas por `Depends` e repassada aos Services.
- **Tabelas:** `criar_tabelas()` roda no início da aplicação (`lifespan`) e cria, a partir dos models,
  apenas as tabelas que ainda não existem, sem apagar dados. Não foi usado Alembic.
- **Chaves estrangeiras:** o SQLite não as valida por padrão; o `PRAGMA foreign_keys=ON` é ativado em toda
  conexão, o que garante a integridade referencial e o `ON DELETE CASCADE`.

### Modelo de dados

| Tabela | Colunas | Restrições |
|---|---|---|
| `eventos` | `id`, `titulo`, `descricao`, `data`, `horario`, `local`, `capacidade`, `categoria` | PK `id`; `CHECK (capacidade > 0)` |
| `participantes` | `id`, `nome`, `email`, `curso` | PK `id`; `email` **UNIQUE** |
| `inscricoes` | `id`, `evento_id`, `participante_id`, `data_inscricao` | PK `id`; FK `evento_id` → `eventos.id`; FK `participante_id` → `participantes.id`; **UNIQUE (`evento_id`, `participante_id`)** |

Relacionamentos (SQLAlchemy): `Evento 1—N Inscricao N—1 Participante` (`Evento.inscricoes`,
`Participante.inscricoes`, `Inscricao.evento`, `Inscricao.participante`). `data_inscricao` é gravada
automaticamente em UTC.

### Integridade dos dados

- **E-mail único:** verificado pelo Service (com mensagem clara) e garantido pelo `UNIQUE` do banco.
  O e-mail é salvo em minúsculas, então `Maria@x.com` e `maria@x.com` são o mesmo e-mail.
- **Inscrição duplicada:** verificada pelo Service e garantida pelo `UNIQUE(evento_id, participante_id)`.
- **Referências válidas:** inscrição só existe para evento e participante existentes (verificação no Service e FK no banco).
- **Exclusão (comportamento definido):** excluir um **evento** ou um **participante** remove também as
  **suas inscrições** (cascade). Não ficam registros órfãos, e o outro lado da relação é preservado
  (excluir um evento não apaga os participantes, e vice-versa). As vagas e os relatórios refletem a mudança.
- **Atualização:** não é possível reduzir a capacidade de um evento para menos que o número de inscritos (409).
- **Falhas do banco:** erros de integridade viram **409** com mensagem amigável; qualquer outra falha de
  persistência desfaz a transação (`rollback`) e responde **500** com mensagem genérica. O erro técnico
  (SQL, caminhos) vai só para o log do servidor, nunca para o cliente.

## Rotas

### Eventos

| Método | Rota | Descrição | Sucesso | Erros |
|---|---|---|---|---|
| POST | `/eventos` | Cadastra evento | 201 | 422 |
| GET | `/eventos` | Lista eventos | 200 | |
| GET | `/eventos/{id}` | Consulta evento | 200 | 404 |
| PUT | `/eventos/{id}` | Atualiza evento | 200 | 404, 409, 422 |
| DELETE | `/eventos/{id}` | Exclui evento e suas inscrições | 204 | 404 |

Campos: `titulo`, `descricao`, `data` (AAAA-MM-DD), `horario` (HH:MM), `local`, `capacidade` (> 0) e
`categoria` (`Palestra`, `Workshop`, `Minicurso`, `Seminário`, `Competição`).

### Participantes

| Método | Rota | Descrição | Sucesso | Erros |
|---|---|---|---|---|
| POST | `/participantes` | Cadastra participante | 201 | 409, 422 |
| GET | `/participantes` | Lista participantes | 200 | |
| GET | `/participantes/{id}` | Consulta participante | 200 | 404 |
| PUT | `/participantes/{id}` | Atualiza participante | 200 | 404, 409, 422 |
| DELETE | `/participantes/{id}` | Exclui participante e suas inscrições | 204 | 404 |

Campos: `nome`, `email` (formato válido e único) e `curso`.

### Inscrições

| Método | Rota | Descrição | Sucesso | Erros |
|---|---|---|---|---|
| POST | `/eventos/{evento_id}/inscricoes/{participante_id}` | Inscreve participante no evento | 201 | 404, 409 |
| GET | `/eventos/{evento_id}/inscricoes` | Lista participantes inscritos (com `data_inscricao`) | 200 | 404 |

Antes de gravar, o Service verifica nesta ordem: (1) o evento existe (404); (2) o participante existe (404);
(3) o participante ainda não está inscrito (409); (4) existem vagas (409). A inscrição é então persistida.

### Relatórios

| Método | Rota | Descrição |
|---|---|---|
| GET | `/relatorios/eventos/ocupacao` | Ocupação de cada evento |
| GET | `/relatorios/eventos/categorias` | Eventos consolidados por categoria |
| GET | `/relatorios/participantes/cursos` | Participação por curso |

## Relatórios e informações consolidadas

Todos os valores são calculados **dinamicamente** por consultas SQLAlchemy (`JOIN`, `GROUP BY`,
`COUNT`, `SUM`) sobre os registros do banco: não há listas ou valores fixos no código. Se não existirem
registros, a resposta é `200` com lista vazia (`[]`).

**Ocupação dos eventos** — para cada evento: `evento_id`, `titulo`, `capacidade`, `total_inscritos`,
`vagas_disponiveis` (capacidade − inscritos) e `percentual_ocupacao` (inscritos ÷ capacidade × 100,
arredondado em 2 casas). Usa `LEFT JOIN`, então eventos **sem inscrições** aparecem com 0 inscritos.
A divisão por zero é evitada com uma guarda no cálculo (e a capacidade é sempre > 0 por validação e `CHECK` no banco).

**Eventos por categoria** — para cada categoria: `total_eventos`, `capacidade_total` e `total_inscricoes`.
As inscrições são contadas por evento em uma subconsulta antes do agrupamento, para que a capacidade de
um evento não seja somada várias vezes quando ele tem muitas inscrições.

**Participação por curso** — para cada curso: `total_participantes` e `total_inscricoes`. Usa
`COUNT(DISTINCT participante.id)`, então um participante com várias inscrições é contado **uma única vez**
em `total_participantes`; participantes sem inscrições também entram na contagem.

## Exemplos de uso

### Cadastrar evento — `POST /eventos`

```json
{
  "titulo": "Introdução à Inteligência Artificial",
  "descricao": "Palestra introdutória",
  "data": "2026-12-05",
  "horario": "19:30",
  "local": "Auditório A",
  "capacidade": 2,
  "categoria": "Palestra"
}
```

Resposta `201 Created`:

```json
{
  "titulo": "Introdução à Inteligência Artificial",
  "descricao": "Palestra introdutória",
  "data": "2026-12-05",
  "horario": "19:30:00",
  "local": "Auditório A",
  "capacidade": 2,
  "categoria": "Palestra",
  "id": 1
}
```

### Cadastrar participante — `POST /participantes`

```json
{ "nome": "Maria Silva", "email": "maria@email.com", "curso": "Engenharia de Software" }
```

Resposta `201 Created`:

```json
{ "nome": "Maria Silva", "email": "maria@email.com", "curso": "Engenharia de Software", "id": 1 }
```

### Inscrever participante — `POST /eventos/1/inscricoes/1`

Resposta `201 Created`:

```json
{ "id": 1, "evento_id": 1, "participante_id": 1, "data_inscricao": "2026-11-24T01:20:12.825423" }
```

### Listar inscritos — `GET /eventos/1/inscricoes`

```json
[
  {
    "nome": "Maria Silva",
    "email": "maria@email.com",
    "curso": "Engenharia de Software",
    "id": 1,
    "data_inscricao": "2026-11-24T01:20:12.825423"
  }
]
```

### Erros

| Situação | Status | Corpo |
|---|---|---|
| Evento inexistente | 404 | `{"detail": "Evento não encontrado."}` |
| Participante inexistente | 404 | `{"detail": "Participante não encontrado."}` |
| Participante já inscrito | 409 | `{"detail": "Participante já está inscrito neste evento."}` |
| Evento sem vagas | 409 | `{"detail": "Não existem vagas disponíveis para este evento."}` |
| E-mail já cadastrado | 409 | `{"detail": "Já existe um participante cadastrado com este e-mail."}` |
| Capacidade menor que os inscritos (PUT) | 409 | `{"detail": "A nova capacidade não pode ser menor que o número de inscritos."}` |
| Falha de persistência | 500 | `{"detail": "Erro interno ao acessar o banco de dados. Tente novamente mais tarde."}` |

Dados inválidos (ex.: `capacidade: 0`) retornam `422 Unprocessable Entity` com o campo (`loc`), a mensagem (`msg`) e o tipo do erro:

```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "capacidade"],
      "msg": "Input should be greater than 0",
      "input": 0,
      "ctx": { "gt": 0 }
    }
  ]
}
```

### Relatório de ocupação — `GET /relatorios/eventos/ocupacao`

Evidência real, com 3 eventos e 3 inscrições (um evento lotado, outro lotado e um sem inscritos):

```json
[
  { "evento_id": 1, "titulo": "Introdução à Inteligência Artificial", "capacidade": 2,
    "total_inscritos": 2, "vagas_disponiveis": 0, "percentual_ocupacao": 100.0 },
  { "evento_id": 2, "titulo": "Workshop de Python", "capacidade": 1,
    "total_inscritos": 1, "vagas_disponiveis": 0, "percentual_ocupacao": 100.0 },
  { "evento_id": 3, "titulo": "Seminário vazio", "capacidade": 30,
    "total_inscritos": 0, "vagas_disponiveis": 30, "percentual_ocupacao": 0.0 }
]
```

### Relatório por categoria — `GET /relatorios/eventos/categorias`

```json
[
  { "categoria": "Palestra",  "total_eventos": 1, "capacidade_total": 2,  "total_inscricoes": 2 },
  { "categoria": "Seminário", "total_eventos": 1, "capacidade_total": 30, "total_inscricoes": 0 },
  { "categoria": "Workshop",  "total_eventos": 1, "capacidade_total": 1,  "total_inscricoes": 1 }
]
```

### Relatório por curso — `GET /relatorios/participantes/cursos`

```json
[
  { "curso": "Análise e Desenvolvimento de Sistemas", "total_participantes": 1, "total_inscricoes": 1 },
  { "curso": "Engenharia de Software", "total_participantes": 2, "total_inscricoes": 2 }
]
```

### Relatórios após excluir um registro

Após `DELETE /participantes/1` (uma participante de Engenharia de Software com 2 inscrições), as inscrições
dela somem e os relatórios mudam sozinhos:

- ocupação: o evento 1 passa de 2 inscritos (100%) para 1 inscrito (50.0%); o evento 2 passa para 0 inscritos;
- cursos: Engenharia de Software passa de 2 participantes e 2 inscrições para 1 participante e 0 inscrições.

### Exemplo com curl

```bash
curl -X POST http://127.0.0.1:8000/eventos \
  -H "Content-Type: application/json" \
  -d '{"titulo":"Workshop de Python","descricao":"Hands-on","data":"2026-12-10","horario":"14:00","local":"Lab 3","capacidade":30,"categoria":"Workshop"}'

curl http://127.0.0.1:8000/relatorios/eventos/ocupacao
```

## Roteiro para demonstrar os cenários no Swagger (`/docs`)

1. `POST /eventos` e `GET /eventos/{id}`: cadastro e consulta de eventos no banco.
2. `POST /participantes` e `GET /participantes/{id}`: cadastro e consulta de participantes.
3. `PUT` e `DELETE` em eventos e participantes: atualização e exclusão.
4. `POST /eventos/{evento_id}/inscricoes/{participante_id}`: inscrição (201).
5. Repetir a mesma inscrição: 409, já inscrito.
6. Inscrever em um `evento_id` que não existe: 404.
7. Inscrever em evento já lotado: 409, sem vagas.
8. **Reinício:** parar o servidor (`Ctrl+C`), subir de novo com `uvicorn main:app` e consultar `GET /eventos`, `GET /participantes` e `GET /eventos/{id}/inscricoes`: os dados continuam lá.
9. `GET /relatorios/eventos/ocupacao`.
10. `GET /relatorios/eventos/categorias`.
11. `GET /relatorios/participantes/cursos`.
12. Inserir, atualizar ou excluir registros e consultar os três relatórios de novo: os números acompanham as mudanças.
