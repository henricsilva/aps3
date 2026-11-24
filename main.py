from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from controller import (
    evento_controller,
    inscricao_controller,
    participante_controller,
    relatorio_controller,
)
from database import criar_tabelas
from service.exceptions import (
    ConflitoError,
    ErroPersistenciaError,
    NaoEncontradoError,
    logger,
)

MENSAGEM_ERRO_INTERNO = ErroPersistenciaError.mensagem


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ao iniciar, cria as tabelas que ainda não existem (os dados existentes são mantidos).
    criar_tabelas()
    yield


app = FastAPI(
    title="API de Eventos Acadêmicos",
    description="Eventos, participantes, inscrições e relatórios, com persistência em SQLite.",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(evento_controller.router)
app.include_router(participante_controller.router)
app.include_router(inscricao_controller.router)
app.include_router(relatorio_controller.router)


# O Service lança exceções (sem conhecer HTTP). Aqui elas viram status HTTP.
@app.exception_handler(NaoEncontradoError)
async def tratar_nao_encontrado(request: Request, erro: NaoEncontradoError):
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": erro.mensagem})


@app.exception_handler(ConflitoError)
async def tratar_conflito(request: Request, erro: ConflitoError):
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": erro.mensagem})


@app.exception_handler(ErroPersistenciaError)
async def tratar_erro_persistencia(request: Request, erro: ErroPersistenciaError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": MENSAGEM_ERRO_INTERNO},
    )


@app.exception_handler(SQLAlchemyError)
async def tratar_erro_sqlalchemy(request: Request, erro: SQLAlchemyError):
    # Rede de segurança (ex.: falha em uma consulta de leitura): o detalhe técnico
    # fica só no log do servidor e nunca é enviado ao cliente.
    logger.error("Erro de banco de dados em %s: %s", request.url.path, erro)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": MENSAGEM_ERRO_INTERNO},
    )


@app.get("/", tags=["Status"], summary="Verifica se a API está no ar")
def raiz():
    return {"status": "online", "docs": "/docs"}
