from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Participante(Base):
    """Tabela `participantes`."""

    __tablename__ = "participantes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(200))
    # E-mail único (guardado em minúsculas pelo schema, o que torna a unicidade
    # insensível a maiúsculas/minúsculas).
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    curso: Mapped[str] = mapped_column(String(200), index=True)

    # Excluir um participante exclui suas inscrições (sem registros órfãos).
    inscricoes: Mapped[list["Inscricao"]] = relationship(  # noqa: F821
        back_populates="participante", cascade="all, delete-orphan", passive_deletes=True
    )
