"""Consolidação de dados: todos os valores são calculados dinamicamente pelo banco
(consultas SQLAlchemy com join, group by, count e sum), sem listas fixas."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from model.evento import Evento
from model.inscricao import Inscricao
from model.participante import Participante


class RelatorioService:
    def __init__(self, db: Session):
        self.db = db

    def ocupacao_eventos(self) -> list[dict]:
        """Capacidade, inscritos, vagas restantes e % de ocupação de cada evento.

        LEFT JOIN: eventos sem inscrições aparecem com 0 inscritos.
        """
        consulta = (
            select(
                Evento.id,
                Evento.titulo,
                Evento.capacidade,
                func.count(Inscricao.id).label("total_inscritos"),
            )
            .outerjoin(Inscricao, Inscricao.evento_id == Evento.id)
            .group_by(Evento.id)
            .order_by(Evento.id)
        )
        resultado = []
        for linha in self.db.execute(consulta):
            # capacidade > 0 é garantida (schema + CHECK no banco), mas a guarda
            # evita divisão por zero caso um dado inválido chegue ao banco.
            percentual = (
                round(linha.total_inscritos / linha.capacidade * 100, 2)
                if linha.capacidade > 0
                else 0.0
            )
            resultado.append(
                {
                    "evento_id": linha.id,
                    "titulo": linha.titulo,
                    "capacidade": linha.capacidade,
                    "total_inscritos": linha.total_inscritos,
                    "vagas_disponiveis": max(linha.capacidade - linha.total_inscritos, 0),
                    "percentual_ocupacao": percentual,
                }
            )
        return resultado

    def eventos_por_categoria(self) -> list[dict]:
        """Eventos, capacidade e inscrições agrupados por categoria.

        As inscrições são contadas por evento em uma subconsulta antes de agrupar
        por categoria; assim a capacidade de um evento não é somada várias vezes
        (o que ocorreria ao juntar direto com as inscrições).
        """
        inscricoes_por_evento = (
            select(Inscricao.evento_id, func.count(Inscricao.id).label("qtd"))
            .group_by(Inscricao.evento_id)
            .subquery()
        )
        consulta = (
            select(
                Evento.categoria,
                func.count(Evento.id).label("total_eventos"),
                func.sum(Evento.capacidade).label("capacidade_total"),
                func.coalesce(func.sum(inscricoes_por_evento.c.qtd), 0).label("total_inscricoes"),
            )
            .outerjoin(inscricoes_por_evento, inscricoes_por_evento.c.evento_id == Evento.id)
            .group_by(Evento.categoria)
            .order_by(Evento.categoria)
        )
        return [
            {
                "categoria": linha.categoria,
                "total_eventos": linha.total_eventos,
                "capacidade_total": linha.capacidade_total,
                "total_inscricoes": linha.total_inscricoes,
            }
            for linha in self.db.execute(consulta)
        ]

    def participacao_por_curso(self) -> list[dict]:
        """Participantes cadastrados e inscrições realizadas, por curso.

        COUNT(DISTINCT participante) evita contar o mesmo participante várias
        vezes quando ele possui diversas inscrições.
        """
        consulta = (
            select(
                Participante.curso,
                func.count(func.distinct(Participante.id)).label("total_participantes"),
                func.count(Inscricao.id).label("total_inscricoes"),
            )
            .outerjoin(Inscricao, Inscricao.participante_id == Participante.id)
            .group_by(Participante.curso)
            .order_by(Participante.curso)
        )
        return [
            {
                "curso": linha.curso,
                "total_participantes": linha.total_participantes,
                "total_inscricoes": linha.total_inscricoes,
            }
            for linha in self.db.execute(consulta)
        ]
