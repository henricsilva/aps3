from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Inscricao(Base):
    """Tabela `inscricoes`: vínculo entre um participante e um evento."""

    __tablename__ = "inscricoes"
    __table_args__ = (
        # Um participante só pode se inscrever uma vez em cada evento.
        UniqueConstraint("evento_id", "participante_id", name="uq_inscricao_evento_participante"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evento_id: Mapped[int] = mapped_column(
        ForeignKey("eventos.id", ondelete="CASCADE"), index=True
    )
    participante_id: Mapped[int] = mapped_column(
        ForeignKey("participantes.id", ondelete="CASCADE"), index=True
    )
    data_inscricao: Mapped[datetime] = mapped_column(DateTime, default=agora)

    evento: Mapped["Evento"] = relationship(back_populates="inscricoes")  # noqa: F821
    participante: Mapped["Participante"] = relationship(back_populates="inscricoes")  # noqa: F821
