from datetime import date, time

from sqlalchemy import CheckConstraint, Date, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Evento(Base):
    """Tabela `eventos`."""

    __tablename__ = "eventos"
    __table_args__ = (CheckConstraint("capacidade > 0", name="ck_eventos_capacidade_positiva"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str] = mapped_column(Text)
    data: Mapped[date] = mapped_column(Date)
    horario: Mapped[time] = mapped_column(Time)
    local: Mapped[str] = mapped_column(String(200))
    capacidade: Mapped[int]
    categoria: Mapped[str] = mapped_column(String(50), index=True)

    # Excluir um evento exclui suas inscrições (sem registros órfãos).
    inscricoes: Mapped[list["Inscricao"]] = relationship(  # noqa: F821
        back_populates="evento", cascade="all, delete-orphan", passive_deletes=True
    )
